"""Operator-only catalogs and fixed lab adapters. Never imported by diagnostic agents."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "tools"))
# Compatibility exports used by the server and operation coordinator.
import generic_faults
from environment_guard import Conflict as Conflict  # noqa: PLC0414
from environment_guard import Lease as Lease  # noqa: PLC0414

CASES = json.loads((ROOT / "tools/sade_cases.json").read_text())
LAB_ROOTS = {
    "enterprise-75": ROOT,
    "enterprise-75-standalone": REPO / "EnterpriseTopology75",
    "multisite": REPO / "MultiSite_BGP_OSPF_Benchmark",
}


def load_lab(topology):
    spec = importlib.util.spec_from_file_location(
        "operator_lab", LAB_ROOTS[topology] / "lab.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def topologies():
    rows = {
        "enterprise-75": {
            "name": "Enterprise Topology",
            "inventory": ROOT / "inventory.json",
            "scenario_count": len(CASES),
            "evaluation_enabled": True,
        },
        "enterprise-75-standalone": {
            "name": "Enterprise Topology · Standalone",
            "inventory": STATIC / "topologies/enterprise-75-standalone.json",
            "scenario_count": len(load_lab("enterprise-75-standalone").FAULTS) + 1,
            "evaluation_enabled": False,
        },
    }
    for item in json.loads((STATIC / "topologies/catalog.json").read_text()):
        rows[item["id"]] = {
            **item,
            "inventory": STATIC / "topologies" / item["inventory"],
        }
    for key, row in rows.items():
        row["scenario_count"] = len(generic_faults.FAMILIES)
        row["evaluation_enabled"] = any(generic_faults.validated(key, family) for family in generic_faults.FAMILIES)
    return {
        key: row
        for key, row in rows.items()
        if sum(
            not n.get("virtual", False)
            for n in json.loads(row["inventory"].read_text())["nodes"].values()
        )
        >= 75
    }


def native_support(topology):
    if topology not in LAB_ROOTS:
        return (
            False,
            "Catalog only: no adapter with scoped execution, complete baseline and verified recovery.",
        )
    lab = load_lab(topology)
    viewed = json.loads(topologies()[topology]["inventory"].read_text())
    actual = json.loads((lab.ROOT / "inventory.json").read_text())
    names = {name for name, node in viewed["nodes"].items() if not node.get("virtual")}
    actual_names = (
        set(actual["nodes"])
        if "nodes" in actual
        else set(actual["interfaces"]) | set(actual["hosts"])
    )
    if names != actual_names:
        return (
            False,
            "Runtime device inventory differs from the topology being viewed; refresh the snapshot.",
        )
    # Compare every mapped interface and collision domain, rather than renaming devices.
    if topology != "enterprise-75":
        config = lab.ROOT / "lab.conf"
        bindings = {
            (node, "eth" + port): domain
            for node, port, domain in re.findall(
                r'^([\w-]+)\[(\d+)\]\s*=\s*["\']?([^\s"\'#]+)',
                config.read_text(),
                re.MULTILINE,
            )
        }
        for name in names:
            for port in viewed["nodes"][name].get("ports", []):
                # Imported inventory ports retain the Kathara collision-domain label.
                domain = (
                    port.get("collision_domain")
                    or port.get("domain")
                    or (
                        port["peer"][4:]
                        if port["peer"].startswith("lan:")
                        else port.get("link")
                    )
                )
                if domain and bindings.get((name, port["interface"])) != domain:
                    return (
                        False,
                        "Runtime interface mapping differs from the displayed snapshot.",
                    )
    return True, f"Adapter ready · {lab.ROOT.name}/lab.py · live baseline required"


def native_catalog(topology):
    if topology not in topologies():
        raise ValueError("Unknown topology ID")
    enabled, reason = native_support(topology)
    rows = []
    if topology in ("enterprise-75", "enterprise-75-standalone"):
        faults = load_lab(topology).FAULTS
        for fault in faults:
            case = CASES[fault]
            rows.append(
                {
                    "id": fault,
                    "kind": "fault",
                    "components": [fault],
                    "description": case["ground_truth"]["root_cause"],
                    "targets": [case["ground_truth"]["resource_id"]],
                    "expected_impact": case["ticket"],
                    "case_ids": [
                        k for k, v in CASES.items() if v.get("fault") == fault
                    ],
                }
            )
        healthy = [k for k, v in CASES.items() if v["category"] == "healthy"]
        rows.append(
            {
                "id": "healthy",
                "kind": "healthy",
                "components": [],
                "description": CASES[healthy[0]]["ground_truth"]["root_cause"],
                "targets": [],
                "expected_impact": "No mutation. Full healthy baseline including intentional policy denials.",
                "case_ids": healthy,
            }
        )
        if topology == "enterprise-75":
            for key, case in CASES.items():
                if case["category"] == "compound":
                    rows.append(
                        {
                            "id": key,
                            "kind": "compound",
                            "components": case["faults"],
                            "description": case["ground_truth"]["root_cause"],
                            "targets": [
                                c["resource_id"]
                                for c in case["ground_truth"]["root_causes"]
                            ],
                            "expected_impact": "Combined effects of: "
                            + ", ".join(case["faults"]),
                            "case_ids": [key],
                        }
                    )
    elif topology == "multisite":
        for key, item in load_lab(topology).FAULTS.items():
            rows.append(
                {
                    "id": key,
                    "kind": "fault",
                    "components": [key],
                    "description": item["desc"],
                    "targets": [
                        f"{n}: {cmd}" for n, cmd in zip(item["nodes"], item["apply"])
                    ],
                    "expected_impact": f"Affected probe from {item['source']}: {item['fail']}; control remains healthy: {item['pass']}",
                    "case_ids": [],
                }
            )
    elif topology == "multi-as-isp":
        grouped = {}
        for path in sorted(
            (REPO / "Multi-AS-ISP-Backbone-W11-75/scenarios").glob(
                "*/ground_truth.json"
            )
        ):
            item = json.loads(path.read_text())
            kind = (
                "compound"
                if item["id"] == "S08"
                else "fault"
                if item["fault_exists"]
                else "healthy"
            )
            signature = json.dumps(
                [kind, item.get("fault_device"), item.get("injection")], sort_keys=True
            )
            if signature in grouped:
                grouped[signature]["case_ids"].append(item["id"])
                continue
            row = {
                "id": item["id"],
                "kind": kind,
                "components": [],
                "description": item["notes"],
                "targets": [str(item.get("fault_device") or "none")],
                "expected_impact": item["category"],
                "case_ids": [item["id"]],
            }
            grouped[signature] = row
            rows.append(row)
    elif topology in ("jiayuan-75", "nika-92"):
        source = {
            "jiayuan-75": "Kath5_Jiayuan_75Devices",
            "nika-92": "NIKA_Clos_Jiayuan_92Devices",
        }[topology]
        for line in (
            (REPO / "FaulT-Bench/ground_truth/scenarios.jsonl").read_text().splitlines()
        ):
            item = json.loads(line)
            if item["topology"] != source:
                continue
            rows.append(
                {
                    "id": item["scenario_id"],
                    "kind": "healthy"
                    if not item["expected_anomaly"]
                    else "compound"
                    if "multi-fault" in item["fault_type"].lower()
                    else "fault",
                    "components": [],
                    "description": item["root_cause_and_reference"],
                    "targets": item["fault_location"],
                    "expected_impact": item["user_scenario"],
                    "case_ids": [item["scenario_id"]],
                }
            )
    else:
        inventory = topologies()[topology]["inventory"]
        rows = json.loads(inventory.read_text()).get("fault_catalog", [])
    for row in rows:
        row.update(
            execution_enabled=enabled,
            support_reason=reason,
            evaluation_enabled=topology == "enterprise-75",
        )
    return rows


def support(topology):
    return generic_faults.support(topology)


def catalog(topology):
    rows = generic_faults.catalog(topology)
    # Preserve recovery access for older native mutations, without offering new ones.
    folder = LAB_ROOTS.get(topology)
    if folder and (folder / 'results/control/state.json').exists():
        pending = Lease(folder).read()['pending']
        if any(key not in generic_faults.FAMILIES for key in pending):
            rows.extend(row for row in native_catalog(topology) if set(row['components']) & set(pending))
    return rows


def selected(topology, fault):
    for row in (catalog(topology) if fault in generic_faults.FAMILIES else native_catalog(topology)):
        if row["id"] == fault:
            return row
    raise ValueError("Unknown fault ID for this topology")


def probe(lab, node, command):
    if hasattr(lab, "execute"):
        ok, detail = lab.execute(node, command)
    else:
        result = lab.exec_cmd(node, command)
        ok = result.returncode == 0
        detail = (result.stdout or "") + (result.stderr or "")
    print(f"{'PASS' if ok else 'FAIL'} probe on {node}", flush=True)
    if not ok and detail:
        print(detail[:1200], flush=True)
    return ok


def verify(lab, topology, fault, repair=False):
    if topology == "multisite":
        item = lab.FAULTS[fault]
        # Invert inside the remote shell, so transport errors never mean expected failure.
        affected = probe(
            lab,
            item["source"],
            item["fail"] if repair else "! ( " + item["fail"] + " )",
        )
        control = probe(lab, item["source"], item["pass"])
        return affected and control
    field = "repair_check" if repair else "inject_check"
    node, cmd = CASES[fault][field]
    return probe(lab, node, cmd)


def step(topology, action, fault=None):
    if fault in generic_faults.FAMILIES:
        if action == 'validate':
            report = generic_faults.validate(topology, fault)
            print(json.dumps(report), flush=True)
            return report['passed']
        adapter = generic_faults.Adapter(topology)
        if action in ('baseline', 'restored-baseline'):
            return adapter.check() == 0
        adapter.action(action, fault)
        return True
    enabled, reason = native_support(topology)
    if not enabled:
        raise ValueError(reason)
    lab = load_lab(topology)
    print(f"Target: {topology} · {lab.ROOT}", flush=True)
    if action == "restored-baseline":
        print(
            "Waiting 8 seconds for routing and gateway convergence before the full baseline…",
            flush=True,
        )
        time.sleep(8)
        action = "baseline"
    if action == "baseline":
        ready = True
        if topology == "multisite":
            from concurrent.futures import ThreadPoolExecutor

            inventory = json.loads((lab.ROOT / "inventory.json").read_text())
            nodes = set(inventory["interfaces"]) | set(inventory["hosts"])
            with ThreadPoolExecutor(max_workers=4) as pool:
                ready = all(
                    pool.map(
                        lambda node: probe(lab, node, "test -d /sys/class/net/eth0"),
                        sorted(nodes),
                    )
                )
        healthy = (
            lab.run_checks() == 0 if topology == "multisite" else lab.check() == 0
        ) and ready
        # Redundant failures can leave data-plane checks healthy. Check all repair predicates.
        predicates = [verify(lab, topology, key, True) for key in lab.FAULTS]
        restored = all(predicates)
        return healthy and restored
    if fault not in lab.FAULTS:
        raise ValueError("Unknown mechanism")
    if action in ("verify", "repaired"):
        attempts = 12 if topology == "multisite" else 4
        for attempt in range(attempts):
            if verify(lab, topology, fault, action == "repaired"):
                return True
            if attempt < attempts - 1:
                time.sleep(3)
        return False
    if action not in ("inject", "repair"):
        raise ValueError("Unknown step")
    if topology == "multisite":
        return lab.fault(fault, action) == 0
    node, inject, repair = lab.FAULTS[fault]
    return probe(lab, node, inject if action == "inject" else repair)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("topology", choices=generic_faults.TARGETS)
    p.add_argument(
        "action",
        choices=[
            "validate",
            "baseline",
            "inject",
            "repair",
            "verify",
            "repaired",
            "restored-baseline",
        ],
    )
    p.add_argument("fault", nargs="?")
    args = p.parse_args()
    sys.exit(0 if step(args.topology, args.action, args.fault) else 1)
