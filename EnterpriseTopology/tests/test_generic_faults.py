"""Generic fault isolation, transport failure, recovery and catalog contracts."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import generic_faults as g
from environment_guard import Lease


class GenericFaultTests(unittest.TestCase):
    def test_all_thirteen_mappings_have_distinct_real_targets(self):
        self.assertEqual(len(g.TARGETS), 13)
        for key, target in g.TARGETS.items():
            with self.subTest(topology=key):
                self.assertGreaterEqual(len(target["nodes"]), 75)
                self.assertEqual(
                    len(
                        {
                            target[role]["node"]
                            for role in ("source", "remote", "control")
                        }
                    ),
                    3,
                )
                self.assertTrue(
                    all(
                        target[role]["node"] in target["nodes"]
                        for role in ("source", "remote", "control")
                    )
                )
                self.assertEqual(
                    [row["id"] for row in g.catalog(key)], list(g.FAMILIES)
                )
                self.assertEqual(set(g.Adapter(key).cases()), set(g.FAMILIES))

    def test_transport_failure_cannot_be_expected_ping_failure(self):
        adapter = g.Adapter("enterprise-75")
        with (
            patch.object(adapter, "execute", return_value=(False, "transport failed")),
            self.assertRaises(RuntimeError),
        ):
            adapter.ping(adapter.source, adapter.destination, succeeds=False)

    def test_unknown_node_does_not_execute_any_command(self):
        with patch.object(g.subprocess, "run") as run:
            self.assertFalse(
                g.Adapter("enterprise-75").execute("other-lab-node", "hostname")[0]
            )
            run.assert_not_called()

    def test_validation_always_repairs_partial_injection_and_keeps_failed_recovery(
        self,
    ):
        for recovery_fails in (False, True):
            with (
                self.subTest(recovery_fails=recovery_fails),
                tempfile.TemporaryDirectory() as folder,
            ):
                adapter = g.Adapter("enterprise-75")
                adapter.ROOT = Path(folder)
                actions = []

                def action(
                    phase,
                    family,
                    actions=actions,
                    recovery_fails=recovery_fails,
                    folder=folder,
                ):
                    actions.append(phase)
                    self.assertIn(family, Lease(folder).read()["pending"])
                    if phase == "inject" or (phase == "repair" and recovery_fails):
                        raise RuntimeError("simulated partial operation")

                with (
                    patch.object(g, "Adapter", return_value=adapter),
                    patch.object(
                        adapter,
                        "baseline",
                        return_value="default via 10.0.0.1 dev eth0",
                    ),
                    patch.object(adapter, "action", side_effect=action),
                    patch.object(
                        g, "evidence_file", return_value=Path(folder) / "evidence.json"
                    ),
                ):
                    result = g.validate("enterprise-75", "link_down")
                self.assertFalse(result["passed"])
                self.assertIn("repair", actions)
                self.assertEqual(
                    Lease(folder).read()["pending"],
                    ["link_down"] if recovery_fails else [],
                )

    def test_stale_evidence_never_enables_benchmark(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "evidence.json"
            path.write_text(json.dumps({"passed": True, "fingerprint": "old"}))
            with (
                patch.object(g, "evidence_file", return_value=path),
                patch.object(g, "support", return_value=(True, "ready")),
            ):
                self.assertFalse(g.validated("enterprise-75", "link_down"))

    def test_existing_backup_prevents_overwriting_recovery_state(self):
        adapter = g.Adapter("enterprise-75")
        with tempfile.TemporaryDirectory() as folder:
            adapter.ROOT = Path(folder)
            path = adapter.backup_path("wrong_gateway")
            path.parent.mkdir(parents=True)
            path.write_text('{"original":"keep"}')
            with self.assertRaises(RuntimeError):
                adapter.save("wrong_gateway")
            self.assertEqual(json.loads(path.read_text()), {"original": "keep"})

    def test_pending_fault_prevents_new_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            adapter = g.Adapter("enterprise-75")
            adapter.ROOT = Path(folder)
            Lease(folder).mark("legacy-fault")
            with (
                patch.object(g, "Adapter", return_value=adapter),
                patch.object(adapter, "baseline"),
                patch.object(adapter, "action") as mutate,
                patch.object(
                    g, "evidence_file", return_value=Path(folder) / "evidence.json"
                ),
            ):
                result = g.validate("enterprise-75", "route_blackhole")
            self.assertFalse(result["passed"])
            mutate.assert_not_called()
            self.assertEqual(Lease(folder).read()["pending"], ["legacy-fault"])

    def test_link_recovery_restores_the_exact_saved_default_route(self):
        adapter = g.Adapter("enterprise-75")
        with tempfile.TemporaryDirectory() as folder:
            adapter.ROOT = Path(folder)
            path = adapter.backup_path("link_down")
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "default_route": "default via 10.30.10.1 dev eth0 metric 77",
                        "fingerprint": g.fingerprint("enterprise-75"),
                    }
                )
            )
            with patch.object(adapter, "require", return_value="") as execute:
                adapter.action("repair", "link_down")
            self.assertEqual(
                execute.call_args.args,
                (
                    adapter.source,
                    "ip link set dev eth0 up && ip route replace default via 10.30.10.1 dev eth0 metric 77",
                ),
            )
            self.assertTrue(
                path.exists(),
                "Keep original state until recovery verification succeeds",
            )

    def test_compiler_reproduces_saved_mapping(self):
        spec = importlib.util.spec_from_file_location(
            "build_generic", TOOLS / "build_generic_faults.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.build(), g.TARGETS)
