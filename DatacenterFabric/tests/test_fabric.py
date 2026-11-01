"""Regressions for wiring validation, forwarding-path checks and recovery."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from tools.generate import generate, inventory, router_config
from tools.validate import validate


class FabricTests(unittest.TestCase):
    def test_generated_topology_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            self.assertTrue(validate(Path(tmp))['passed'])

    def test_expansion_preserves_original_routing_and_wires(self):
        inv = inventory()
        self.assertEqual(len(inv['nodes']), 75)
        self.assertEqual(len(inv['links']), 84)
        # Reconstruct the original six-rack, four-endpoint fabric.
        original = json.loads(json.dumps(inv))
        original['nodes'] = {n: m for n, m in original['nodes'].items()
                             if m['role'] not in ('client', 'server') or int(n.split('h')[1]) <= 4}
        original['links'] = original['links'][:48]
        for n, m in original['nodes'].items():
            m['ports'] = [p for p in m['ports'] if p['peer'] in original['nodes']]
            self.assertEqual(inv['nodes'][n]['ports'][:len(m['ports'])], m['ports'])
            if m['role'] in ('spine', 'leaf'):
                self.assertEqual(router_config(n, m, original), router_config(n, inv['nodes'][n], inv))
        for rack in range(1, 7):
            self.assertEqual(len(inv['nodes'][f'rack{rack}']['ports']), 11)
            for host in range(1, 11):
                self.assertEqual(inv['nodes'][f'rack{rack}h{host}']['address'], f'10.60.{rack}.{10+host}/24')

    def test_live_checks_cover_all_expanded_endpoints(self):
        with patch.object(lab, 'inventory', return_value=inventory()):
            items = lab.checks()
        sweeps = [i for i in items if 'other endpoints reachable' in i[0]]
        self.assertEqual(len(sweeps), 60)
        for title, node, command in sweeps:
            self.assertIn('all 59 other endpoints', title)
            self.assertEqual(len(command.split('for target in ')[1].split('; do')[0].split()), 59)
        self.assertEqual(sum('dependency healthy' in i[0] for i in items), 60)
        self.assertEqual(sum('11 ports on isolated rack bridge' in i[0] for i in items), 6)

    def test_successful_failover_probes_every_expanded_endpoint(self):
        with patch.object(lab, 'inventory', return_value=inventory()), patch.object(lab, 'check', return_value=0), patch.object(lab, 'execute', return_value=(True, 'ok')) as execute, patch.object(lab.time, 'sleep'), patch.object(lab, 'save_report'):
            self.assertEqual(lab.failover(), 0)
        commands = [call.args[1] for call in execute.call_args_list]
        self.assertEqual(sum('for target in' in c for c in commands), 60)
        self.assertEqual(sum('curl -fsS' in c for c in commands), 60)
        self.assertEqual(execute.call_args_list[-1].args, ('leaf1', 'ip link set eth0 up'))

    def test_validator_rejects_miswired_interface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate(root)
            path=root/'lab.conf'
            path.write_text(path.read_text().replace('leaf1[0]=wire01','leaf1[0]=wire02'))
            with self.assertRaises(AssertionError): validate(root)

    def test_validator_rejects_missing_ebgp_export_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); generate(root)
            path=root/'leaf1/etc/frr/frr.conf'
            path.write_text(path.read_text().replace('neighbor 172.22.0.1 prefix-list LOCAL out','neighbor 172.22.0.1 description missing-filter'))
            with self.assertRaises(AssertionError): validate(root)

    def test_ecmp_requires_installed_distinct_active_paths(self):
        code=shlex.split(lab.ecmp_command('10.60.2.0/24'))[-1]
        hops=[dict(gateway=f'172.22.0.{n}') for n in (1,3,5)]
        examples=[([dict(nexthops=hops)],True),([],False),([dict(gateway='172.22.0.1')],False),([dict(nexthops=hops[:2])],False),([dict(nexthops=[hops[0]]*3)],False),([dict(nexthops=[dict(h,flags=['dead']) for h in hops])],False)]
        for rows,expected in examples:
            with self.subTest(rows=rows):
                result=subprocess.run([sys.executable,'-c',code],input=json.dumps(rows),text=True,capture_output=True)
                self.assertEqual(result.returncode==0,expected)

    def test_partial_injection_is_always_repaired(self):
        with patch.object(lab,'check',return_value=0), patch.object(lab,'execute',side_effect=[(False,'partial failure'),(True,'restored')]) as execute, patch.object(lab.time,'sleep'), patch.object(lab,'save_report') as save:
            self.assertEqual(lab.failover(),1)
            self.assertEqual(execute.call_args_list[-1].args,('leaf1','ip link set eth0 up'))
            self.assertTrue(save.call_args.args[1]['recovered'])
            self.assertFalse(save.call_args.args[1]['passed'])

    def test_unhealthy_baseline_never_changes_network(self):
        with patch.object(lab,'check',return_value=1), patch.object(lab,'execute') as execute, patch.object(lab,'save_report'):
            self.assertEqual(lab.failover(),1)
            execute.assert_not_called()


if __name__=='__main__':
    unittest.main()
