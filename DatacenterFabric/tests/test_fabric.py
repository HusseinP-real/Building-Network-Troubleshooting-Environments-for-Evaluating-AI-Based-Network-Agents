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
from tools.generate import generate
from tools.validate import validate


class FabricTests(unittest.TestCase):
    def test_generated_topology_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate(Path(tmp))
            self.assertTrue(validate(Path(tmp))['passed'])

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
