"""Offline regression checks for scoring and experiment state isolation."""

import asyncio
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import sade_benchmark as bench
import sade_eval as ev


def prediction(case):
    gt = ev.CASES[case]["ground_truth"]
    causes = ev.expected_causes(case)
    return {
        "is_anomaly": gt["is_anomaly"],
        "resource_id": gt["resource_id"],
        "fault_type": gt["fault_type"],
        "faulty_devices": sorted({c["device"] for c in causes}),
        "root_causes": copy.deepcopy(causes),
        "repair_actions": [
            {"device": r["device"], "command": r["command"]} for r in gt["remediation"]
        ],
        "diagnosis_text": gt["root_cause"],
        "repair_text": "Targeted recovery for the observed causes.",
    }


QUALITY = {
    "explanation_correct": True,
    "repair_correct": True,
    "explanation_reason": "Correct observed mechanism.",
    "repair_reason": "Targeted repair.",
}


class RobustnessTests(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("claude_agent_sdk"), "Requires NIKA SDK environment"
    )
    def test_no_tools_mode_has_no_mcp_or_builtin_tools(self):
        captured = []

        async def fake_query(*, prompt, options):
            captured.append(options)
            if False:
                yield None

        with patch("claude_agent_sdk.query", fake_query):
            asyncio.run(
                ev._run_sade("ticket", Path("/tmp/nika"), 30, "test", "no-tools")
            )
            asyncio.run(
                ev._run_sade(
                    "ticket", Path("/tmp/nika"), 30, "test", "live", "guided", "sweep"
                )
            )
        control, live = captured
        self.assertEqual(control.tools, [])
        self.assertEqual(control.mcp_servers, {})
        self.assertEqual(control.allowed_tools, [])
        self.assertEqual(control.setting_sources, [])
        self.assertEqual(len(live.mcp_servers), 2)
        self.assertIn("Skill", live.tools)

    def test_all_case_answers_and_wrong_detection(self):
        for name in ev.CASES:
            with self.subTest(case=name):
                answer = prediction(name)
                self.assertTrue(ev.score_prediction(name, answer)["rca_exact"])
                answer["is_anomaly"] = not answer["is_anomaly"]
                self.assertFalse(ev.score_prediction(name, answer)["rca_exact"])

    def test_extra_devices_and_wrong_root_cause_fail(self):
        answer = prediction("core-uplink")
        answer["faulty_devices"].append("r6")
        self.assertFalse(ev.score_prediction("core-uplink", answer)["device_correct"])
        self.assertFalse(ev.score_prediction("core-uplink", answer)["rca_exact"])
        for field in ("resource_id", "fault_type"):
            answer = prediction("core-uplink")
            answer[field] = "wrong"
            self.assertFalse(ev.score_prediction("core-uplink", answer)["rca_exact"])
        self.assertFalse(ev.score_prediction("core-uplink", {})["rca_exact"])

    def test_invalid_output_rejected(self):
        for text in (
            "",
            "=== DIAGNOSIS ===\nis_anomaly: maybe",
            "=== DIAGNOSIS ===\nis_anomaly: true\nis_anomaly: false",
            "=== DIAGNOSIS ===\n=== DIAGNOSIS ===",
        ):
            with self.assertRaises(ValueError):
                ev.parse_prediction(text)

    def test_variants_have_same_hidden_state(self):
        for name, case in ev.CASES.items():
            if case["fault"]:
                self.assertEqual(
                    case["ground_truth"], ev.CASES[case["fault"]]["ground_truth"]
                )
            self.assertNotIn(case["ground_truth"]["root_cause"], ev.prompt_for(name))
            self.assertNotIn("ground_truth", ev.prompt_for(name))

    def test_errors_in_denominator_and_healthy_false_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, (name, status, answer) in enumerate(
                [
                    ("core-uplink", "scored", prediction("core-uplink")),
                    ("database-acl", "error", None),
                    ("healthy-outage", "scored", prediction("core-uplink")),
                    ("healthy-policy", "error", None),
                ]
            ):
                data = {"case": name, "status": status}
                if answer:
                    data["score"] = ev.score_prediction(name, answer)
                p = Path(tmp) / f"{i}.json"
                p.write_text(json.dumps(data))
                paths.append(p)
            report = bench.summarize(paths)
            self.assertEqual(report["metrics"]["rca_exact"]["rate"], 0.25)
            self.assertEqual(report["healthy_false_positive"]["rate"], 1)
            self.assertEqual(report["healthy_false_positive"]["unscored"], 1)
            self.assertEqual(report["by_category"]["healthy"]["denominator"], 2)
        self.assertLess(bench.proportion(3, 3)["ci95"][0], 0.5)

    def test_healthy_case_never_injects_and_verifies_restoration(self):
        async def fake_agent(*args):
            return {
                "final_text": "=== DIAGNOSIS ===\nis_anomaly: false\nresource_id: none\nfault_type: none\nfaulty_devices: none\ndiagnosis_text: No fault found.\n=== END ==="
            }

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(ev, "ROOT", Path(tmp)),
            patch.object(ev, "_preflight"),
            patch.object(ev.lab, "check", return_value=0) as check,
            patch.object(ev.lab, "execute") as execute,
            patch.object(ev, "_run_sade", fake_agent),
            patch.object(ev, "_judge_prediction", return_value=QUALITY),
        ):
            data = json.loads(
                ev.run_case("healthy-outage", Path(tmp), 30, "test").read_text()
            )
            execute.assert_not_called()
            self.assertEqual(check.call_count, 2)
            self.assertTrue(data["state_verified"])
            self.assertTrue(data["environment_restored"])
            self.assertFalse(data["injection_verified"])
            self.assertTrue(data["score"]["rca_exact"])

    def test_fault_is_restored_even_when_agent_fails(self):
        async def fail(*args):
            raise RuntimeError("model unavailable")

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(ev, "ROOT", Path(tmp)),
            patch.object(ev, "_preflight"),
            patch.object(ev.lab, "check", return_value=0),
            patch.object(ev.lab, "execute", return_value=(True, "")) as execute,
            patch.object(ev.time, "sleep"),
            patch.object(ev, "_run_sade", fail),
        ):
            data = json.loads(
                ev.run_case("core-uplink-misleading", Path(tmp), 30, "test").read_text()
            )
            self.assertEqual(data["status"], "error")
            self.assertTrue(data["environment_restored"])
            self.assertIn(
                ("r5", "ip link set eth0 up"), [c.args for c in execute.call_args_list]
            )

    def test_wrong_explanation_and_repair_cannot_receive_full_credit(self):
        answer = prediction("core-uplink")
        self.assertTrue(
            ev.score_prediction("core-uplink", answer, QUALITY)["full_correct"]
        )
        wrong_explanation = {
            **QUALITY,
            "explanation_correct": False,
            "explanation_reason": "Claims database crash instead of interface shutdown.",
        }
        answer["diagnosis_text"] = "The database crashed."
        result = ev.score_prediction("core-uplink", answer, wrong_explanation)
        self.assertTrue(result["rca_exact"])
        self.assertFalse(result["explanation_correct"])
        self.assertFalse(result["full_correct"])
        answer = prediction("core-uplink")
        answer["repair_actions"] = [{"device": "r6", "command": "ip link set eth0 up"}]
        self.assertFalse(
            ev.score_prediction("core-uplink", answer, QUALITY)["repair_correct"]
        )
        answer["repair_actions"] = [
            {"device": "r5", "command": "ip link set eth0 down"}
        ]
        self.assertFalse(
            ev.score_prediction("core-uplink", answer, QUALITY)["full_correct"]
        )
        answer["repair_actions"] = [
            {"device": "r5", "command": "ip link set eth0 up; pkill keepalived"}
        ]
        self.assertFalse(
            ev.score_prediction("core-uplink", answer, QUALITY)["full_correct"]
        )
        answer = prediction("core-uplink")
        result = ev.score_prediction(
            "core-uplink", answer, {**QUALITY, "repair_correct": False}
        )
        self.assertFalse(result["repair_correct"])
        self.assertFalse(result["full_correct"])

    def test_compound_requires_all_causes_and_all_repairs(self):
        answer = prediction("compound-uplink-acl")
        self.assertTrue(
            ev.score_prediction("compound-uplink-acl", answer, QUALITY)["full_correct"]
        )
        answer["root_causes"].reverse()
        answer["repair_actions"].reverse()
        self.assertTrue(
            ev.score_prediction("compound-uplink-acl", answer, QUALITY)["full_correct"]
        )
        answer["root_causes"].pop()
        self.assertFalse(
            ev.score_prediction("compound-uplink-acl", answer, QUALITY)["rca_exact"]
        )
        answer = prediction("compound-uplink-acl")
        answer["repair_actions"].pop()
        self.assertFalse(
            ev.score_prediction("compound-uplink-acl", answer, QUALITY)["full_correct"]
        )
        answer = prediction("compound-uplink-acl")
        (
            answer["root_causes"][0]["fault_type"],
            answer["root_causes"][1]["fault_type"],
        ) = (
            answer["root_causes"][1]["fault_type"],
            answer["root_causes"][0]["fault_type"],
        )
        self.assertFalse(
            ev.score_prediction("compound-uplink-acl", answer, QUALITY)["rca_exact"]
        )

    def test_healthy_unnecessary_repair_and_missing_judge(self):
        answer = prediction("healthy-policy")
        self.assertTrue(
            ev.score_prediction("healthy-policy", answer, QUALITY)["full_correct"]
        )
        answer["repair_actions"] = [{"device": "app", "command": "iptables -F"}]
        self.assertFalse(
            ev.score_prediction("healthy-policy", answer, QUALITY)["full_correct"]
        )
        result = ev.score_prediction("core-uplink", prediction("core-uplink"))
        self.assertIsNone(result["full_correct"])
        self.assertIsNone(result["explanation_correct"])

    def test_v3_parser_separates_explanation_and_repair(self):
        answer = prediction("compound-uplink-acl")
        text = (
            "=== DIAGNOSIS ===\nis_anomaly: true\nresource_id: multiple\nfault_type: multiple\n"
            "faulty_devices: r6, database\nroot_causes: "
            + json.dumps(answer["root_causes"])
            + "\nrepair_actions: "
            + json.dumps(answer["repair_actions"])
            + "\ndiagnosis_text:\nTwo independent causes.\nrepair_text:\nRestore both.\n=== END ==="
        )
        parsed = ev.parse_prediction(text)
        self.assertEqual(parsed["diagnosis_text"], "Two independent causes.")
        self.assertEqual(parsed["repair_text"], "Restore both.")
        self.assertTrue(
            ev.score_prediction("compound-uplink-acl", parsed, QUALITY)["full_correct"]
        )

    @unittest.skipUnless(
        importlib.util.find_spec("claude_agent_sdk"), "Requires NIKA SDK environment"
    )
    def test_judge_schema_and_isolation_fail_closed(self):
        from claude_agent_sdk import ResultMessage

        captured = []
        verdict = dict(QUALITY)

        async def fake_query(*, prompt, options):
            captured.append((json.loads(prompt), options))
            yield ResultMessage(
                "success", 1, 1, False, 1, "test", result=json.dumps(verdict)
            )

        with patch("claude_agent_sdk.query", fake_query):
            quality = asyncio.run(
                ev._judge_prediction(
                    "core-uplink", prediction("core-uplink"), {}, "test", "live"
                )
            )
            self.assertTrue(quality["explanation_correct"])
            payload, options = captured[0]
            self.assertIn("ground_truth", payload)
            self.assertEqual(options.tools, [])
            self.assertEqual(options.setting_sources, [])
            self.assertEqual(options.mcp_servers, {})
            verdict["explanation_correct"] = "true"
            with self.assertRaises(ValueError):
                asyncio.run(
                    ev._judge_prediction(
                        "core-uplink", prediction("core-uplink"), {}, "test", "live"
                    )
                )

    def test_quality_failure_preserves_fields_without_full_credit(self):
        prediction("healthy-policy")
        final = (
            "=== DIAGNOSIS ===\nis_anomaly: false\nresource_id: none\nfault_type: none\n"
            "faulty_devices: none\nroot_causes: []\nrepair_actions: []\n"
            "diagnosis_text:\nHealthy policy.\nrepair_text:\nNo changes.\n=== END ==="
        )

        async def agent(*args):
            return {"final_text": final}

        async def judge(*args):
            raise RuntimeError("Judge unavailable")

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(ev, "ROOT", Path(tmp)),
            patch.object(ev, "_preflight"),
            patch.object(ev.lab, "check", return_value=0),
            patch.object(ev, "_run_sade", agent),
            patch.object(ev, "_judge_prediction", judge),
        ):
            data = json.loads(
                ev.run_case("healthy-policy", Path(tmp), 30, "test").read_text()
            )
            self.assertTrue(data["score"]["rca_exact"])
            self.assertIsNone(data["score"]["full_correct"])
            self.assertIn("quality_error", data)
            report = bench.summarize([next(Path(tmp).glob("results/sade/*/*.json"))])
            self.assertEqual(report["quality_scored"], 0)
            self.assertEqual(report["metrics"]["full_correct"]["unscored"], 1)

    def test_compound_partial_injection_cleanup(self):
        async def fail(*args):
            raise RuntimeError("model unavailable")

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(ev, "ROOT", Path(tmp)),
            patch.object(ev, "_preflight"),
            patch.object(ev.lab, "check", return_value=0),
            patch.object(ev.lab, "execute", return_value=(True, "")) as execute,
            patch.object(ev.time, "sleep"),
            patch.object(ev, "_run_sade", fail),
        ):
            data = json.loads(
                ev.run_case("compound-uplink-acl", Path(tmp), 30, "test").read_text()
            )
            self.assertTrue(data["environment_restored"])
            repairs = [
                (ev.lab.FAULTS[f][0], ev.lab.FAULTS[f][2])
                for f in reversed(ev.case_faults("compound-uplink-acl"))
            ]
            calls = [c.args for c in execute.call_args_list]
            self.assertLess(calls.index(repairs[0]), calls.index(repairs[1]))

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "Requires MCP environment")
    def test_diagnostic_paths_reject_traversal_and_credentials(self):
        import sade_lab_mcp as mcp

        for command in (
            "cat /etc/frr/../../../shared/tools/sade_cases.json",
            "cat /proc/1/environ",
            "cat /proc/self/root/shared/tools/sade_cases.json",
        ):
            self.assertIsNone(mcp._safe_command(command))
        self.assertIsNotNone(mcp._safe_command("cat /etc/frr/frr.conf"))
        self.assertIsNotNone(mcp._safe_command("cat /sys/class/net/eth0/operstate"))

    def test_partial_injection_error_restores_every_attempted_fault(self):
        faults = ev.case_faults("compound-uplink-acl")
        failed_command = ev.lab.FAULTS[faults[1]][1]

        def execute(node, command):
            return (
                command != failed_command,
                "injection failed" if command == failed_command else "",
            )

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(ev, "ROOT", Path(tmp)),
            patch.object(ev, "_preflight"),
            patch.object(ev.lab, "check", return_value=0),
            patch.object(ev.lab, "execute", side_effect=execute) as calls,
            patch.object(ev.time, "sleep"),
            patch.object(ev, "_run_sade") as agent,
        ):
            data = json.loads(
                ev.run_case("compound-uplink-acl", Path(tmp), 30, "test").read_text()
            )
            agent.assert_not_called()
            self.assertEqual(data["status"], "error")
            self.assertTrue(data["environment_restored"])
            for fault in faults:
                self.assertIn(
                    (ev.lab.FAULTS[fault][0], ev.lab.FAULTS[fault][2]),
                    [c.args for c in calls.call_args_list],
                )

    def test_ablation_summary_keeps_profiles_and_unknown_quality_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for i, (style, tools, quality) in enumerate(
                [
                    ("generic", "atomic", None),
                    ("generic", "sweep", QUALITY),
                    ("guided", "atomic", QUALITY),
                    ("guided", "sweep", QUALITY),
                ]
            ):
                data = {
                    "case": "core-uplink",
                    "status": "scored",
                    "mode": "live",
                    "scorer_version": ev.SCORER_VERSION,
                    "prompt_style": style,
                    "tool_profile": tools,
                    "score": ev.score_prediction(
                        "core-uplink", prediction("core-uplink"), quality
                    ),
                }
                path = Path(tmp) / f"{i}.json"
                path.write_text(json.dumps(data))
                paths.append(path)
            report = bench.summarize(paths)
            self.assertEqual(len(report["by_experiment"]), 4)
            self.assertEqual(report["quality_scored"], 3)
            self.assertIsNone(
                report["by_experiment"]["live/generic/atomic"]["metrics"][
                    "full_correct"
                ]["rate"]
            )
            self.assertNotIn(
                "guided_minus_generic/atomic/full_correct", report["ablation_deltas"]
            )
            self.assertEqual(report["metrics"]["full_correct"]["rate"], 0.75)


if __name__ == "__main__":
    unittest.main()
