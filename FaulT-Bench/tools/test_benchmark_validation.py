"""Regression tests for false positives and device-command exit status."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'faultbench/src'))
from faultbench.checks import _evaluate_expectation as evaluate, all_passed, run_check
from faultbench.lab import kathara_exec, _lab_filters
from faultbench.scenario import CheckLine


class StrictChecks(unittest.TestCase):
    def test_timeout_and_missing_output_are_not_fault_evidence(self):
        for rc in (0, 1, 124, 127):
            self.assertFalse(evaluate('loss>0', rc, '')[0])
        self.assertFalse(evaluate('loss>0', 124, '100% packet loss')[0])

    def test_ping_exit_status_and_percentage(self):
        self.assertTrue(evaluate('loss>0', 1, '100% packet loss')[0])
        self.assertTrue(evaluate('0% loss (gateway)', 0, '0% packet loss')[0])
        self.assertFalse(evaluate('0% loss', 0, '100% packet loss')[0])
        self.assertFalse(evaluate('loss>0', 2, '100% packet loss')[0])

    def test_failed_ping_is_valid_evidence_through_the_full_check_runner(self):
        with patch('faultbench.checks.kathara_exec', return_value=(1, '100% packet loss')):
            result = run_check('test', CheckLine('r1', 'ping -c1 -W1 target', 'loss>0'))
        self.assertTrue(result.passed)
        self.assertEqual(result.rc, 1)

    def test_unknown_assertions_and_empty_suites_fail(self):
        self.assertFalse(evaluate('HTTP 200', 0, '200')[0])
        self.assertFalse(all_passed([]))

    def test_command_errors_cannot_pass_as_numbers_or_nonempty(self):
        self.assertFalse(evaluate('1', 1, 'error on device 1')[0])
        self.assertFalse(evaluate('1', 0, 'error on device 1')[0])
        self.assertFalse(evaluate('nonempty', 127, 'command not found')[0])
        self.assertTrue(evaluate('000', 0, '000')[0])
        self.assertTrue(evaluate('equals: 192.168.251.12', 0, '192.168.251.12\n')[0])

    def test_grep_no_match_is_distinct_from_execution_error(self):
        with patch('faultbench.checks.kathara_exec', return_value=(1, '0')):
            self.assertTrue(run_check('test', CheckLine('r1', 'grep -c prefix /etc/frr/frr.conf', '0')).passed)
            self.assertFalse(run_check('test', CheckLine('r1', 'false; echo 0', '0')).passed)
        self.assertFalse(evaluate('empty', 124, '')[0])

    def test_real_api_exit_code_and_stderr_are_preserved(self):
        api = SimpleNamespace(exec=lambda **kwargs: (b'output', b'error', 17))
        with patch('faultbench.lab._kathara', return_value=api):
            self.assertEqual(kathara_exec('test', 'r1', 'false'), (17, 'outputerror'))

    def test_ambiguous_failure_never_reexecutes_mutation(self):
        with patch('faultbench.lab._kathara', side_effect=RuntimeError('connection lost')) as api:
            rc, output = kathara_exec('test', 'r1', 'mutation')
        self.assertEqual(rc, 125)
        self.assertEqual(api.call_count, 1)

    def test_resource_filters_always_include_exact_lab_and_user(self):
        first, second = _lab_filters('first'), _lab_filters('second')
        self.assertNotEqual(first, second)
        self.assertIn('app=kathara', first['label'])
        self.assertTrue(any(v.startswith('lab_hash=') for v in first['label']))
        self.assertTrue(any(v.startswith('user=') for v in first['label']))



class CustomScenarioContracts(unittest.TestCase):
    def test_roles_cover_all_75_devices_without_guessing_names(self):
        from Kathara.parser.netkit.LabParser import LabParser
        from faultbench.inventory import apply_roles
        root = Path(__file__).resolve().parents[1] / 'topology_kathara/Kath5_Jiayuan_75Devices'
        lab = LabParser().parse(str(root)); lab.name = root.name
        api = SimpleNamespace(lab=lab)
        apply_roles(api)
        self.assertIn('a1', api.hosts)
        self.assertIn('g1', api.hosts)
        self.assertIn('mgmt3', api.hosts)
        self.assertIn('intapp1', api.servers['web'])
        self.assertEqual(len(api.routers) + len(api.hosts) + sum(map(len, api.servers.values())), 75)

    def test_four_scenarios_have_baseline_fault_and_machine_readable_recovery(self):
        import json, subprocess
        from faultbench.scenario import parse_scenario, resolve_scenario
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / 'topology_kathara/Kath5_Jiayuan_75Devices/benchmark.json').read_text())
        self.assertEqual(len(config['scenarios']), 4)
        for ref in config['scenarios']:
            sc = parse_scenario(resolve_scenario(ref))
            self.assertEqual(sc.topology, 'Kath5_Jiayuan_75Devices')
            self.assertTrue(sc.pre_check and sc.post_inject_check and sc.recovery_check)
            for inj in [sc.injection, sc.recovery]:
                self.assertTrue(inj.device and inj.command)
                subprocess.run(['sh', '-n'], input=inj.command, text=True, check=True)
            import shlex
            for check in sc.pre_check + sc.post_inject_check + sc.recovery_check:
                words = shlex.split(check.command)
                for i, word in enumerate(words[:-1]):
                    if word == 'awk':
                        subprocess.run(['awk', words[i+1]], input='', text=True, capture_output=True, check=True)

    def test_failed_baseline_prevents_mutation_and_agent_call(self):
        import tempfile
        from contextlib import ExitStack
        from faultbench.orchestrator import run_one
        from faultbench.scenario import resolve_scenario
        with ExitStack() as stack:
            stack.enter_context(patch("faultbench.orchestrator.require_credentials"))
            stack.enter_context(patch("faultbench.orchestrator.snapshot_runtime",return_value={"unit_fixture":True}))
            stack.enter_context(patch('faultbench.orchestrator.lstart', return_value=75))
            stack.enter_context(patch('faultbench.orchestrator.kathara_container_count', return_value=75))
            stack.enter_context(patch('faultbench.orchestrator.time.sleep'))
            stack.enter_context(patch('faultbench.orchestrator.time.monotonic', side_effect=[0, 999]))
            stack.enter_context(patch('faultbench.orchestrator.run_checks', return_value=[]))
            stack.enter_context(patch('faultbench.orchestrator._finalize', side_effect=lambda row,*a:row))
            mutate = stack.enter_context(patch('faultbench.orchestrator.apply_injection'))
            with tempfile.TemporaryDirectory() as out:
                row = run_one(resolve_scenario('jiayuan75-intapp1-http-stopped'), 'sade', Path(out), stream=False)
        self.assertEqual(row['status'], 'baseline_failed')
        mutate.assert_not_called()

class RuntimeAndSchemaGuards(unittest.TestCase):
    def test_cloud_key_alias_works_without_env_file(self):
        import os
        from faultbench.envfile import load_env
        with patch.dict(os.environ, {'FAULTBENCH_OPENAI_API_KEY': 'unit-test-placeholder'}, clear=True):
            self.assertFalse(load_env(Path('/nonexistent-soft3888.env')))
            self.assertEqual(os.environ['OPENAI_API_KEY'], 'unit-test-placeholder')

    def test_cloud_key_alias_never_overrides_existing_binding(self):
        import os
        from faultbench.envfile import load_env
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'existing-test-placeholder', 'FAULTBENCH_OPENAI_API_KEY': 'alias-test-placeholder'}, clear=True):
            load_env(Path('/nonexistent-soft3888.env'))
            self.assertEqual(os.environ['OPENAI_API_KEY'], 'existing-test-placeholder')

    def test_usr_hash_changes_when_program_bytes_change(self):
        import tempfile
        from faultbench.runtime import tree_hash
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'program').write_text('original')
            before = tree_hash(root)
            (root / 'program').write_text('tampered')
            self.assertNotEqual(before, tree_hash(root))

    def test_malformed_strict_check_is_not_silently_dropped(self):
        from faultbench.scenario import _parse_checks
        with self.assertRaises(ValueError):
            _parse_checks('r1 ping target -> expect healthy', strict=True)

    def test_custom_reachability_is_deterministic_and_bounded(self):
        import asyncio, json
        from Kathara.parser.netkit.LabParser import LabParser
        from faultbench.inventory import apply_roles, sampled_reachability
        root = Path(__file__).resolve().parents[1] / 'topology_kathara/Kath5_Jiayuan_75Devices'
        lab = LabParser().parse(str(root)); lab.name = root.name
        api = SimpleNamespace(lab=lab)
        api.load_machines = lambda: apply_roles(api)
        api.get_host_ip = lambda name: '192.0.2.1'
        state = dict(active=0, peak=0)
        async def ping(src, ip):
            state['active'] += 1
            state['peak'] = max(state['peak'], state['active'])
            await asyncio.sleep(0.001)
            state['active'] -= 1
            return dict(status='ok', tx=2, rx=2, loss_percent=0)
        api._check_ping_success_async = ping
        first = json.loads(asyncio.run(sampled_reachability(api)))
        second = json.loads(asyncio.run(sampled_reachability(api)))
        self.assertEqual(first, second)
        self.assertEqual(first['sampling']['destinations'], ['b1', 'intapp1'])
        self.assertEqual(len(first['hosts']), 54)
        self.assertEqual(len(first['results']), 106)
        self.assertGreater(state['peak'], 1)
        self.assertLessEqual(state['peak'], 4)

    def test_empty_cloud_git_guard_is_not_a_repository(self):
        import tempfile
        from faultbench.runners.base import _git_root
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.git').mkdir()
            child = root / 'clean'; child.mkdir()
            self.assertIsNone(_git_root(child))
            (root / '.git/HEAD').write_text('ref: refs/heads/main')
            self.assertEqual(_git_root(child), root)

    def test_incomplete_inventory_cannot_hide_a_device(self):
        from faultbench.inventory import apply_roles
        api = SimpleNamespace(lab=SimpleNamespace(name='Kath5_Jiayuan_75Devices', machines={'a1': object()}))
        with self.assertRaises(ValueError):
            apply_roles(api)

class PublishedClosContracts(unittest.TestCase):
    def test_92_devices_and_all_collision_domain_subnets_agree(self):
        import json, ipaddress
        from collections import defaultdict
        from Kathara.parser.netkit.LabParser import LabParser
        root = Path(__file__).resolve().parents[1] / 'topology_kathara/NIKA_Clos_Jiayuan_92Devices'
        lab = LabParser().parse(str(root))
        self.assertEqual(len(lab.machines), 92)
        self.assertEqual(len(lab.links), 228)
        plan = json.loads((root / 'address-plan.json').read_text())
        domains = defaultdict(set); addresses = []
        for node in plan['routers'].values():
            for interface in node['interfaces']:
                address = ipaddress.ip_interface(interface['address'])
                domains[interface['domain']].add(address.network)
                addresses.append(address.ip)
        for node in plan['endpoints'].values():
            address = ipaddress.ip_interface(node['address'] + '/24')
            domains[node['domain']].add(address.network)
            addresses.append(address.ip)
        self.assertEqual(len(domains), 228)
        self.assertTrue(all(len(networks) == 1 for networks in domains.values()))
        self.assertEqual(len(addresses), len(set(addresses)))

    def test_core_clos_scenarios_and_dhcp_trigger_are_complete(self):
        import json, subprocess, shlex
        from faultbench.scenario import resolve_scenario, parse_scenario
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / 'topology_kathara/NIKA_Clos_Jiayuan_92Devices/benchmark.json').read_text())
        self.assertEqual(len(config['scenarios']), 4)
        for ref in config['scenarios']:
            sc = parse_scenario(resolve_scenario(ref))
            self.assertTrue(sc.pre_check and sc.post_inject_check and sc.recovery_check)
            for inj in (sc.injection, sc.recovery, sc.trigger):
                if inj: subprocess.run(['sh','-n'],input=inj.command,text=True,check=True)
            for check in sc.pre_check + sc.post_inject_check + sc.recovery_check:
                words = shlex.split(check.command)
                for i,word in enumerate(words[:-1]):
                    if word == 'awk':subprocess.run(['awk',words[i+1]],input='',text=True,capture_output=True,check=True)
            if sc.injection.device == 'dhcp1':
                self.assertEqual(sc.trigger.device, 'client_0')
            else:self.assertIsNone(sc.trigger)

    def test_compound_rule_count_rejects_duplicates(self):
        import subprocess
        from faultbench.scenario import resolve_scenario, parse_scenario
        sc = parse_scenario(resolve_scenario('nika92-client1-compound-gateway-and-tcp-filter'))
        command = next(c.command for c in sc.post_inject_check if 'iptables-legacy -S' in c.command)
        fake = "fake_iptables() { printf '%s\\n' '-A OUTPUT soft3888-nika92-compound' '-A OUTPUT soft3888-nika92-compound'; }; "
        proc = subprocess.run(['sh','-c',fake+command.replace('iptables-legacy', 'fake_iptables')],capture_output=True,text=True,check=True)
        self.assertEqual(proc.stdout.strip(), '2')

    def test_failed_dhcp_refresh_prevents_agent_execution(self):
        import tempfile
        from contextlib import ExitStack
        from faultbench.orchestrator import run_one
        from faultbench.scenario import resolve_scenario, parse_scenario
        from faultbench.inject import InjectionResult
        from faultbench.checks import CheckResult
        sc = parse_scenario(resolve_scenario('nika92-dhcp1-wrong-router-option'))
        with ExitStack() as stack:
            stack.enter_context(patch("faultbench.orchestrator.require_credentials"))
            stack.enter_context(patch("faultbench.orchestrator.snapshot_runtime",return_value={"unit_fixture":True}))
            stack.enter_context(patch('faultbench.orchestrator.lstart', return_value=92))
            stack.enter_context(patch('faultbench.orchestrator.kathara_container_count', return_value=92))
            stack.enter_context(patch('faultbench.orchestrator.time.sleep'))
            stack.enter_context(patch('faultbench.orchestrator.run_checks', return_value=[CheckResult(sc.pre_check[0], True, 'ok', 'test fixture')]))
            stack.enter_context(patch('faultbench.orchestrator.apply_injection', side_effect=[InjectionResult(True,None,0,'server changed'),InjectionResult(True,None,1,'no DHCP lease')]))
            stack.enter_context(patch('faultbench.orchestrator._finalize', side_effect=lambda row,*a:row))
            agent = stack.enter_context(patch.dict('faultbench.orchestrator.AGENT_RUNNERS', {'sade': lambda **kw: self.fail('agent must not run')}))
            with tempfile.TemporaryDirectory() as out:
                result = run_one(sc.source_path, 'sade', Path(out), stream=False)
        self.assertEqual(result['status'], 'injection_failed')
        self.assertIn('no DHCP lease', result['error'])

if __name__ == "__main__":
    unittest.main()
