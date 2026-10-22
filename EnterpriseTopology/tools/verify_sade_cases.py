"""Verify fault injection and restoration without calling a diagnosis model."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import sade_eval as ev


def verify(case_name: str) -> dict:
    report = {
        "case": case_name,
        "injection_verified": False,
        "environment_restored": False,
    }
    injected = []
    try:
        if ev.lab.check() != 0:
            raise RuntimeError("Baseline is unhealthy; no fault was injected")
        for fault in ev.case_faults(case_name):
            node, command, _ = ev.lab.FAULTS[fault]
            injected.append(fault)
            ok, detail = ev.lab.execute(node, command)
            if not ok:
                raise RuntimeError(f"{fault}: {detail}")
        if injected:
            time.sleep(8)
            for fault in injected:
                ev._assert_state(fault, "inject")
        report["injection_verified"] = True
        observations = []
        for cause in ev.expected_causes(case_name):
            node = cause["device"]
            commands = {
                "interface_down": "ip -br link show",
                "vrrp_service_stopped": "pgrep -a keepalived",
                "backend_acl_reject": "iptables -S",
                "ospf_passive_interface": "vtysh -c 'show ip ospf interface eth0'",
            }
            ok, output = ev.lab.execute(node, commands[cause["fault_type"]])
            observations.append({"node": node, "ok": ok, "output": output})
        report["observations"] = observations
    except Exception as exc:  # noqa: BLE001 - restore owned faults even after verification errors
        report["error"] = str(exc)
    finally:
        errors = []
        for fault in reversed(injected):
            node, _, command = ev.lab.FAULTS[fault]
            try:
                ok, detail = ev.lab.execute(node, command)
                if not ok:
                    errors.append(f"{fault}: {detail}")
            except Exception as exc:  # noqa: BLE001 - restore owned faults even after verification errors
                errors.append(f"{fault}: {exc}")
        if injected:
            time.sleep(8)
            if not errors:
                try:
                    for fault in injected:
                        ev._assert_state(fault, "repair")
                    report["environment_restored"] = ev.lab.check() == 0
                except Exception as exc:  # noqa: BLE001 - restore owned faults even after verification errors
                    errors.append(str(exc))
        elif "error" not in report:
            report["environment_restored"] = ev.lab.check() == 0
        if errors:
            report["repair_errors"] = errors
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="+", choices=list(ev.CASES))
    args = parser.parse_args()
    reports = []
    for case in args.cases:
        print(f"Verifying {case}...", flush=True)
        report = verify(case)
        reports.append(report)
        print(
            json.dumps({k: v for k, v in report.items() if k != "observations"}),
            flush=True,
        )
        if not report["environment_restored"]:
            break
    out = (
        ev.ROOT
        / "results"
        / "sade"
        / f"verification-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2) + "\n")
    print(f"Verification: {out}")
    return (
        0
        if len(reports) == len(args.cases)
        and all(
            r["injection_verified"] and r["environment_restored"] and "error" not in r
            for r in reports
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
