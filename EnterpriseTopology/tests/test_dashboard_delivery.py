"""Real loopback HTTP tests of selection, rejection and report retrieval.

The process launcher is replaced only at the paid-model/runtime boundary.
These tests do not establish that a network scenario or an agent succeeded.
"""

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))
import server


class DashboardDeliveryTests(unittest.TestCase):
    def setUp(self):
        credentials = patch.dict(server.os.environ, {"ANTHROPIC_API_KEY": "fake-test-api-key"})
        credentials.start()
        self.addCleanup(credentials.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.state = server.RunState(Path(sys.executable), self.directory)
        results = patch.object(server, "RESULTS", self.directory)
        results.start()
        self.addCleanup(results.stop)
        handler = type(
            "DeliveryHandler",
            (server.Handler,),
            {
                "state": self.state,
                "log_message": lambda *args: None,
            },
        )
        self.http = server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def request(self, path, payload=None, method="GET", raw=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.http.server_port, timeout=5
        )
        self.addCleanup(connection.close)
        body = (
            raw
            if raw is not None
            else json.dumps(payload)
            if method == "POST"
            else None
        )
        connection.request(method, path, body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        content = response.read()
        return response.status, json.loads(
            content
        ) if "application/json" in response.getheader("Content-Type", "") else content

    def test_selected_fault_and_model_reach_existing_runner_unchanged(self):
        payload = {
            "topology_id": "enterprise-75",
            "fault_id": "link_down",
            "scope": "selected",
            "model": "test-model",
            "repeats": 2,
            "mode": "live",
            "prompt_style": "generic",
            "tool_profile": "atomic",
            "judge_model": "same",
        }
        with patch.object(server.generic_faults, "validated", return_value=True), patch.object(self.state, "start", return_value=True) as start:
            self.assertEqual(self.request("/api/run", payload, "POST")[0], 202)
            self.assertEqual(
                start.call_args.args,
                (
                    "test-model",
                    2,
                    "live",
                    "generic",
                    "atomic",
                    None,
                    "link_down",
                    "enterprise-75",
                ),
            )

    def test_original_suite_routes_all_twenty_tickets_to_native_runner(self):
        payload = {"topology_id": "enterprise-75", "fault_id": "link_down",
                   "scope": "enterprise20", "model": "claude-opus-5-5",
                   "judge_model": "claude-haiku-5-5", "repeats": 1}
        with patch.object(server.generic_faults, "validated", return_value=False), patch.object(self.state, "start", return_value=True) as start:
            self.assertEqual(self.request("/api/run", payload, "POST")[0], 202)
            self.assertEqual(start.call_args.args,
                             ("claude-opus-5-5", 1, "live", "generic", "atomic",
                              "claude-haiku-5-5", None, "enterprise-75"))
            self.assertEqual(start.call_args.kwargs, {"enterprise20": True})
            payload["topology_id"] = "multisite"
            self.assertEqual(self.request("/api/run", payload, "POST")[0], 400)
            self.assertEqual(start.call_count, 1)

    def test_original_suite_counts_repeats_and_preserves_pending_fault_lock(self):
        from environment_guard import Conflict
        with patch.object(server, "native_support", return_value=(True, "ready")), patch.object(self.state.operations, "reserve_auto", side_effect=Conflict("Recover pending faults")):
            with self.assertRaises(Conflict):
                self.state.start("test", 5, enterprise20=True)
            self.assertFalse(self.state.running)
        with patch.object(server, "native_support", return_value=(True, "ready")), patch.object(self.state.operations, "reserve_auto"), patch.object(server.threading, "Thread"):
            self.assertTrue(self.state.start("test", 5, enterprise20=True))
            self.assertEqual(self.state.snapshot()["case_count"], 20)
            self.assertEqual(self.state.snapshot()["repeats"], 5)

    def test_original_suite_uses_twenty_turn_budget_and_clears_generic_environment(self):
        from unittest.mock import MagicMock
        process = MagicMock()
        process.stdout = iter([])
        process.wait.return_value = 0
        lease = MagicMock()
        lease.file.fileno.return_value = 9
        with patch.dict(server.os.environ, {"SADE_GENERIC_TOPOLOGY": "multisite"}), patch.object(server.subprocess, "Popen", return_value=process) as launch:
            self.state._run("claude-opus-5-5", 1, judge_model="claude-haiku-5-5",
                            lease=lease, enterprise20=True)
        command = launch.call_args.args[0]
        self.assertEqual(command[command.index("--max-turns") + 1], "20")
        self.assertEqual(command[command.index("--seed") + 1], "42")
        self.assertNotIn("--cases", command)
        self.assertNotIn("SADE_GENERIC_TOPOLOGY", launch.call_args.kwargs["env"])
        lease.release.assert_called_once()

    def test_gpt_subscription_agent_and_judge_do_not_require_anthropic_key(self):
        with patch.dict(server.os.environ, {}, clear=True), patch.object(self.state, "start", return_value=True) as start:
            payload = {"topology_id": "enterprise-75", "fault_id": "link_down", "scope": "enterprise20", "model": "gpt-6.1-sol", "judge_model": "gpt-6.1-terra"}
            status, _ = self.request("/api/run", payload, "POST")
            self.assertEqual(status, 202)
            self.assertEqual(start.call_args.args[0], "gpt-6.1-sol")
            self.assertEqual(start.call_args.args[5], "gpt-6.1-terra")
            payload["judge_model"] = "claude-haiku-5-5"
            self.assertEqual(self.request("/api/run", payload, "POST")[0], 202)
            self.assertEqual(start.call_count, 2)

    def test_invalid_configuration_never_launches_a_run(self):
        valid = {"topology_id": "enterprise-75", "fault_id": "link_down"}
        bad_values = {
            "repeats": [0, -1, 11, True, 1.5, "2", None],
            "model": ["", "$(id)", [], "x" * 101],
            "judge_model": [[], "bad model"],
            "scope": ["unknown", []],
            "mode": ["unknown", []],
            "prompt_style": ["unknown", []],
            "tool_profile": ["unknown", []],
        }
        with patch.object(server.generic_faults, "validated", return_value=True), patch.object(self.state, "start") as start:
            for key, values in bad_values.items():
                for value in values:
                    with self.subTest(key=key, value=value):
                        self.assertEqual(
                            self.request("/api/run", {**valid, key: value}, "POST")[0],
                            400,
                        )
            start.assert_not_called()

    def test_unadapted_topologies_cannot_launch_the_enterprise_runner(self):
        with patch.object(server.generic_faults, "validated", return_value=False), patch.object(self.state, "start") as start:
            for topology in server.topologies():
                if topology == "enterprise-75":
                    continue
                fault = server.catalog(topology)[0]["id"]
                self.assertEqual(
                    self.request(
                        "/api/run", {"topology_id": topology, "fault_id": fault}, "POST"
                    )[0],
                    400,
                )
            start.assert_not_called()

    def test_new_catalogs_reject_manual_execution_without_creating_a_lease(self):
        with patch.object(server.generic_faults, "support", return_value=(False, "Lab source unavailable")), patch.object(self.state.operations, "lease") as lease:
            for topology in (
                "kairos-enterprise",
                "campus80-eason",
                "enterprise80-eason",
            ):
                for fault in server.catalog(topology):
                    with self.subTest(topology=topology, fault=fault["id"]):
                        status, body = self.request(
                            "/api/manual",
                            {
                                "topology_id": topology,
                                "fault_id": fault["id"],
                                "action": "inject",
                            },
                            "POST",
                        )
                        self.assertEqual(status, 400)
                        self.assertIn("Lab source unavailable", body["error"])
            lease.assert_not_called()

    def test_malformed_or_oversized_body_never_launches_a_run(self):
        with patch.object(self.state, "start") as start:
            for raw in ("{broken", "null", "[]", " ", "x" * 4097):
                with self.subTest(body=raw[:20]):
                    self.assertEqual(
                        self.request("/api/run", method="POST", raw=raw)[0], 400
                    )
            start.assert_not_called()

    def test_missing_provider_credentials_do_not_launch_a_paid_request(self):
        with (
            patch.dict(server.os.environ, {}, clear=True),
            patch.object(server.generic_faults, "validated", return_value=True),
            patch.object(self.state, "start") as start,
        ):
            status, data = self.request(
                "/api/run",
                {
                    "topology_id": "enterprise-75",
                    "fault_id": "link_down",
                    "model": "deepseek-test",
                },
                "POST",
            )
            self.assertEqual(status, 400)
            self.assertIn("DEEPSEEK_API_KEY", data["error"])
            for models in (
                {"model": "gemini-3.8-flash", "judge_model": "same"},
                {"model": "claude-haiku-5-5", "judge_model": "gemini-3.8-flash"},
            ):
                status, data = self.request("/api/run", {
                    "topology_id": "enterprise-75", "fault_id": "link_down", **models,
                }, "POST")
                self.assertEqual(status, 400)
                self.assertIn("GEMINI_API_KEY", data["error"])
            start.assert_not_called()

    def test_report_roundtrip_preserves_results_and_original_scope(self):
        report = {
            "topology_name": "Original enterprise run",
            "attempted": 5,
            "scored": 5,
            "metrics": {"rca_exact": {"rate": 0.6}},
            "runs": [{"model": "fixed-model", "case": "link_down"}],
        }
        (self.directory / "benchmark-delivery.json").write_text(json.dumps(report))
        status, index = self.request("/api/reports")
        self.assertEqual(status, 200)
        self.assertEqual(index[0]["exact_rate"], 0.6)
        # Changing the selected map must not relabel or alter a saved report.
        self.assertEqual(self.request("/api/topology?id=multisite")[0], 200)
        status, loaded = self.request("/api/report?id=benchmark-delivery.json")
        self.assertEqual(status, 200)
        self.assertEqual(loaded, report)

    def test_corrupt_report_does_not_break_the_report_list(self):
        for name, value in {
            "broken": "{",
            "array": "[]",
            "null": "null",
            "runs": '{"runs":[null]}',
            "metrics": '{"metrics":[]}',
        }.items():
            (self.directory / f"benchmark-{name}.json").write_text(value)
        (self.directory / "benchmark-good.json").write_text('{"attempted":0,"runs":[]}')
        status, index = self.request("/api/reports")
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in index], ["benchmark-good.json"])

    def test_unknown_report_and_path_traversal_are_rejected(self):
        for name in ("missing.json", "../../lab.py", "%2e%2e%2f%2e%2e%2flab.py"):
            self.assertEqual(self.request("/api/report?id=" + name)[0], 404)
        self.assertEqual(self.request("/not-an-endpoint")[0], 404)


if __name__ == "__main__":
    unittest.main()
