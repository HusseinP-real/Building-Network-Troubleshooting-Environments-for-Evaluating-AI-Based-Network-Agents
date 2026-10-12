"""Inject a lab fault, run SADE, compare its answer to hidden ground truth, repair."""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lab

CASES = json.loads((ROOT / "tools" / "sade_cases.json").read_text())
INVENTORY = json.loads((ROOT / "inventory.json").read_text())
ONTOLOGY = {
    "interface_down": "A routed interface is administratively down.",
    "vrrp_service_stopped": "The VRRP gateway daemon is stopped on one router.",
    "backend_acl_reject": "A host egress firewall rejects application-to-backend traffic.",
}
SYSTEM_PROMPT = """You are SADE, a symptom-aware network diagnostician. Investigate this live Kathara lab and submit a structured root-cause diagnosis.

Follow five phases:
1. Blind start: first call mcp__kathara_base_mcp_server__get_reachability.
2. Decide whether an observed symptom is present. Expected policy denials are not faults. A healthy application path does not clear a redundant link or VRRP failure.
3. Follow the strongest symptom through a relevant Skill from the SADE project skill library. Use mcp__helper_server__run_helper for its diagnostic sweep; confirm the owner with read-only exec_shell commands.
4. If the first map looks healthy, enter diagnosis-methodology-skill and sweep L1/L2, routing, then service state. For this lab use available helpers: baseline_behavior, infra_sweep, ospf_snapshot, service_snapshot, l2_snapshot.
5. Stop when direct evidence identifies the altered resource. Do not repair it.

The helper scripts described in some SADE skills assume a NIKA session. In this standalone lab invoke mcp__helper_server__run_helper(script_name="...") instead of Bash or h.py. The exec_shell tool accepts host_name and one read-only command with no shell operators. You cannot use Bash, Read, Glob, Grep, Edit, Write, WebFetch, WebSearch, or Task. Ground truth is unavailable to you.

Your final answer must have exactly this form:
=== DIAGNOSIS ===
is_anomaly: true or false
resource_id: one canonical resource ID, or none
fault_type: one public ontology ID, or none
faulty_devices: comma-separated device names, or none
diagnosis_text:
Explain the observed evidence, mechanism, and repair in your own words.
=== END ===
"""


def _nika_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.getenv("NIKA_ROOT"):
        return Path(os.environ["NIKA_ROOT"]).expanduser().resolve()
    for parent in ROOT.parents:
        candidate = parent / "nika-demo"
        if candidate.is_dir():
            return candidate
    return ROOT / "nika-demo"


def _agent_dir(nika_root: Path) -> Path:
    return nika_root / "src" / "agent" / "community" / "sade"


def _topology_overview() -> str:
    nodes = INVENTORY["nodes"]
    lines = [f"{len(nodes)} devices, {len(INVENTORY['links'])} point-to-point links."]
    for role in ("router", "switch", "host"):
        names = [name for name, meta in nodes.items() if meta["role"] == role]
        lines.append(f"{role}s: {', '.join(names)}")
    lines.append("Links (device/interface to device/interface):")
    for link in INVENTORY["links"]:
        a, b = link["endpoints"]
        lines.append(f"{a['node']}/{a['interface']} <-> {b['node']}/{b['interface']}")
    return "\n".join(lines)


def _resource_catalog() -> str:
    # The resource catalog is public, as in NIKA. The expected pair remains
    # private until scoring; every router interface and possible owner appears.
    rows = []
    for name, meta in INVENTORY["nodes"].items():
        if meta["role"] == "router":
            rows.extend(f"interface/{name}/{port['interface']}" for port in meta["ports"])
            rows.append(f"service/{name}/keepalived")
        if meta["role"] == "host":
            rows.append(f"policy/{name}/output-tcp-8080")
    return "\n".join(rows)


def prompt_for(case_name: str) -> str:
    case = CASES[case_name]
    ontology = "\n".join(f"- {name}: {meaning}" for name, meaning in ONTOLOGY.items())
    # The ticket and public ontology are visible. Injection commands, expected
    # owner, and the ground-truth JSON are intentionally excluded.
    return (f"# Topology\n{_topology_overview()}\n\n"
            f"# Public fault ontology\n{ontology}\n\n"
            f"# Public resource catalog\n{_resource_catalog()}\n\n"
            "Choose one catalog resource using direct evidence.\n\n"
            f"# User ticket\n{case['ticket']}\n")


def parse_prediction(text: str) -> dict:
    match = re.search(r"===\s*DIAGNOSIS\s*===(.*?)(?:===\s*END\s*===|\Z)",
                      text, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("SADE did not submit a complete DIAGNOSIS block")
    body = match.group(1)
    fields = {}
    for key in ("is_anomaly", "resource_id", "fault_type", "faulty_devices"):
        found = re.search(rf"^{key}:\s*(.*)$", body, re.IGNORECASE | re.MULTILINE)
        if not found:
            raise ValueError(f"SADE diagnosis missing {key}")
        fields[key] = found.group(1).strip()
    anomaly = fields["is_anomaly"].lower()
    if anomaly not in ("true", "false"):
        raise ValueError("is_anomaly must be true or false")
    diagnosis = re.search(r"^diagnosis_text:\s*\n?(.*)$", body,
                          re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not diagnosis or not diagnosis.group(1).strip():
        raise ValueError("SADE diagnosis_text is empty")
    devices = [part.strip().lower() for part in fields["faulty_devices"].split(",")
               if part.strip() and part.strip().lower() != "none"]
    return {"is_anomaly": anomaly == "true",
            "resource_id": fields["resource_id"].lower(),
            "fault_type": fields["fault_type"].lower(),
            "faulty_devices": devices,
            "diagnosis_text": diagnosis.group(1).strip()}


def score_prediction(case_name: str, prediction: dict) -> dict:
    expected = CASES[case_name]["ground_truth"]
    observed = {"is_anomaly": prediction.get("is_anomaly"),
                "resource_id": str(prediction.get("resource_id", "")).lower(),
                "fault_type": str(prediction.get("fault_type", "")).lower(),
                "device": expected["device"] in prediction.get("faulty_devices", [])}
    return {
        "detection_correct": observed["is_anomaly"] is expected["is_anomaly"],
        "localization_correct": observed["resource_id"] == expected["resource_id"],
        "fault_type_correct": observed["fault_type"] == expected["fault_type"],
        "device_correct": observed["device"],
        "rca_exact": (observed["resource_id"], observed["fault_type"]) ==
                     (expected["resource_id"], expected["fault_type"]),
        "expected": expected,
        "predicted": prediction,
    }


def _preflight(nika_root: Path) -> None:
    agent_dir = _agent_dir(nika_root)
    if not (agent_dir / ".claude" / "skills").is_dir():
        raise RuntimeError(f"SADE skills not found at {agent_dir}; pass --nika-root")
    if importlib.util.find_spec("claude_agent_sdk") is None:
        raise RuntimeError("claude-agent-sdk is missing; install the NIKA sade extra")
    if not os.getenv("ANTHROPIC_API_KEY"):
        status = subprocess.run(["claude", "auth", "status"], text=True,
                                capture_output=True, check=False)
        if status.returncode != 0:
            raise RuntimeError("Set ANTHROPIC_API_KEY or log in with `claude auth login`")
    for node in ("r1", "r5", "app"):
        ok, output = lab.execute(node, "test -f /tmp/enterprise-ready")
        if not ok:
            raise RuntimeError(f"Lab device {node} is not ready: {output}; run python3 lab.py start")


async def _run_sade(prompt: str, nika_root: Path, max_turns: int, model: str) -> dict:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        UserMessage,
        query,
    )

    python = sys.executable
    server = str(ROOT / "tools" / "sade_lab_mcp.py")
    common = {"command": python, "args": [server], "transport": "stdio"}
    server_env = {key: os.environ[key] for key in ("PATH", "DOCKER_HOST", "XDG_CONFIG_HOME")
                  if key in os.environ}
    servers = {
        "kathara_base_mcp_server": {**common, "env": {**server_env, "SADE_MCP_KIND": "base"}},
        "helper_server": {**common, "env": {**server_env, "SADE_MCP_KIND": "helper"}},
    }
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        cwd=str(_agent_dir(nika_root)),
        setting_sources=["project"],
        model=model,
        max_turns=max_turns,
        permission_mode="bypassPermissions",
        mcp_servers=servers,
        allowed_tools=["mcp__kathara_base_mcp_server__*", "mcp__helper_server__*", "Skill"],
        disallowed_tools=["Bash", "Read", "Glob", "Grep", "Edit", "Write",
                          "NotebookEdit", "WebFetch", "WebSearch", "Task"],
    )
    trace = []
    final = ""
    tool_calls = 0
    usage = {}
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    final = block.text.strip()
                    trace.append({"kind": "text", "text": final})
                elif isinstance(block, ToolUseBlock):
                    tool_calls += 1
                    trace.append({"kind": "tool", "name": block.name, "input": block.input})
        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            for block in message.content:
                result = getattr(block, "content", None)
                if result is not None:
                    trace.append({"kind": "tool_result", "content": str(result)[:10000]})
        elif isinstance(message, ResultMessage):
            final = message.result or final
            usage = message.usage or {}
            if message.is_error:
                raise RuntimeError(f"SADE SDK reported an error: {final}")
    return {"final_text": final, "trace": trace, "tool_calls": tool_calls, "usage": usage}


def _assert_state(case_name: str, phase: str) -> None:
    node, command = CASES[case_name][f"{phase}_check"]
    ok, output = lab.execute(node, command)
    if not ok:
        raise RuntimeError(f"{case_name}: {phase} verification failed on {node}: {output}")


def run_case(case_name: str, nika_root: Path, max_turns: int, model: str) -> Path:
    _preflight(nika_root)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out = ROOT / "results" / "sade" / now / f"{case_name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {"case": case_name, "timestamp": now, "model": model, "status": "running",
              "agent_prompt": prompt_for(case_name), "injection_verified": False,
              "repair_verified": False}
    started = time.monotonic()
    injected = False
    try:
        # Only one case at a time; a healthy baseline makes comparisons fair.
        if lab.check() != 0:
            raise RuntimeError("Healthy baseline failed; repair existing faults before running SADE")
        node, inject, repair = lab.FAULTS[case_name]
        injected = True  # all repair commands are idempotent, including partial injection
        ok, detail = lab.execute(node, inject)
        if not ok:
            raise RuntimeError(f"Injection failed: {detail}")
        time.sleep(8)
        _assert_state(case_name, "inject")
        report["injection_verified"] = True
        report["agent"] = asyncio.run(_run_sade(report["agent_prompt"], nika_root, max_turns, model))
        prediction = parse_prediction(report["agent"]["final_text"])
        report["score"] = score_prediction(case_name, prediction)
        report["status"] = "scored"
    except Exception as exc:  # noqa: BLE001 - always attempt repair and save the result
        report["status"] = "error"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if injected:
            node, _, repair = lab.FAULTS[case_name]
            try:
                ok, detail = lab.execute(node, repair)
            except Exception as exc:  # noqa: BLE001 - preserve the run report if repair raises
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            if ok:
                time.sleep(8)
                for attempt in range(3):
                    try:
                        _assert_state(case_name, "repair")
                        report["repair_verified"] = True
                        break
                    except Exception as exc:  # noqa: BLE001 - keep retrying verification
                        report["repair_error"] = str(exc)
                        if attempt < 2:
                            time.sleep(2)
                if report["repair_verified"]:
                    report.pop("repair_error", None)
            else:
                report["repair_error"] = detail
        report["wall_seconds"] = round(time.monotonic() - started, 3)
        out.write_text(json.dumps(report, indent=2, default=str) + "\n")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    verify = sub.add_parser("validate", help="Check case metadata and SADE source without running a model")
    verify.add_argument("--nika-root")
    score = sub.add_parser("score", help="Score a saved SADE final message against ground truth")
    score.add_argument("case", choices=CASES)
    score.add_argument("answer_file", type=Path)
    run = sub.add_parser("run", help="Inject, diagnose, score, and repair one case")
    run.add_argument("case", choices=CASES)
    run.add_argument("--nika-root")
    run.add_argument("--max-turns", type=int, default=30)
    run.add_argument("--model", default=os.getenv("SADE_MODEL", "claude-haiku-5-5"),
                     help="Claude model ID (default: SADE_MODEL or claude-haiku-5-5)")
    args = parser.parse_args()
    if args.action == "list":
        for name, case in CASES.items():
            print(f"{name}: {case['ticket']}")
        return 0
    if args.action == "validate":
        for name in CASES:
            assert name in lab.FAULTS
            assert CASES[name]["ground_truth"]["fault_type"] in ONTOLOGY
            assert CASES[name]["ground_truth"]["device"] in INVENTORY["nodes"]
            assert CASES[name]["ground_truth"]["resource_id"] in _resource_catalog().splitlines()
            assert CASES[name]["ground_truth"]["root_cause"] not in prompt_for(name)
        agent_dir = _agent_dir(_nika_root(args.nika_root))
        if not (agent_dir / ".claude" / "skills").is_dir():
            parser.error(f"SADE skills not found at {agent_dir}")
        print("3 cases valid; SADE skills found; expected root causes hidden from prompts")
        return 0
    if args.action == "score":
        content = args.answer_file.read_text()
        try:
            saved = json.loads(content)
            content = saved.get("final_text", saved.get("agent", {}).get("final_text", content))
        except json.JSONDecodeError:
            pass
        result = score_prediction(args.case, parse_prediction(content))
        print(json.dumps(result, indent=2))
        return 0 if result["rca_exact"] else 1
    if args.max_turns < 1:
        parser.error("--max-turns must be positive")
    if not args.model.strip():
        parser.error("--model must not be empty")
    try:
        path = run_case(args.case, _nika_root(args.nika_root), args.max_turns, args.model)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    result = json.loads(path.read_text())
    print(f"Result: {path}\nStatus: {result['status']}\nModel: {result['model']}")
    print(f"Injection verified: {result['injection_verified']}")
    print(f"Repair verified: {result['repair_verified']}")
    if result.get("score"):
        for label, key in (("Anomaly detection", "detection_correct"),
                           ("Device", "device_correct"),
                           ("Resource localization", "localization_correct"),
                           ("Fault type", "fault_type_correct"),
                           ("Exact RCA", "rca_exact")):
            print(f"{label}: {result['score'][key]}")
        print(f"Tool calls: {result['agent']['tool_calls']}")
    if result.get("error"):
        print(result["error"], file=sys.stderr)
    if not result["repair_verified"]:
        print("Repair was not verified; inspect the lab before another case.", file=sys.stderr)
    return 0 if result["status"] == "scored" and result["repair_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
