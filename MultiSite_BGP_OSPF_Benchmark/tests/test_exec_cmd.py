import sys, unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab

class ExecCmdTests(unittest.TestCase):
    @patch.object(lab, 'call')
    def test_single_kathara_command_and_remote_failure(self, mock):
        mock.return_value = subprocess.CompletedProcess([], 0, 'output\n__SOFT3888_RC__=1\n', '')
        result = lab.exec_cmd('e1', "false | grep -q example")
        args = mock.call_args.args[0]
        self.assertEqual(args[4], 'e1')
        self.assertEqual(len(args), 6)
        self.assertTrue(args[5].startswith('bash -lc '))
        self.assertEqual(result.returncode, 1)
    @patch.object(lab, 'call')
    def test_remote_success(self, mock):
        mock.return_value = subprocess.CompletedProcess([], 0, 'success\n__SOFT3888_RC__=0\n', '')
        self.assertEqual(lab.exec_cmd('e1', 'true').returncode, 0)
    @patch.object(lab, 'call')
    def test_missing_marker_never_passes(self, mock):
        mock.return_value = subprocess.CompletedProcess([], 0, 'unexpected', '')
        self.assertNotEqual(lab.exec_cmd('e1', 'true').returncode, 0)
