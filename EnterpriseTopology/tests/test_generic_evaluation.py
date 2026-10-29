"""Exercise selected-topology evaluator/MCP boundaries without model or lab calls."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import generic_faults


def load(name, topology):
    spec = importlib.util.spec_from_file_location(
        "generic_test_" + name, TOOLS / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {"SADE_GENERIC_TOPOLOGY": topology}):
        spec.loader.exec_module(module)
    return module


class GenericEvaluationTests(unittest.TestCase):
    def test_every_topology_has_scoped_cases_and_public_resources(self):
        for topology in generic_faults.TARGETS:
            with self.subTest(topology=topology):
                evaluator = load("sade_eval", topology)
                self.assertEqual(evaluator.ROOT, generic_faults.root(topology))
                self.assertEqual(set(evaluator.CASES), set(generic_faults.FAMILIES))
                for key, case in evaluator.CASES.items():
                    prompt = evaluator.prompt_for(key)
                    real_count = sum(
                        not node.get("virtual")
                        for node in evaluator.INVENTORY["nodes"].values()
                    )
                    self.assertIn(f"{real_count} real devices", prompt)
                    self.assertNotIn(case["ground_truth"]["root_cause"], prompt)
                    self.assertNotIn("192.0.2.254", prompt)
                    for cause in evaluator.expected_causes(key):
                        self.assertIn(
                            cause["resource_id"],
                            evaluator._resource_catalog().splitlines(),
                        )
                        self.assertIn(cause["device"], evaluator.INVENTORY["nodes"])

    def test_selected_lab_runs_recovery_and_preserves_topology_in_report(self):
        evaluator = load("sade_eval", "multisite")
        case = evaluator.CASES["wrong_gateway"]["ground_truth"]
        prediction = (
            "=== DIAGNOSIS ===\nis_anomaly: true\n"
            f"resource_id: {case['resource_id']}\nfault_type: wrong_gateway\n"
            f"faulty_devices: {case['device']}\n"
            f"root_causes: {json.dumps(evaluator.expected_causes('wrong_gateway'))}\n"
            f"repair_actions: {json.dumps([{k: v for k, v in r.items() if k != 'alternatives'} for r in case['remediation']])}\n"
            "diagnosis_text:\nObserved incorrect default route.\nrepair_text:\nRestore the original gateway.\n=== END ==="
        )
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            with (
                patch.object(evaluator, "ROOT", directory),
                patch.object(evaluator, "PROJECT_ROOT", directory),
                patch.object(evaluator.lab, "ROOT", directory),
                patch.object(evaluator, "_preflight"),
                patch.object(generic_faults, "validated", return_value=True),
                patch.object(evaluator.lab, "check", return_value=0),
                patch.object(
                    evaluator.lab, "execute", return_value=(True, "verified")
                ) as execute,
                patch.object(evaluator.time, "sleep"),
                patch.object(
                    evaluator,
                    "_run_sade",
                    new=AsyncMock(return_value={"final_text": prediction}),
                ),
                patch.object(
                    evaluator,
                    "_judge_prediction",
                    new=AsyncMock(
                        return_value={
                            "explanation_correct": True,
                            "repair_correct": True,
                        }
                    ),
                ),
            ):
                data = json.loads(
                    evaluator.run_case(
                        "wrong_gateway", directory, 5, "MOCK"
                    ).read_text()
                )
            self.assertEqual(data["topology_id"], "multisite")
            self.assertEqual(data["status"], "scored")
            self.assertTrue(data["score"]["rca_exact"])
            self.assertTrue(data["environment_restored"])
            self.assertEqual(
                [call.args[1] for call in execute.call_args_list],
                [
                    "@inject:wrong_gateway",
                    "@verify:wrong_gateway",
                    "@repair:wrong_gateway",
                    "@repaired:wrong_gateway",
                ],
            )
            self.assertEqual(
                json.loads((directory / "results/control/state.json").read_text())[
                    "pending"
                ],
                [],
            )

    def test_unvalidated_case_never_calls_model(self):
        evaluator = load("sade_eval", "multisite")
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(evaluator, "ROOT", Path(folder)),
            patch.object(generic_faults, "validated", return_value=False),
            patch.object(evaluator, "_preflight") as preflight,
        ):
            with self.assertRaises(RuntimeError):
                evaluator.run_case("link_down", Path(folder), 5, "MOCK")
            preflight.assert_not_called()

    def test_failed_injection_is_recovered_without_a_model_attempt(self):
        evaluator = load("sade_eval", "multisite")
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)

            def execute(node, command):
                return (
                    (False, "injected state absent")
                    if command == "@verify:link_down"
                    else (True, "ok")
                )

            with (
                patch.object(evaluator, "ROOT", directory),
                patch.object(evaluator, "PROJECT_ROOT", directory),
                patch.object(evaluator.lab, "ROOT", directory),
                patch.object(evaluator, "_preflight"),
                patch.object(generic_faults, "validated", return_value=True),
                patch.object(evaluator.lab, "check", return_value=0),
                patch.object(evaluator.lab, "execute", side_effect=execute),
                patch.object(evaluator.time, "sleep"),
                patch.object(evaluator, "_run_sade") as agent,
            ):
                data = json.loads(
                    evaluator.run_case("link_down", directory, 5, "MOCK").read_text()
                )
            agent.assert_not_called()
            self.assertFalse(data["state_verified"])
            self.assertEqual(data["failure_kind"], "injection_error")
            self.assertTrue(data["environment_restored"])
        import sade_benchmark as benchmark

        with patch.object(benchmark.sade_eval, "GENERIC_TOPOLOGY", "multisite"):
            metric = benchmark.summarize_metric(
                [{"state_verified": False, "score": None}], "rca_exact"
            )
            self.assertEqual(metric["denominator"], 0)
            self.assertIsNone(metric["rate"])

    def test_diagnostics_are_scoped_and_cannot_mutate(self):
        diagnostics = load("sade_lab_mcp", "multisite")
        with patch.object(
            diagnostics.lab, "execute", return_value=(True, "read only")
        ) as execute:
            self.assertFalse(diagnostics._query("foreign-container", "hostname")["ok"])
            execute.assert_not_called()
            self.assertTrue(diagnostics._query("ba_h01", "ip route show")["ok"])
            self.assertIsNone(diagnostics._safe_command("ip link set eth0 down"))
            self.assertIsNone(
                diagnostics._safe_command("cat /tmp/generic-original-link_down.json")
            )
