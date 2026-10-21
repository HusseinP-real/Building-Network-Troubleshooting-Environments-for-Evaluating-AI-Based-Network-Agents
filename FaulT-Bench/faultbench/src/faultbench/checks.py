"""Strict checks: command errors and unsupported expectations fail closed.

Exit 1 with an exact zero/empty result is accepted for grep/pgrep's documented
no-match outcome. No other nonzero status can satisfy a non-ping assertion.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .lab import kathara_exec
from .scenario import CheckLine


@dataclass
class CheckResult:
    line: CheckLine
    passed: bool
    actual: str
    rationale: str
    rc: int = 0


def run_check(topology: str, line: CheckLine, timeout: int = 30) -> CheckResult:
    rc, out = kathara_exec(topology, line.device, line.command, timeout=timeout)
    passed, why = _evaluate_expectation(line.expect, rc, out, command=line.command)
    return CheckResult(line, passed, out.strip(), why, rc)


def run_checks(topology: str, lines: list[CheckLine]) -> list[CheckResult]:
    return [run_check(topology, line) for line in lines]


def all_passed(results: list[CheckResult]) -> bool:
    return bool(results) and all(r.passed for r in results)


_PERCENT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%\s*(?:packet\s*)?loss', re.I)


def _evaluate_expectation(expect: str, rc: int, out: str, *, command: str | None = None) -> tuple[bool, str]:
    e = expect.strip().lower()
    value = out.strip()
    # Existing datasets append parenthetical explanations to ping checks.
    if re.match(r'^0\s*%\s+loss(?:\s|$)', e) or re.match(r'^loss\s*>\s*0(?:\s|$)', e):
        match = _PERCENT_RE.search(out)
        if match is None:
            return False, 'no packet-loss result; timeout/errors are not evidence of loss'
        loss = float(match.group(1))
        if not 0 <= loss <= 100:
            return False, 'invalid packet-loss percentage'
        healthy = e.startswith('0')
        return (rc == 0 and loss == 0 if healthy else rc in (0, 1) and loss > 0), f'rc={rc}, loss={loss}%'
    no_match = rc == 1 and ((e.isdecimal() and int(e) == 0 and value == '0') or (e == 'empty' and not value))
    if no_match and command is not None and not re.search(r'\b(?:grep|pgrep)\b', command):
        return False, 'nonzero exit outside a grep/pgrep no-match check'
    if rc != 0 and not no_match:
        return False, f'command failed: rc={rc}'
    if e in ('nonempty', 'non-empty', 'empty'):
        return (bool(value) if e != 'empty' else not value), f'output {"present" if value else "empty"}'
    if e in ('up', 'down'):
        found = re.search(r'\bstate\s+' + e + r'\b', value, re.I)
        return bool(found), f'link state {e}: {bool(found)}'
    if e in ('full', 'init'):
        return bool(re.search(r'\b' + e + r'\b', value, re.I)), f'neighbor state {e}'
    number = re.fullmatch(r'\d+', value)
    if e.isdecimal():
        return bool(number) and int(value) == int(e), f'got {value!r}, expected {e}'
    comparison = re.fullmatch(r'(>=|<)\s*(\d+)', e)
    if comparison:
        passed = bool(number) and (int(value) >= int(comparison[2]) if comparison[1] == '>=' else int(value) < int(comparison[2]))
        return passed, f'got {value!r}, expected {e}'
    if e in ('nonzero', 'non-zero'):
        return bool(number) and int(value) > 0, f'got {value!r}, expected positive integer'
    if e.startswith('equals:'):
        expected = expect.strip().split(':', 1)[1].strip()
        return value == expected, f'got {value!r}, expected {expected!r}'
    return False, f'unsupported expectation: {expect!r}'
