"""Offline structural and harness regression tests; not an OSPF simulation."""
import heapq
import ipaddress
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

import p20_enterprise_model as model
import validate_p20_enterprise as demo
from p20_docker_lab import select_containers


def shortest(source, target, removed=frozenset()):
    """Physical router graph, used only to test design redundancy and link costs."""
    graph = {node: [] for node, data in model.SPEC['nodes'].items() if 'ospf' in data}
    for link in model.SPEC['links']:
        if any(tuple(end) in removed for end in link['ends']):
            continue
        (a, _), (b, _) = link['ends']
        graph[a].append((b, link['cost']))
        graph[b].append((a, link['cost']))
    queue, visited = [(0, source, [source])], set()
    while queue:
        cost, node, path = heapq.heappop(queue)
        if node == target:
            return path
        if node in visited:
            continue
        visited.add(node)
        for peer, weight in graph[node]:
            if peer not in visited:
                heapq.heappush(queue, (cost + weight, peer, path + [peer]))
    return None


class TopologyTests(unittest.TestCase):
    def test_native_files_match_and_all_cases_resolve(self):
        spec, cases = demo.specs()
        self.assertEqual(spec['version'], 3)
        self.assertEqual(len(cases), 6)
        self.assertEqual(len(spec['nodes']), 75)
        self.assertEqual(sum('ospf' in d for d in spec['nodes'].values()), 25)

    def test_unique_addresses_and_47_nonoverlapping_networks(self):
        segments, addresses = {}, []
        for data in model.SPEC['nodes'].values():
            for segment, addr in data['interfaces'].values():
                iface = ipaddress.ip_interface(addr)
                segments.setdefault(segment, set()).add(iface.network)
                addresses.append(iface.ip)
        self.assertEqual(len(segments), 47)
        self.assertTrue(all(len(nets) == 1 for nets in segments.values()))
        self.assertEqual(len(addresses), len(set(addresses)))
        networks = [next(iter(nets)) for nets in segments.values()]
        self.assertTrue(all(not a.overlaps(b) for i, a in enumerate(networks) for b in networks[i+1:]))
        self.assertNotIn(ipaddress.ip_address('10.10.1.254'), addresses)

    def test_extension_preserves_original_addresses_and_covers_seven_sites(self):
        self.assertEqual(len(model.SPEC['sites']), 7)
        self.assertEqual(sum(d['role'] == 'pc' for d in model.SPEC['nodes'].values()), 35)
        self.assertEqual(sum(d['role'] == 'server' for d in model.SPEC['nodes'].values()), 15)
        self.assertEqual(model.address('pc1'), '10.10.1.11')
        self.assertEqual(model.address('pc16'), '10.10.4.14')
        self.assertEqual(model.address('server8'), '10.40.4.12')
        self.assertEqual(model.uplink_gateway('eth0'), '10.255.8.1')
        for site in model.SPEC['sites'].values():
            self.assertTrue(all(model.SPEC['nodes'][n]['site'] == model.SPEC['nodes'][site['endpoints'][0]]['site'] for n in site['endpoints']))

    def test_transit_peers_share_area_and_cost(self):
        for link in model.SPEC['links']:
            configs = [model.SPEC['nodes'][node]['ospf'][iface] for node, iface in link['ends']]
            self.assertEqual(configs[0], configs[1])
            self.assertFalse(configs[0]['passive'])

    def test_seven_areas_have_two_abrs_and_passive_endpoint_lans(self):
        for site in model.SPEC['sites'].values():
            edge = model.SPEC['nodes'][site['router']]
            for name in ('primary_abr', 'backup_abr'):
                areas = {d['area'] for d in model.SPEC['nodes'][site[name]]['ospf'].values()}
                self.assertIn(0, areas)
                self.assertEqual(len(areas), 2)
            self.assertEqual([i for i, d in edge['ospf'].items() if d['passive']], ['eth2', 'eth3'])
        self.assertTrue(all(not data['routes'] for data in model.SPEC['nodes'].values() if 'ospf' in data))

    def test_every_single_transit_link_has_an_alternate_path(self):
        routers = [n for n, d in model.SPEC['nodes'].items() if 'ospf' in d]
        for link in model.SPEC['links']:
            removed = {tuple(link['ends'][0])}
            for node in routers:
                self.assertIsNotNone(shortest('r1', node, removed), (link['segment'], node))

    def test_hq_primary_backup_and_isolation_are_distinct(self):
        self.assertEqual(shortest('r13', 'r14')[1], 'r5')
        self.assertEqual(shortest('r13', 'r14', {('r13', 'eth0')})[1], 'r6')
        self.assertIsNone(shortest('r13', 'r14', {('r13', 'eth0'), ('r13', 'eth1')}))
        self.assertIsNotNone(shortest('r14', 'r16', {('r13', 'eth0'), ('r13', 'eth1')}))

    def test_probes_cover_every_endpoint_and_each_lan(self):
        covered = {node for pair in model.PROBES for node in pair}
        endpoints = {n for n, d in model.SPEC['nodes'].items() if 'ospf' not in d}
        self.assertEqual(covered, endpoints)

    def test_faults_distinguish_service_loss_from_degraded_redundancy(self):
        self.assertTrue(all(model.expected_ping('failover', *pair) for pair in model.PROBES))
        self.assertFalse(model.expected_ping('isolation', 'pc1', 'pc5'))
        self.assertTrue(model.expected_ping('isolation', 'pc1', 'server1'))
        self.assertFalse(model.expected_ping('advertisement', 'pc5', 'server1'))
        self.assertTrue(model.expected_ping('advertisement', 'pc1', 'server1'))
        self.assertFalse(model.expected_ping('server-link', 'pc1', 'server1'))
        self.assertTrue(model.expected_ping('server-link', 'server1', 'server2'))
        self.assertTrue(model.expected_ping('gateway', 'pc1', 'pc2'))
        self.assertFalse(model.expected_ping('gateway', 'pc1', 'server1'))
        self.assertTrue(model.expected_ping('gateway', 'pc2', 'server1'))

    def test_failover_requires_backup_route_not_only_pings(self):
        rows = model.checks('failover')
        self.assertIn(('r13', model.route_count('10.10.2.0/24', model.uplink_gateway('eth1'), 'ospf'), '1'), rows)
        self.assertNotEqual(model.checks('healthy'), rows)


class HarnessTests(unittest.TestCase):
    def test_advertisement_injection_handles_absence_but_not_tool_errors(self):
        injection = model.CASES['advertisement']['inject']
        for fake, expected in [
            ("vtysh() { return 0; }; ", 0),
            ("vtysh() { return 127; }; ", 127),
            ("vtysh() { if test \"$2\" = 'show running-config'; then echo ' network 10.40.1.0/24 area 0.0.0.1'; else return 2; fi; }; ", 2),
        ]:
            result = subprocess.run(['sh', '-c', fake + injection], capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)

    def test_container_mapping_rejects_other_labs_duplicates_and_missing_nodes(self):
        def record(name='r13', lab='this-lab', running=True):
            return {'Id': 'container-id', 'State': {'Running': running},
                    'Config': {'Labels': {'name': name, 'app': 'kathara', 'user': 'owner', 'lab_hash': lab}}}
        self.assertEqual(select_containers([record()], 'this-lab', 'owner', {'r13'}), {'r13': 'container-id'})
        for records in [[], [record(lab='other-lab')], [record(), record()], [record(name='r14')], [record(running=False)]]:
            with self.assertRaises(RuntimeError):
                select_containers(records, 'this-lab', 'owner', {'r13'})

    def test_route_assertion_handles_nhid_and_rejects_wrong_gateway(self):
        cmd = model.route_count('10.10.2.0/24', '10.255.8.1', 'ospf')
        for row, expected in [
            ('10.10.2.0/24 nhid 14 via 10.255.8.1 dev eth0 proto ospf metric 20', '1'),
            ('10.10.2.0/24 via 10.255.8.1 dev eth0 proto ospf', '1'),
            ('10.10.2.0/24 via 10.255.9.1 dev eth1 proto ospf', '0'),
            ('10.10.2.0/24 via 10.255.8.1 dev eth0 proto static', '0'),
        ]:
            script = "ip() { printf '%s\\n' \"$ROW\"; }; " + cmd
            result = subprocess.run(['sh', '-c', script], env={'ROW': row, 'PATH': '/usr/bin:/bin'}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), expected)

    def test_baseline_failure_prevents_injection(self):
        with patch.object(demo, 'converge', side_effect=RuntimeError('bad baseline')), patch.object(demo, 'mutate') as mutate:
            with self.assertRaises(RuntimeError):
                demo.cycle(Mock(), {}, 'failover', Mock(), 1)
            mutate.assert_not_called()

    def test_failure_after_injection_attempts_repair(self):
        scenario = Mock(injection=Mock(device='r13', command='ip link set eth0 down'))
        with patch.object(demo, 'converge', side_effect=[None, RuntimeError('fault checks')]), patch.object(demo, 'mutate') as mutate:
            with self.assertRaises(RuntimeError):
                demo.cycle(Mock(), {}, 'failover', scenario, 1)
            self.assertEqual(mutate.call_args.args[1:], ('r13', 'ip link set eth0 up'))

    def test_missing_batch_markers_are_errors(self):
        lab = Mock(); lab.exec.return_value = (0, 'tool error')
        with self.assertRaises(RuntimeError):
            demo.execute_batch(lab, 'pc1', ['ping -c1 10.10.1.1'])

    def test_batch_keeps_each_exit_code(self):
        lab = Mock()
        lab.exec.return_value = (0, '__P20_test_0_BEGIN\n0% packet loss\n__P20_test_0_END:0\n__P20_test_1_BEGIN\n100% packet loss\n__P20_test_1_END:1')
        with patch.object(demo.uuid, 'uuid4', return_value=Mock(hex='test')):
            self.assertEqual(demo.execute_batch(lab, 'pc1', ['one', 'two']), [(0, '0% packet loss'), (1, '100% packet loss')])

    def test_tool_error_does_not_count_as_expected_packet_loss(self):
        self.assertFalse(demo.evaluate('loss>0', 127, 'ping not found'))
        self.assertFalse(demo.evaluate('loss>0', 2, '100% packet loss'))
        self.assertFalse(demo.evaluate('loss>0', 0, '0% packet loss'))

    def test_convergence_requires_two_consecutive_rounds(self):
        with patch.object(demo, 'run_stage', side_effect=[True, False, True, True]) as stage, patch.object(demo.time, 'sleep'):
            demo.converge(Mock(), {}, 'example', [], 120)
            self.assertEqual(stage.call_count, 4)


if __name__ == '__main__':
    unittest.main()
