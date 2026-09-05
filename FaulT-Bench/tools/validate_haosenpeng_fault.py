#!/usr/bin/env python3
"""Exercise the compound fault in an isolated Kath3 lab, without LLM APIs.

Run from any directory with Python 3.12+, Docker and the Kathara CLI installed.
Only the temporary lab created here is cleaned. Existing labs are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "faultbench" / "src"))
from faultbench.scenario import parse_scenario, resolve_scenario

SCENARIO_ID = "kath3-laptop0-wrong-gateway-and-icmp-drop"
SCENARIO = ROOT / "dataset/kath3_Q/custom" / f"{SCENARIO_ID}.txt"
TOPOLOGY = ROOT / "topology_kathara/Kath3"
RULE = ("OUTPUT -d 192.168.100.1/32 -p icmp -m comment "
        "--comment haosenpeng-compound-icmp -j DROP")
FIX_ROUTE = "ip route replace default via 172.16.20.1"
FIX_FILTER = "iptables -D " + RULE


def evaluate(expect: str, rc: int, output: str) -> bool:
    """Fail closed: no advisory passes or assumed packet loss on exec errors."""
    if expect.isdecimal():
        return rc == 0 and output.strip() == expect
    if expect not in ("0% loss", "loss>0"):
        raise ValueError(f"Unsupported expectation: {expect!r}")
    match = re.search(r"(\d+(?:\.\d+)?)%\s*(?:packet\s*)?loss", output)
    if match is None:
        return False
    loss = float(match.group(1))
    return (rc == 0 and loss == 0) if expect == "0% loss" else (rc == 1 and loss > 0)


def validate_spec():
    sc = parse_scenario(SCENARIO)
    assert resolve_scenario(SCENARIO_ID) == SCENARIO
    assert sc.scenario_id == SCENARIO_ID and sc.topology == "Kath3"
    assert sc.injection.device == "laptop0" and sc.injection.command
    assert len(sc.post_inject_check) == 6
    assert sc.ground_truth and sc.fix_spec and sc.scoring_axes
    subprocess.run(["sh", "-n"], input=sc.injection.command, text=True, check=True)
    for check in sc.post_inject_check:
        assert check.device in ("laptop0", "pc4")
        evaluate(check.expect, 255, "")
    return sc


class Lab:
    def __init__(self, path: Path):
        self.path = path
        self.marker = "__FAULTBENCH_RC_" + uuid.uuid4().hex + "="

    def exec(self, device: str, command: str) -> tuple[int, str]:
        # Kathara CLI's exit status is not the device command's exit status.
        # Run the command in a child shell so even 'exit'/'set -e' cannot
        # suppress the outer status marker. A missing marker is a hard error.
        wrapped = (f"sh -c {shlex.quote(command)}; _fb_rc=$?; "
                   f"printf '\\n{self.marker}%s\\n' \"$_fb_rc\"")
        proc = subprocess.run(
            ["kathara", "exec", "-d", str(self.path), "--wait", device,
             "--", "sh", "-c", wrapped],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=45,
        )
        match = re.search(rf"\n{re.escape(self.marker)}(\d+)\s*$", proc.stdout)
        if proc.returncode != 0 or match is None:
            raise RuntimeError(f"Cannot execute on {device}: {proc.stdout[-2000:]}")
        return int(match.group(1)), proc.stdout[:match.start()].strip()

    def mutate(self, command: str):
        rc, output = self.exec("laptop0", command)
        if rc != 0:
            raise RuntimeError(f"Mutation failed (rc={rc}): {command}\n{output}")


def probe(device: str, target: str, healthy: bool = True):
    return device, f"ping -W2 -c2 {target}", "0% loss" if healthy else "loss>0"


def state_checks(gateway: str, filtered: bool, pc4_ok: bool, remote_ok: bool):
    # awk prints zero and exits successfully when the tagged rule is absent.
    return [
        ("laptop0", f"ip route show default | grep -c 'via {gateway}'", "1"),
        ("laptop0", "rules=$(iptables -S OUTPUT) && printf '%s\\n' \"$rules\" | awk '/haosenpeng-compound-icmp/ "
         "{n++} END {print n+0}'", "1" if filtered else "0"),
        probe("laptop0", "172.16.20.1"),
        probe("laptop0", "172.16.10.4", pc4_ok),
        probe("laptop0", "192.168.100.1", remote_ok),
        probe("pc4", "192.168.100.1"),
    ]


def run_stage(lab: Lab, report: dict, name: str, checks, *, required=True):
    records = []
    for device, command, expect in checks:
        rc, output = lab.exec(device, command)
        records.append(dict(device=device, command=command, expect=expect,
                            rc=rc, output=output, passed=evaluate(expect, rc, output)))
    passed = all(row["passed"] for row in records)
    report["stages"].append(dict(name=name, passed=passed, checks=records))
    print(f"[{name}] {'PASS' if passed else 'FAIL'}", flush=True)
    if required and not passed:
        failed = [r for r in records if not r["passed"]]
        raise RuntimeError(f"{name}: {json.dumps(failed, ensure_ascii=False)}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Parse and shell-check; no containers")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "faultbench/runs/haosenpeng-validation.json")
    parser.add_argument("--converge-timeout", type=int, default=240)
    args = parser.parse_args()
    sc = validate_spec()
    if args.check_only:
        print("PASS: scenario resolves, parses, and injection shell syntax is valid")
        return 0
    for binary in ("docker", "kathara"):
        if not shutil.which(binary):
            parser.error(f"{binary} is not on PATH")
    report = dict(scenario_id=SCENARIO_ID, started_at=datetime.now(timezone.utc).isoformat(),
                  kind="live-network-validation-without-llm", passed=False, stages=[],
                  scenario_sha256=hashlib.sha256(SCENARIO.read_bytes()).hexdigest(),
                  topology_sha256={str(p.relative_to(TOPOLOGY)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(TOPOLOGY.rglob("*"))
                                   if p.is_file() and (p.name == "lab.conf" or p.suffix == ".startup")})
    for command in (["docker", "version", "--format", "{{.Server.Version}}"],
                    ["kathara", "--version"]):
        proc = subprocess.run(command, capture_output=True, text=True, timeout=20, check=True)
        report[command[0] + "_version"] = proc.stdout.strip()
    # CLI lab identity is directory-based: a unique temporary copy isolates
    # the entire topology from any existing CLI- or API-started Kath3 lab.
    temp = Path(tempfile.mkdtemp(prefix="faultbench-haosenpeng-"))
    lab_path = temp / "Kath3"
    shutil.copytree(TOPOLOGY, lab_path, ignore=shutil.ignore_patterns("shared", ".DS_Store"))
    lab = Lab(lab_path)
    report["temporary_lab"] = str(lab_path)
    try:
        print(f"[deploy] isolated lab: {lab_path}", flush=True)
        proc = subprocess.run(
            ["kathara", "lstart", "-d", str(lab_path), "--noterminals", "-H", "-S"],
            capture_output=True, text=True, timeout=240,
        )
        report["deploy"] = dict(rc=proc.returncode, output=proc.stdout + proc.stderr)
        if proc.returncode != 0:
            raise RuntimeError(report["deploy"]["output"])
        healthy = state_checks("172.16.20.1", False, True, True)
        deadline = time.monotonic() + args.converge_timeout
        while not run_stage(lab, report, "baseline", healthy, required=False):
            if time.monotonic() >= deadline:
                raise RuntimeError("Healthy baseline did not converge; no fault injected")
            time.sleep(5)

        lab.mutate(sc.injection.command)
        checks = [(c.device, c.command, c.expect) for c in sc.post_inject_check]
        run_stage(lab, report, "both-faults", checks)
        lab.mutate(sc.injection.command)
        run_stage(lab, report, "repeat-injection-no-duplicate-rule", checks)

        lab.mutate(FIX_ROUTE)
        # Reset only this rule's counter, then demonstrate matching drops.
        # The rule was inserted at position 1 in this fresh, isolated lab.
        lab.mutate("iptables -Z OUTPUT 1")
        run_stage(lab, report, "gateway-fixed-filter-remains",
                  state_checks("172.16.20.1", True, True, False))
        rc, counters = lab.exec("laptop0", "iptables -L OUTPUT -n -v -x")
        report["filter_counters_after_route_repair"] = counters
        tagged = [line for line in counters.splitlines() if "haosenpeng-compound-icmp" in line]
        if rc != 0 or len(tagged) != 1 or int(tagged[0].split()[0]) < 1:
            raise RuntimeError("Target ping did not increment the tagged DROP counter")

        lab.mutate(FIX_FILTER)
        run_stage(lab, report, "both-fixed-route-first", healthy)

        lab.mutate(sc.injection.command)
        lab.mutate(FIX_FILTER)
        run_stage(lab, report, "filter-fixed-wrong-gateway-remains",
                  state_checks("172.16.20.99", False, False, False))
        lab.mutate(FIX_ROUTE)
        run_stage(lab, report, "both-fixed-filter-first", healthy)
        report["passed"] = True
    except (Exception, KeyboardInterrupt) as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(report["error"], file=sys.stderr, flush=True)
    finally:
        # Never call the harness's global pruning helpers or docker prune.
        try:
            proc = subprocess.run(["kathara", "lclean", "-d", str(lab_path)],
                                  capture_output=True, text=True, timeout=180)
            report["cleanup"] = dict(rc=proc.returncode, output=proc.stdout + proc.stderr)
            if proc.returncode != 0:
                report["passed"] = False
        except Exception as exc:
            report["cleanup"] = dict(error=str(exc))
            report["passed"] = False
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        # Retain the small temporary config for troubleshooting failed deploys.
        print(f"Report: {args.output.resolve()}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
