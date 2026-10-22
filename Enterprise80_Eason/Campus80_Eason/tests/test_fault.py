"""Offline regression checks: transport errors must not count as expected faults."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fault', Path(__file__).resolve().parents[1] / 'fault.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

class Checks(unittest.TestCase):
    def lab(self):
        return f.Lab.__new__(f.Lab)

    def test_zero_received_is_expected_fault(self):
        lab = self.lab()
        lab.dev = lambda *a: '2 packets transmitted, 0 received, 100% packet loss\nPING_RC=1\n'
        lab.ping('pc01', '10.10.3.100', False)

    def test_partial_loss_is_not_expected_total_outage(self):
        lab = self.lab()
        lab.dev = lambda *a: '2 packets transmitted, 1 received, 50% packet loss\nPING_RC=0\n'
        with self.assertRaises(f.Failure):
            lab.ping('pc01', '10.10.3.100', False)

    def test_missing_ping_is_not_expected_fault(self):
        lab = self.lab()
        lab.dev = lambda *a: 'ping: not found'
        with self.assertRaises(f.Failure):
            lab.ping('pc01', '10.10.3.100', False)

    def test_exec_failure_is_not_process_absence(self):
        lab = self.lab()
        lab.dev = lambda *a: 'Error: No such container'
        with self.assertRaises(f.Failure):
            lab.process('r01', 'ospfd', False)

    def test_docker_exit_one_rejected(self):
        lab = self.lab()
        lab.say = lambda *a: None
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Docker failure')):
            with self.assertRaises(f.Failure):
                lab.run(['docker', 'exec', 'missing', 'ping'])

    def test_static(self):
        f.static_check()

if __name__ == '__main__':
    unittest.main()
