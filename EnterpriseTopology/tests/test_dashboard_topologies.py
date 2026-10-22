"""Validate imported topology identity, shared LAN semantics and API selection."""
import importlib.util
import json
from pathlib import Path
import unittest

DASHBOARD = Path(__file__).resolve().parents[1] / 'dashboard'
spec = importlib.util.spec_from_file_location('dashboard_server', DASHBOARD / 'server.py')
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
        counts = {'multi-as-isp':75,'multisite':80,'jiayuan-75':75,'nika-92':92}
        for key, count in counts.items():
            with self.subTest(topology=key):
                status, data = self.request('/api/topology?id=' + key)
                self.assertEqual(status, 200)
                self.assertFalse(data['evaluation_enabled'])
                self.assertEqual(sum(not n.get('virtual') for n in data['nodes'].values()), count)
                self.assertEqual(len(data['source_commit']), 40)
                for link in data['links']:
                    a, b = link['endpoints']
                    for own, peer in ((a,b),(b,a)):
                        node = data['nodes'][own['node']]
                        self.assertIn(node['role'], ('router','switch','host'))
                        self.assertTrue(any(p['interface']==own['interface'] and p['peer']==peer['node'] for p in node['ports']))

    def test_catalog_and_existing_evaluation_stay_distinct(self):
        status, catalog = self.request('/api/topologies')
        self.assertEqual(status, 200)
        self.assertEqual(len(catalog), 6)
        self.assertEqual([x['id'] for x in catalog if x['evaluation_enabled']], ['enterprise-75'])
        self.assertEqual(self.request('/api/topology?id=enterprise-75')[1]['scenario_count'], 20)
        self.assertEqual(self.request('/api/topology?id=../../secret')[0], 404)
        for excluded in ('datacenter-fabric', 'missing-return-route', 'abilene'):
            self.assertEqual(self.request('/api/topology?id=' + excluded)[0], 404)
