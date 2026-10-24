"""Asynchronous manual operations with durable intent and per-environment exclusion."""
from __future__ import annotations
import os
import re
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from fault_runtime import LAB_ROOTS, STATIC, selected, support, topologies, Lease, Conflict


def sanitized(text):
    # Do not expose inherited provider credentials if a subprocess/SDK includes them in errors.
    for key, value in os.environ.items():
        if value and len(value) >= 6 and any(word in key.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')):
            text = text.replace(value, '[REDACTED]')
    return re.sub(r'(?i)(bearer\s+|(?:api[_-]?key|token|password)\s*[:=]\s*)[^\s,;]+', r'\1[REDACTED]', text)


class Operations:
    def __init__(self, python):
        self.python = python

    def lease(self, topology):
        if topology not in topologies():
            raise ValueError('Unknown topology ID')
        if topology not in LAB_ROOTS:
            raise ValueError(support(topology)[1])
        return Lease(LAB_ROOTS[topology])

    def snapshot(self, topology):
        if topology not in topologies():
            raise ValueError('Unknown topology ID')
        if topology not in LAB_ROOTS:
            return {'pending': [], 'operation': None, 'busy': False, 'execution_enabled': False,
                    'support_reason': support(topology)[1]}
        lease = self.lease(topology)
        busy = False
        try:
            lease.acquire()
        except Conflict:
            busy = True
        finally:
            lease.release()
        state = lease.read()
        # A killed server releases flock, but durable pending intent remains recoverable.
        operation = state.get('operation')
        if not busy and operation and operation['status'] == 'running':
            operation = {**operation, 'status': 'interrupted',
                         'error': 'Previous operation stopped. Inspect and recover pending faults.'}
        enabled, reason = support(topology)
        return {**state, 'operation': operation, 'busy': busy, 'execution_enabled': enabled,
                'support_reason': reason, 'target': str(LAB_ROOTS[topology])}

    def reserve_auto(self, topology):
        if topology != 'enterprise-75':
            raise ValueError('Automatic SADE evaluation is only adapted for EnterpriseTopology')
        lease = self.lease(topology).acquire()
        try:
            if lease.read()['pending']:
                raise Conflict('Recover manual or unverified faults before starting automatic evaluation')
            return lease
        except Exception:
            lease.release()
            raise

    def start(self, topology, action, fault):
        row = selected(topology, fault)
        if action not in ('baseline', 'inject', 'verify', 'recover'):
            raise ValueError('Unknown manual action')
        if not row['execution_enabled']:
            raise ValueError(row['support_reason'])
        lease = self.lease(topology).acquire()
        try:
            state = lease.read()
            if action == 'inject' and (state['pending'] or row['kind'] == 'healthy'):
                raise Conflict('Injection requires a real fault and no pending recovery')
            if action in ('verify', 'recover') and not set(row['components']) & set(state['pending']):
                raise Conflict('No pending component of this scenario; select a pending fault')
            state['operation'] = {'action': action, 'fault_id': fault, 'topology_id': topology,
                'status': 'running', 'phase': 'Preparing', 'completed': 0, 'total': 1,
                'started_at': datetime.now(timezone.utc).isoformat(), 'lines': []}
            lease.write(state)
            threading.Thread(target=self._run, args=(lease, topology, action, row), daemon=True).start()
        except Exception:
            lease.release()
            raise

    def update(self, lease, **fields):
        state = lease.read()
        state['operation'].update(fields)
        lease.write(state)

    def log(self, lease, line):
        state = lease.read()
        state['operation']['lines'] = (state['operation']['lines'] + [sanitized(line)])[-240:]
        lease.write(state)

    def _step(self, lease, topology, action, fault=None):
        label = f'{action}: {fault or topology}'
        self.update(lease, phase=label)
        self.log(lease, label)
        command = [str(self.python), '-u', str(STATIC / 'fault_runtime.py'), topology, action]
        if fault:
            command.append(fault)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   pass_fds=(lease.file.fileno(),))
        # Bound even a hung baseline; each native per-device probe also has its own timeout.
        timer = threading.Timer(1200, process.kill)
        timer.start()
        try:
            for line in process.stdout:
                self.log(lease, line.rstrip())
            returncode = process.wait()
        finally:
            timer.cancel()
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()
        self.log(lease, f'{"PASS" if returncode == 0 else "FAIL"} {label}')
        state = lease.read()
        self.update(lease, completed=state['operation']['completed'] + 1)
        return returncode == 0

    def _run(self, lease, topology, action, row):
        try:
            components = row['components']
            if action == 'baseline':
                steps = [('baseline', None)]
            elif action == 'inject':
                steps = [('baseline', None)] + [('inject', f) for f in components] + [('verify', f) for f in components]
            elif action == 'verify':
                steps = [('verify', f) for f in components]
            else:
                components = [f for f in reversed(components) if f in lease.read()['pending']]
                steps = [('repair', f) for f in components] + [('repaired', f) for f in components] + [('restored-baseline', None)]
            self.update(lease, total=len(steps))
            errors = []
            for step, fault in steps:
                if step == 'inject':
                    lease.mark(fault)  # MUST precede the command, even if it raises or times out.
                try:
                    ok = self._step(lease, topology, step, fault)
                except Exception as exc:
                    ok = False
                    self.log(lease, f'{step} failed: {sanitized(str(exc))}')
                if not ok:
                    errors.append(f'{step}: {fault or topology}')
                    # Never continue an uncertain injection. Recovery, however, tries every target.
                    if action != 'recover':
                        break
            if errors:
                raise RuntimeError('Failed: ' + ', '.join(errors) + '. Pending faults remain available for recovery.')
            if action == 'recover':
                lease.clear(components)
            self.update(lease, status='succeeded', phase='Complete', finished_at=datetime.now(timezone.utc).isoformat())
        except Exception as exc:
            self.log(lease, sanitized(str(exc)))
            self.update(lease, status='failed', error=sanitized(str(exc)), finished_at=datetime.now(timezone.utc).isoformat())
        finally:
            lease.release()
