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
            "fault_id": "gateway-service-r8",
            "scope": "selected",
            "model": "test-model",
            "repeats": 2,
            "mode": "live",
            "prompt_style": "generic",
            "tool_profile": "atomic",
            "judge_model": "same",
        }
        with patch.object(self.state, "start", return_value=True) as start:
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
                    "gateway-service-r8",
                ),
            )

    def test_invalid_configuration_never_launches_a_run(self):
        valid = {"topology_id": "enterprise-75", "fault_id": "core-uplink"}
        bad_values = {
            "repeats": [0, -1, 11, True, 1.5, "2", None],
            "model": ["", "$(id)", [], "x" * 101],
            "judge_model": [[], "bad model"],
            "scope": ["unknown", []],
            "mode": ["unknown", []],
            "prompt_style": ["unknown", []],
            "tool_profile": ["unknown", []],
        }
        with patch.object(self.state, "start") as start:
            for key, values in bad_values.items():
                for value in values:
                    with self.subTest(key=key, value=value):
                        self.assertEqual(
                            self.request("/api/run", {**valid, key: value}, "POST")[0],
                            400,
                        )
            start.assert_not_called()

    def test_unadapted_topologies_cannot_launch_the_enterprise_runner(self):
        with patch.object(self.state, "start") as start:
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
            patch.object(self.state, "start") as start,
        ):
            status, data = self.request(
                "/api/run",
                {
                    "topology_id": "enterprise-75",
                    "fault_id": "core-uplink",
                    "model": "deepseek-test",
                },
                "POST",
            )
            self.assertEqual(status, 400)
            self.assertIn("DEEPSEEK_API_KEY", data["error"])
            start.assert_not_called()

    def test_report_roundtrip_preserves_results_and_original_scope(self):
        report = {
            "topology_name": "Original enterprise run",
            "attempted": 5,
            "scored": 5,
            "metrics": {"rca_exact": {"rate": 0.6}},
            "runs": [{"model": "fixed-model", "case": "core-uplink"}],
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
