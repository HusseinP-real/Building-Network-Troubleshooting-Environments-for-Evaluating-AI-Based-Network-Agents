"""Validate imported topology identity, shared LAN semantics and API selection."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"
spec = importlib.util.spec_from_file_location(
    "dashboard_server", DASHBOARD / "server.py"
)
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class DashboardTopologyTests(unittest.TestCase):
    def request(self, path):
        handler = object.__new__(server.Handler)
        handler.path = path
        result = []
        handler._json = lambda status, body: result.append((status, body))
        handler.do_GET()
        return result[0]

    def test_every_imported_device_and_edge_is_explorable(self):
        counts = {
            "multi-as-isp": 75,
            "multisite": 80,
            "jiayuan-75": 75,
            "nika-92": 92,
            "kairos-enterprise": 75,
            "campus80-eason": 80,
            "enterprise80-eason": 80,
        }
        for key, count in counts.items():
            with self.subTest(topology=key):
                status, data = self.request("/api/topology?id=" + key)
                self.assertEqual(status, 200)
                self.assertFalse(data["evaluation_enabled"])
                self.assertEqual(
                    sum(not n.get("virtual") for n in data["nodes"].values()), count
                )
                self.assertEqual(len(data["source_commit"]), 40)
                for link in data["links"]:
                    a, b = link["endpoints"]
                    for own, peer in ((a, b), (b, a)):
                        node = data["nodes"][own["node"]]
                        self.assertIn(node["role"], ("router", "switch", "host"))
                        self.assertTrue(
                            any(
                                p["interface"] == own["interface"]
                                and p["peer"] == peer["node"]
                                for p in node["ports"]
                            )
                        )

    def test_catalog_and_existing_evaluation_stay_distinct(self):
        status, catalog = self.request("/api/topologies")
        self.assertEqual(status, 200)
        self.assertEqual(len(catalog), 9)
        self.assertEqual(
            [x["id"] for x in catalog if x["evaluation_enabled"]], ["enterprise-75"]
        )
        self.assertEqual(
            self.request("/api/topology?id=enterprise-75")[1]["scenario_count"], 20
        )
        self.assertEqual(self.request("/api/topology?id=../../secret")[0], 404)
        for excluded in (
            "datacenter-fabric",
            "missing-return-route",
            "abilene",
            "kairos-kath3",
            "sarah-enterprise",
            "sarah-service",
        ):
            self.assertEqual(self.request("/api/topology?id=" + excluded)[0], 404)

    def test_new_native_catalogs_preserve_identity_without_enabling_execution(self):
        for key, count, target in [
            ("kairos-enterprise", 8, "infra"),
            ("campus80-eason", 1, "r01"),
            ("enterprise80-eason", 1, "sydr1"),
        ]:
            with self.subTest(topology=key):
                status, rows = self.request("/api/faults?topology_id=" + key)
                self.assertEqual(status, 200)
                self.assertEqual(len(rows), count)
                self.assertTrue(any(target in row["targets"] for row in rows))
                self.assertEqual(len({row["id"] for row in rows}), count)
                inventory = self.request("/api/topology?id=" + key)[1]
                self.assertEqual(
                    set(inventory["scenarios"]), {row["id"] for row in rows}
                )
                for row in rows:
                    self.assertFalse(row["execution_enabled"])
                    self.assertFalse(row["evaluation_enabled"])
                    self.assertTrue(
                        (DASHBOARD.parents[1] / row["source_path"]).is_file()
                    )

    def test_saved_snapshots_reproduce_from_their_pinned_revision(self):
        spec = importlib.util.spec_from_file_location(
            "import_topologies",
            DASHBOARD.parent / "tools/import_dashboard_topologies.py",
        )
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        commit = json.loads((DASHBOARD / "topologies/campus80-eason.json").read_text())[
            "source_commit"
        ]
        with tempfile.TemporaryDirectory() as directory:
            importer.OUT = Path(directory)
            importer.export(commit)
            for generated in importer.OUT.iterdir():
                self.assertEqual(
                    generated.read_bytes(),
                    (DASHBOARD / "topologies" / generated.name).read_bytes(),
                    generated.name,
                )
        excluded = json.loads((DASHBOARD / "topologies/excluded.json").read_text())
        self.assertTrue(
            all(
                row["device_count"] < 75 and row["source_commit"] == commit
                for row in excluded
            )
        )
