"""Offline tests: no Docker/Kathara or model requests. Real HTTP and process leases."""
import concurrent.futures
import http.client
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

DASHBOARD = Path(__file__).resolve().parents[1] / 'dashboard'
sys.path.insert(0, str(DASHBOARD))
import server
import fault_runtime as runtime
import operation_control as control
from environment_guard import Lease, Conflict


class ManualHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.patcher = patch.object(control, 'Lease', lambda root: Lease(self.directory / Path(root).name))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.operations = control.Operations(Path(sys.executable))
        validation = patch.object(runtime.generic_faults, 'validated', return_value=True)
        validation.start()
        self.addCleanup(validation.stop)

    def wait(self, topology='enterprise-75'):
        for _ in range(200):
            snapshot = self.operations.snapshot(topology)
            if not snapshot['busy']:
                return snapshot
            time.sleep(.01)
        self.fail('Worker did not finish')

    def fake_step(self, lease, topology, action, fault=None):
        self.operations.log(lease, f'MOCK {topology} {action} {fault}')
        state = lease.read()
        self.operations.update(lease, completed=state['operation']['completed'] + 1)
        return True


class ManualTests(ManualHarness):
    def test_catalog_deduplicates_tickets_and_filters_real_devices(self):
        rows = runtime.native_catalog('enterprise-75')
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(r['kind'] == 'fault' for r in rows), 7)
        self.assertEqual(sum(r['kind'] == 'healthy' for r in rows), 1)
        self.assertEqual(sum(r['kind'] == 'compound' for r in rows), 2)
        self.assertEqual(runtime.selected('enterprise-75', 'core-uplink')['case_ids'],
            ['core-uplink', 'core-uplink-vague', 'core-uplink-misleading'])
        for key, topology in runtime.topologies().items():
            inventory = json.loads(topology['inventory'].read_text())
            self.assertGreaterEqual(sum(not n.get('virtual') for n in inventory['nodes'].values()), 75)
        self.assertEqual(len(runtime.native_catalog('enterprise-75-standalone')), 4)
        self.assertEqual([r['id'] for r in runtime.native_catalog('multisite')], ['F01', 'F02', 'F03'])
        for key, count in [('multi-as-isp', 8), ('jiayuan-75', 5), ('nika-92', 6)]:
            rows = runtime.native_catalog(key)
            self.assertEqual(len(rows), count)
            self.assertFalse(any(r['execution_enabled'] for r in rows))
        nika = runtime.native_catalog('nika-92')
        self.assertEqual(sum(r['kind'] == 'compound' for r in nika), 1)

    def test_no_device_renaming_compatibility_and_bad_ids(self):
        for topology, fault in [('enterprise-75', 'F01'), ('multisite', 'core-uplink'),
                                ('../../etc', 'core-uplink'), ('nika-92', '$(touch /tmp/bad)')]:
            with self.assertRaises(ValueError):
                self.operations.start(topology, 'inject', fault)
        with self.assertRaises(ValueError):
            self.operations.start('jiayuan-75', 'inject', runtime.native_catalog('jiayuan-75')[0]['id'])
        inventory = json.loads(runtime.topologies()['multisite']['inventory'].read_text())
        inventory['nodes']['a1']['ports'][0]['link'] = 'wrong-domain'
        original = runtime.topologies
        with patch.object(runtime, 'topologies', return_value={**original(), 'multisite': {
                **original()['multisite'], 'inventory': self.directory / 'view.json'}}):
            (self.directory / 'view.json').write_text(json.dumps(inventory))
            self.assertFalse(runtime.native_support('multisite')[0])

    def test_full_cycle_and_no_model_import(self):
        with patch.object(self.operations, '_step', side_effect=self.fake_step) as steps:
            self.operations.start('enterprise-75', 'baseline', 'core-uplink')
            self.assertEqual(self.wait()['operation']['status'], 'succeeded')
            self.operations.start('enterprise-75', 'inject', 'core-uplink')
            state = self.wait()
            self.assertEqual(state['pending'], ['core-uplink'])
            self.assertEqual(state['operation']['completed'], 3)
            with self.assertRaises(Conflict):
                self.operations.reserve_auto('enterprise-75')
            self.operations.start('enterprise-75', 'verify', 'core-uplink')
            self.assertEqual(self.wait()['operation']['status'], 'succeeded')
            self.operations.start('enterprise-75', 'recover', 'core-uplink')
            self.assertEqual(self.wait()['pending'], [])
            lease = self.operations.reserve_auto('enterprise-75')
            lease.release()
            self.assertIn('baseline', [c.args[2] for c in steps.call_args_list])
        self.assertNotIn('sade_eval', runtime.__dict__)

    def test_partial_failure_durable_intent_and_targeted_recovery(self):
        calls = []
        def partial(lease, topology, action, fault=None):
            calls.append((action, fault))
            if action == 'inject':
                self.assertIn(fault, lease.read()['pending'])
            return not (action == 'inject' and fault == 'database-ingress-acl')
        with patch.object(self.operations, '_step', side_effect=partial):
            self.operations.start('enterprise-75', 'inject', 'compound-uplink-acl')
            state = self.wait()
            self.assertEqual(state['operation']['status'], 'failed')
            self.assertEqual(set(state['pending']), {'core-uplink-r6', 'database-ingress-acl'})
            # A new server instance still sees both attempted mutations.
            self.assertEqual(control.Operations(sys.executable).snapshot('enterprise-75')['pending'], state['pending'])
        with patch.object(self.operations, '_step', side_effect=self.fake_step) as steps:
            self.operations.start('enterprise-75', 'recover', 'compound-uplink-acl')
            self.assertEqual(self.wait()['pending'], [])
            self.assertEqual([(c.args[2], c.args[3]) for c in steps.call_args_list[:2]],
                [('repair', 'database-ingress-acl'), ('repair', 'core-uplink-r6')])

    def test_exception_injection_and_repair_failure_keep_intent(self):
        def fail(lease, topology, action, fault=None):
            if action in ('inject', 'repair'):
                raise OSError('uncertain transport result')
            return True
        with patch.object(self.operations, '_step', side_effect=fail):
            self.operations.start('enterprise-75', 'inject', 'core-uplink')
            self.assertEqual(self.wait()['pending'], ['core-uplink'])
            self.operations.start('enterprise-75', 'recover', 'core-uplink')
            self.assertEqual(self.wait()['operation']['status'], 'failed')
            self.assertEqual(self.wait()['pending'], ['core-uplink'])

    def test_baseline_failure_never_mutates_and_healthy_never_injects(self):
        with patch.object(self.operations, '_step', return_value=False) as steps:
            self.operations.start('enterprise-75', 'inject', 'database-acl')
            self.assertEqual(self.wait()['pending'], [])
            self.assertEqual([c.args[2] for c in steps.call_args_list], ['baseline'])
        with self.assertRaises(Conflict):
            self.operations.start('enterprise-75', 'inject', 'healthy')

    def test_cross_process_lock_and_duplicate_clicks(self):
        block, entered = threading.Event(), threading.Event()
        def wait_step(*args):
            entered.set()
            block.wait(3)
            return True
        with patch.object(self.operations, '_step', side_effect=wait_step):
            self.operations.start('enterprise-75', 'baseline', 'core-uplink')
            self.assertTrue(entered.wait(1))
            try:
                other = control.Operations(sys.executable)
                with self.assertRaises(Conflict):
                    other.start('enterprise-75', 'inject', 'core-uplink')
                with self.assertRaises(Conflict):
                    other.reserve_auto('enterprise-75')
                root = self.directory / 'EnterpriseTopology'
                code = f"import sys;sys.path.insert(0,{str(runtime.ROOT / 'tools')!r});from environment_guard import Lease,Conflict\ntry: Lease({str(root)!r}).acquire()\nexcept Conflict: sys.exit(17)"
                self.assertEqual(subprocess.run([sys.executable, '-c', code]).returncode, 17)
                # A different environment has its own independent lease.
                separate = other.lease('enterprise-75-standalone').acquire()
                separate.release()
            finally:
                block.set()
                self.wait()

    def test_auto_excludes_manual_and_restart_retains_pending(self):
        lease = self.operations.reserve_auto('enterprise-75')
        try:
            with self.assertRaises(Conflict):
                self.operations.start('enterprise-75', 'baseline', 'core-uplink')
            lease.mark('core-uplink')
            lease.write({**lease.read(), 'operation': {'status': 'running', 'action': 'inject'}})
        finally:
            lease.release()
        state = self.operations.snapshot('enterprise-75')
        self.assertEqual(state['operation']['status'], 'interrupted')
        self.assertEqual(state['pending'], ['core-uplink'])

    def test_fixed_worker_path_scoped_to_selected_topology(self):
        lease = self.operations.lease('multisite').acquire()
        lease.write({'pending': [], 'operation': {'lines': [], 'completed': 0}})
        process = unittest.mock.Mock()
        process.stdout = io.StringIO('PASS safe log\n')
        process.wait.return_value = 0
        process.poll.return_value = 0
        with patch.object(control.subprocess, 'Popen', return_value=process) as launch:
            self.assertTrue(self.operations._step(lease, 'multisite', 'inject', 'F01'))
            command = launch.call_args.args[0]
            self.assertEqual(command[-3:], ['multisite', 'inject', 'F01'])
            self.assertNotIn('shell', launch.call_args.kwargs)
            self.assertEqual(launch.call_args.kwargs['pass_fds'], (lease.file.fileno(),))
        lease.release()

    def test_native_adapters_reuse_exact_injection_and_repair(self):
        for topology in ('enterprise-75', 'enterprise-75-standalone', 'multisite'):
            lab = runtime.load_lab(topology)
            with patch.object(runtime, 'load_lab', return_value=lab):
                if topology == 'multisite':
                    result = subprocess.CompletedProcess([], 0, '', '')
                    with patch.object(lab, 'exec_cmd', return_value=result) as execute:
                        for fault, item in lab.FAULTS.items():
                            self.assertTrue(runtime.step(topology, 'inject', fault))
                            self.assertTrue(runtime.step(topology, 'repair', fault))
                            expected = list(zip(item['nodes'], item['apply'])) + list(zip(item['nodes'], item['repair']))
                            self.assertEqual([c.args for c in execute.call_args_list], expected)
                            execute.reset_mock()
                        self.assertTrue(runtime.verify(lab, topology, 'F01'))
                        self.assertEqual(execute.call_args_list[0].args[1], '! ( ' + lab.FAULTS['F01']['fail'] + ' )')
                else:
                    with patch.object(lab, 'execute', return_value=(True, '')) as execute:
                        for fault, (node, inject, repair) in lab.FAULTS.items():
                            self.assertTrue(runtime.step(topology, 'inject', fault))
                            self.assertTrue(runtime.step(topology, 'repair', fault))
                            self.assertEqual([c.args for c in execute.call_args_list], [(node, inject), (node, repair)])
                            execute.reset_mock()

    def test_auto_command_uses_selected_ticket_cases_and_inherits_lease(self):
        state = server.RunState(Path(sys.executable), self.directory)
        state.operations = self.operations
        lease = self.operations.reserve_auto('enterprise-75')
        descriptor = lease.file.fileno()
        process = unittest.mock.Mock()
        process.stdout = io.StringIO('safe output\n')
        process.wait.return_value = 0
        with patch.object(server.subprocess, 'Popen', return_value=process) as launch:
            state._run('test-model', 1, fault_id='link_down', lease=lease)
            arguments = launch.call_args.args[0]
            self.assertEqual(arguments[arguments.index('--cases') + 1:],
                runtime.selected('enterprise-75', 'link_down')['case_ids'])
            self.assertEqual(launch.call_args.kwargs['pass_fds'], (descriptor,))
            self.assertEqual(launch.call_args.kwargs['env']['SADE_ENV_LOCK_FD'], str(descriptor))
        self.assertEqual(state.returncode, 0)
        self.assertFalse(self.operations.snapshot('enterprise-75')['busy'])

    def test_corrupt_journal_fails_closed(self):
        lease = self.operations.lease('enterprise-75')
        lease.journal.write_text('{"pending": "not-a-list"}')
        with self.assertRaises(ValueError):
            self.operations.reserve_auto('enterprise-75')
        with self.assertRaises(ValueError):
            self.operations.start('enterprise-75', 'inject', 'core-uplink')
        # Validation failures release the lease rather than deadlocking recovery.
        lease.acquire()
        lease.release()

    def test_evaluator_guard_is_exclusive_between_threads(self):
        import environment_guard as guard
        started, release = threading.Event(), threading.Event()
        @guard.evaluation_session
        def work():
            started.set()
            release.wait(3)
        with patch.object(guard, 'ROOT', self.directory):
            thread = threading.Thread(target=work)
            thread.start()
            self.assertTrue(started.wait(1))
            try:
                with self.assertRaises(Conflict):
                    work()
            finally:
                release.set()
                thread.join(3)

    def test_operator_journal_and_catalog_cannot_be_read_by_diagnostic_agent(self):
        try:
            import sade_lab_mcp as mcp
        except ImportError:
            self.skipTest('Requires MCP environment')
        for command in ('cat /shared/results/control/state.json',
                        'cat /shared/dashboard/fault_runtime.py',
                        'cat /shared/tools/sade_cases.json',
                        'curl http://127.0.0.1:8765/api/faults?topology_id=enterprise-75'):
            self.assertIsNone(mcp._safe_command(command))

    def test_credentials_are_redacted(self):
        with patch.dict(control.os.environ, {'DEEPSEEK_API_KEY': 'secret-value'}):
            self.assertNotIn('secret-value', control.sanitized('error secret-value'))
            self.assertNotIn('sk-abcd', control.sanitized('api_key=sk-abcd'))


class HTTPTests(ManualHarness):
    def setUp(self):
        super().setUp()
        self.state = server.RunState(Path(sys.executable), self.directory)
        self.state.operations = self.operations
        handler = type('TestHandler', (server.Handler,), {'state': self.state, 'log_message': lambda *a: None})
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)

    def post(self, payload, path='/api/manual', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.http.server_port)
        connection.request('POST', path, json.dumps(payload), headers=headers or {'Content-Type': 'application/json'})
        result = connection.getresponse()
        data = json.loads(result.read())
        status = result.status
        connection.close()
        return status, data

    def test_illegal_http_requests(self):
        valid = {'topology_id': 'enterprise-75', 'fault_id': 'core-uplink', 'action': 'inject'}
        for payload in [[], None, {**valid, 'command': 'touch /tmp/no'}, {**valid, 'path': '/etc/passwd'},
                        {**valid, 'topology_id': '../../'}, {**valid, 'fault_id': []},
                        {**valid, 'fault_id': 'core-uplink-vague'}, {**valid, 'action': 'wipe'}]:
            self.assertEqual(self.post(payload)[0], 400, payload)
        self.assertEqual(self.post(valid, headers={'Content-Type': 'application/json', 'Origin': 'https://other.site'})[0], 403)
        self.assertEqual(self.post(valid, headers={'Content-Type': 'text/plain'})[0], 415)
        self.assertEqual(self.post(valid, headers={'Content-Type': 'application/json', 'Host': 'attacker.test'})[0], 403)
        self.assertEqual(self.post(valid, headers={'Content-Type': 'application/json', 'Host': '['})[0], 403)
        self.assertEqual(self.post({'topology_id': 'multisite', 'fault_id': 'F01'}, '/api/run')[0], 400)
        self.assertEqual(self.post({'topology_id': 'enterprise-75'}, '/api/run')[0], 400)

    def test_http_duplicate_clicks_get_conflict(self):
        block, entered = threading.Event(), threading.Event()
        def step(*args):
            entered.set()
            block.wait(3)
            return True
        with patch.object(self.operations, '_step', side_effect=step):
            payload = {'topology_id': 'enterprise-75', 'fault_id': 'core-uplink', 'action': 'baseline'}
            self.assertEqual(self.post(payload)[0], 202)
            self.assertTrue(entered.wait(1))
            try:
                self.assertEqual(self.post(payload)[0], 409)
                self.assertEqual(self.post({'topology_id': 'enterprise-75', 'fault_id': 'link_down'}, '/api/run')[0], 409)
            finally:
                block.set()
                self.wait()

    def test_selected_scope_and_all_scope_use_existing_runner(self):
        calls = []
        def finish(model, repeats, mode, style, profile, judge, fault, lease, topology):
            calls.append(fault)
            lease.release()
            self.state.running = False
        with patch.object(self.state, '_run', side_effect=finish):
            payload = {'topology_id': 'enterprise-75', 'fault_id': 'link_down', 'scope': 'selected'}
            self.assertEqual(self.post(payload, '/api/run')[0], 202)
            self.assertEqual(self.state.case_count, 1)
            for _ in range(100):
                if not self.state.running: break
                time.sleep(.01)
            self.assertEqual(self.post({**payload, 'scope': 'all'}, '/api/run')[0], 202)
            self.assertEqual(self.state.case_count, 5)
            for _ in range(100):
                if not self.state.running: break
                time.sleep(.01)
        self.assertEqual(calls, ['link_down', None])

    def test_pending_manual_fault_blocks_auto_over_http(self):
        with patch.object(self.operations, '_step', side_effect=self.fake_step):
            payload = {'topology_id': 'enterprise-75', 'fault_id': 'core-uplink', 'action': 'inject'}
            self.assertEqual(self.post(payload)[0], 202)
            self.wait()
            self.assertEqual(self.post({'topology_id': 'enterprise-75', 'fault_id': 'link_down'}, '/api/run')[0], 409)
            self.assertEqual(self.post({**payload, 'action': 'recover'})[0], 202)
            self.assertEqual(self.wait()['pending'], [])


if __name__ == '__main__':
    unittest.main()
