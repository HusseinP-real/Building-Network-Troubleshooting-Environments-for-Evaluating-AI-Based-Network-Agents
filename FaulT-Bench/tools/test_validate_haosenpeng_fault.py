"""Regression checks for failures that must never count as successful injection."""
import unittest

from validate_haosenpeng_fault import evaluate, validate_spec


class ValidationTests(unittest.TestCase):
    def test_scenario_is_resolvable_and_shell_valid(self):
        validate_spec()

    def test_missing_output_is_not_packet_loss(self):
        self.assertFalse(evaluate("loss>0", 1, ""))
        self.assertFalse(evaluate("loss>0", 124, "[TIMEOUT]"))
        self.assertFalse(evaluate("loss>0", 127, "ping: command not found"))

    def test_ping_failure_requires_loss_and_expected_status(self):
        self.assertTrue(evaluate("loss>0", 1, "2 transmitted, 0 received, 100% packet loss"))
        self.assertFalse(evaluate("loss>0", 2, "100% packet loss"))
        self.assertFalse(evaluate("loss>0", 1, "0% packet loss"))

    def test_healthy_ping_cannot_match_inside_100_percent(self):
        self.assertTrue(evaluate("0% loss", 0, "2 transmitted, 2 received, 0% packet loss"))
        self.assertFalse(evaluate("0% loss", 0, "100% packet loss"))
        self.assertFalse(evaluate("0% loss", 124, "0% packet loss"))

    def test_numeric_check_rejects_errors_and_mixed_output(self):
        self.assertTrue(evaluate("1", 0, "1\n"))
        self.assertFalse(evaluate("1", 1, "1"))
        self.assertFalse(evaluate("1", 0, "error on device 1"))

    def test_unknown_expectation_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate("looks broken", 0, "")


if __name__ == "__main__":
    unittest.main()
