"""Offline topology and control-flow checks, not live packet-forwarding evidence."""
import copy
import ipaddress as ip
import json
import re
import unittest
from unittest.mock import Mock,patch
import validate_p20_enterprise as demo
from faultbench.scenario import discover_scenarios


def reaches(nodes,source,target,down=frozenset()):
    """Model longest-prefix static routes and on-link next hops, with loop detection."""
    target=ip.ip_address(target);current=source;visited=set()
    while current not in visited:
        visited.add(current);device=nodes[current]
        active={i:(segment,ip.ip_interface(addr)) for i,(segment,addr) in device['interfaces'].items() if (current,i) not in down}
        if any(a.ip==target for _,a in active.values()):return True
        if current!=source and not current.startswith('r'):return False
        candidates=[]
        for iface,(segment,address) in active.items():
            if target in address.network:candidates.append((address.network.prefixlen,target))
        for prefix,via in device['routes'].items():
            net=ip.ip_network('0.0.0.0/0' if prefix=='default' else prefix)
            if target in net:candidates.append((net.prefixlen,ip.ip_address(via)))
        if not candidates:return False
        next_hop=max(candidates,key=lambda c:c[0])[1]
        peers=[]
        for iface,(segment,addr) in active.items():
            if next_hop not in addr.network:continue
            for peer,pdata in nodes.items():
                if peer==current:continue
                for pi,(ps,pa) in pdata['interfaces'].items():
                    if (peer,pi) not in down and ps==segment and ip.ip_interface(pa).ip==next_hop:peers.append(peer)
        if len(peers)!=1:return False
        current=peers[0]
    return False

def ping(nodes,source,target,down=frozenset()):
    destination=next(n for n,d in nodes.items() if any(str(ip.ip_interface(a).ip)==target for _,a in d['interfaces'].values()))
    source_ip=str(ip.ip_interface(next(iter(nodes[source]['interfaces'].values()))[1]).ip)
    return reaches(nodes,source,target,down) and reaches(nodes,destination,source_ip,down)

class TopologyTests(unittest.TestCase):
    def setUp(self):self.nodes=json.loads(demo.SPEC_PATH.read_text())['nodes']
    def test_native_specs_and_location(self):
        spec,scenarios=demo.specs()
        self.assertEqual(len(spec['nodes']),9);self.assertEqual(len(scenarios),4)
        self.assertTrue((demo.TOPOLOGY/'lab.conf').is_file())
        self.assertFalse({s.source_path for s in scenarios.values()}.intersection(discover_scenarios('all')))
    def test_six_nonoverlapping_subnets_and_unique_addresses(self):
        segments={};addresses=[]
        for node in self.nodes.values():
            for segment,addr in node['interfaces'].values():
                interface=ip.ip_interface(addr);segments.setdefault(segment,set()).add(interface.network);addresses.append(interface.ip)
        self.assertEqual(len(segments),6);self.assertTrue(all(len(n)==1 for n in segments.values()))
        self.assertEqual(len(set(addresses)),len(addresses))
        nets=[next(iter(n)) for n in segments.values()]
        self.assertTrue(all(not a.overlaps(b) for i,a in enumerate(nets) for b in nets[i+1:]))
        self.assertNotIn(ip.ip_address('10.10.10.254'),addresses)
    def test_startup_configs_match_source_spec(self):
        conf=(demo.TOPOLOGY/'lab.conf').read_text()
        for node,data in self.nodes.items():
            startup=(demo.TOPOLOGY/(node+'.startup')).read_text()
            for interface,(domain,address) in data['interfaces'].items():
                self.assertIn(f'{node}[{interface[3:]}]="{domain}"',conf)
                self.assertIn(f'ip link set {interface} up',startup)
                self.assertIn(f'ip address replace {address} dev {interface}',startup)
            for net,via in data['routes'].items():self.assertIn(f'ip route replace {net} via {via}',startup)
            self.assertIn(f'{node}[sysctl]="net.ipv4.ip_forward='+('1' if node.startswith('r') else '0')+'"',conf)
            self.assertNotIn('sysctl -w',startup)
    def test_all_endpoint_pairs_have_forward_and_return_routes(self):
        endpoints=[n for n in self.nodes if not n.startswith('r')]
        for src in endpoints:
            for dst in endpoints:
                if src==dst:continue
                target=str(ip.ip_interface(self.nodes[dst]['interfaces']['eth0'][1]).ip)
                self.assertTrue(ping(self.nodes,src,target),(src,dst))
    def test_each_fault_has_predicted_scope(self):
        for case in demo.IDS:
            nodes=copy.deepcopy(self.nodes);down=set()
            if case=='server-link':down.add(('r2','eth2'))
            if case=='return-route':del nodes['r3']['routes']['10.10.10.0/24']
            if case=='gateway':nodes['pc1']['routes']['default']='10.10.10.254'
            for source,target in demo.PROBES:
                self.assertEqual(ping(nodes,source,target,down),(source,target) not in demo.FAILURES[case],(case,source,target))
    def test_return_route_fault_is_directional(self):
        del self.nodes['r3']['routes']['10.10.10.0/24']
        self.assertTrue(reaches(self.nodes,'pc1','10.40.40.10'))
        self.assertFalse(reaches(self.nodes,'server2','10.10.10.11'))
    def test_repair_model_recovers_connectivity(self):
        self.nodes['r3']['routes'].pop('10.10.10.0/24')
        self.assertFalse(ping(self.nodes,'pc1','10.40.40.10'))
        self.nodes['r3']['routes']['10.10.10.0/24']='10.255.23.1'
        self.assertTrue(ping(self.nodes,'pc1','10.40.40.10'))

class RunnerTests(unittest.TestCase):
    def test_bad_baseline_prevents_injection(self):
        with patch.object(demo,'converge',side_effect=RuntimeError('baseline')),patch.object(demo,'mutate') as mutate:
            with self.assertRaises(RuntimeError):demo.cycle(Mock(),{},'server-link',Mock(),1)
            mutate.assert_not_called()
    def test_injected_failure_attempts_exact_repair(self):
        sc=Mock(injection=Mock(device='r2',command='ip link set eth2 down'))
        with patch.object(demo,'converge',side_effect=[None,RuntimeError('failed')]),patch.object(demo,'mutate') as mutate:
            with self.assertRaises(RuntimeError):demo.cycle(Mock(),{},'server-link',sc,1)
            self.assertEqual(mutate.call_args.args[1:],('r2','ip link set eth2 up'))
    def test_mutation_error_is_not_ignored(self):
        lab=Mock();lab.exec.return_value=(1,'permission denied')
        with self.assertRaises(RuntimeError):demo.mutate(lab,'r2','ip link set eth2 down')
    def test_missing_startup_marker_fails(self):
        lab=Mock();lab.exec.return_value=(1,'')
        with self.assertRaises(RuntimeError):demo.verify_config(lab,json.loads(demo.SPEC_PATH.read_text()),{})
    def test_no_advisory_success_failure_expectations(self):
        for case in demo.IDS:
            for _,_,expect in demo.checks(case):self.assertIn(expect,('0% loss','loss>0','0','1'))

if __name__=='__main__':unittest.main()
