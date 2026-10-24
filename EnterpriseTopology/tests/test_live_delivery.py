"""Opt-in real Kathara regression cycles, without any model/API calls.

RUN_LIVE_DELIVERY=1 python -m unittest discover -s tests -p test_live_delivery.py -v
Uses the existing EnterpriseTopology lab and the same process-shared lease as the
dashboard. It never starts, stops, rebuilds or deletes a lab. Only faults this
suite attempts are repaired. An uncertain repair retains durable pending intent.
"""

import json
import os
import sys
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
import fault_runtime as runtime
from environment_guard import Lease


@unittest.skipUnless(
    os.getenv("RUN_LIVE_DELIVERY") == "1",
    "Opt in to real Kathara mutation with RUN_LIVE_DELIVERY=1",
)
class LiveDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lease = Lease(ROOT).acquire()
        cls.addClassCleanup(cls.lease.release)
        if cls.lease.read()["pending"]:
            raise RuntimeError(
                "Existing pending faults: recover them before live tests"
            )
        cls.lab = runtime.load_lab("enterprise-75")
        cls.report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "kind": "real_network_validation",
            "topology_id": "enterprise-75",
            "model_evaluation": False,
            "cycles": [],
        }
        cls.out = (
            ROOT
            / "results"
            / "delivery"
            / (
                "live-"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + ".json"
            )
        )
        cls.out.parent.mkdir(parents=True, exist_ok=True)
        cls.addClassCleanup(cls.save)
        cls.report["initial_baseline_passed"] = runtime.step(
            "enterprise-75", "baseline"
        )
        cls.save()
        if not cls.report["initial_baseline_passed"]:
            raise RuntimeError("Initial live baseline failed; no fault was injected")

    @classmethod
    def save(cls):
        cls.report["updated_at"] = datetime.now(timezone.utc).isoformat()
        cls.report["pending"] = cls.lease.read()["pending"]
        cls.out.write_text(json.dumps(cls.report, indent=2) + "\n")

    def probe(self, row, label, node, command):
        ok, output = self.lab.execute(node, command)
        row["checks"].append(
            {
                "label": label,
                "node": node,
                "command": command,
                "passed": ok,
                "output": output,
            }
        )
        self.assertTrue(ok, f"{label}: {output}")

    def impact(self, row, faults):
        acl = bool({"database-acl", "database-ingress-acl"} & set(faults))
        if acl:
            self.probe(
                row,
                "Application has the intended HTTP 503 symptom",
                "office",
                'test "$(curl -s --max-time 6 -o /tmp/delivery-fault-body -w "%{http_code}" http://app.enterprise.test/)" = 503 && grep -F "database dependency unavailable" /tmp/delivery-fault-body',
            )
            self.probe(
                row,
                "Database remains healthy from unaffected operations path",
                "ops",
                'curl -fsS --max-time 6 http://10.30.20.10:8080/ | grep -F "database: healthy"',
            )
        else:
            self.probe(
                row,
                "Redundant paths preserve application access",
                "staff",
                'curl -fsS --max-time 6 http://app.enterprise.test/ | grep -F "app: healthy"',
            )
        if "gateway-service" in faults:
            self.probe(
                row,
                "Backup assumes the staff virtual gateway",
                "r6",
                "ip -4 addr | grep -F '10.10.10.1/24'",
            )
            self.probe(
                row,
                "Stopped primary releases the staff virtual gateway",
                "r5",
                "! ip -4 addr | grep -F '10.10.10.1/24'",
            )
        if "gateway-service-r8" in faults:
            self.probe(
                row,
                "Branch primary retains the engineering gateway",
                "r7",
                "ip -4 addr | grep -F '10.20.10.1/24'",
            )
        if "ospf-passive-r7" in faults:
            self.probe(
                row,
                "Passive OSPF failure leaves the physical interface up",
                "r7",
                'test "$(cat /sys/class/net/eth0/operstate)" = up',
            )

    def cycle(self, scenario):
        self.assertEqual(
            self.lease.read()["pending"],
            [],
            "Earlier cycle needs recovery; refusing to mutate",
        )
        components = runtime.selected("enterprise-75", scenario)["components"]
        row = {
            "scenario": scenario,
            "components": components,
            "checks": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "restored": False,
        }
        self.report["cycles"].append(row)
        attempted = []
        started = time.monotonic()
        try:
            for fault in components:
                self.assertTrue(
                    runtime.verify(self.lab, "enterprise-75", fault, True),
                    "Fault precondition not healthy",
                )
                self.lease.mark(fault)
                attempted.append(fault)
                self.assertTrue(runtime.step("enterprise-75", "inject", fault))
            time.sleep(8 if components else 0)
            for fault in components:
                self.assertTrue(
                    runtime.step("enterprise-75", "verify", fault),
                    f"No fault state for {fault}",
                )
            self.impact(row, components)
            row["passed"] = True
        except BaseException as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            repairs = []
            for fault in reversed(attempted):
                try:
                    repairs.append(runtime.step("enterprise-75", "repair", fault))
                except Exception as exc:  # noqa: BLE001 - attempt every owned repair before reporting failure
                    repairs.append(False)
                    row.setdefault("repair_errors", []).append(str(exc))
            if all(repairs):
                if attempted:
                    time.sleep(8)
                predicates = [
                    runtime.step("enterprise-75", "repaired", fault)
                    for fault in attempted
                ]
                baseline = runtime.step("enterprise-75", "baseline")
                row["restored"] = all(predicates) and baseline
                if row["restored"]:
                    self.lease.clear(attempted)
            row["seconds"] = round(time.monotonic() - started, 3)
            row["passed"] = row["passed"] and row["restored"]
            self.save()
            self.assertTrue(
                row["restored"], "Recovery was not verified; pending faults retained"
            )

    def test_01_healthy_negative_control(self):
        self.cycle("healthy")

    def test_02_core_uplink(self):
        self.cycle("core-uplink")

    def test_03_alternate_core_uplink(self):
        self.cycle("core-uplink-r6")

    def test_04_gateway_failover(self):
        self.cycle("gateway-service")

    def test_05_standby_gateway_failure(self):
        self.cycle("gateway-service-r8")

    def test_06_application_egress_acl(self):
        self.cycle("database-acl")

    def test_07_database_ingress_acl(self):
        self.cycle("database-ingress-acl")

    def test_08_ospf_passive_interface(self):
        self.cycle("ospf-passive-r7")

    def test_09_compound_uplink_acl(self):
        self.cycle("compound-uplink-acl")

    def test_10_compound_ospf_gateway(self):
        self.cycle("compound-ospf-gateway")

    def test_11_repeat_application_fault_after_other_cycles(self):
        self.cycle("database-acl")


if __name__ == "__main__":
    unittest.main()
