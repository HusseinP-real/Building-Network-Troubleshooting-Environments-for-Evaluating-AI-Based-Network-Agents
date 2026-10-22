"""Reject device-padding or silently divergent NIKA reference exports."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'faultbench/src'))
LAB=ROOT/'topology_kathara/NIKA_Clos_Jiayuan_92Devices'

class NikaReferenceContract(unittest.TestCase):
    def test_reference_graph_and_original_addresses_are_preserved(self):
        from Kathara.parser.netkit.LabParser import LabParser
        from tools.extend_nika_clos import render
        # Actually construct the pinned NIKA lab; compare its graph to the exported parser.
        rendered=render()
        self.assertEqual(rendered['reference-provenance.json'],(LAB/'reference-provenance.json').read_text())
        provenance=json.loads(rendered['reference-provenance.json'])
        lab=LabParser().parse(str(LAB))
        self.assertEqual(len(lab.machines),92); self.assertEqual(len(lab.links),228)
        self.assertEqual(len(provenance['original_graph']),88)
        self.assertEqual(set(lab.machines)-set(provenance['original_graph']),{'dhcp1','lb1','monitor1','monitor2'})
        for name,ports in provenance['original_graph'].items():
            self.assertEqual({str(i):p.link.name for i,p in lab.machines[name].interfaces.items()},ports)
        plan=json.loads((LAB/'address-plan.json').read_text())
        self.assertEqual(len(plan['routers']),52)
        self.assertEqual(len(plan['endpoints']),40)
        domains=defaultdict(set); addresses=[]
        for node in plan['routers'].values():
            for port in node['interfaces']:
                address=ipaddress.ip_interface(port['address']);domains[port['domain']].add(address.network);addresses.append(address.ip)
        for node in plan['endpoints'].values():
            address=ipaddress.ip_interface(node['address']+'/24');domains[node['domain']].add(address.network);addresses.append(address.ip)
        self.assertEqual(len(domains),228)
        self.assertTrue(all(len(nets)==1 for nets in domains.values()))
        self.assertEqual(len(addresses),len(set(addresses)))

    def test_original_asns_neighbors_router_ids_and_prefixes_are_preserved(self):
        import os
        os.environ['BASE_DIR']=str(ROOT/'SADE-NetworkAgent')
        from nika.net_env.data_center_routing.dc_clos_bgp.lab_services import DCClosService
        source=DCClosService('l').lab
        plan=json.loads((LAB/'address-plan.json').read_text())
        for name,node in plan['routers'].items():
            cfg=source.fs.readtext(name+'/etc/frr/frr.conf')
            out=(LAB/name/'etc/frr/frr.conf').read_text()
            self.assertEqual(node['asn'],int(re.search(r'router bgp (\d+)',cfg)[1]))
            self.assertEqual(node['router_id'],re.search(r'bgp router-id (\S+)',cfg)[1])
            self.assertEqual(re.findall(r'neighbor (\S+) remote-as (\d+)',cfg),re.findall(r'neighbor (\S+) remote-as (\d+)',out))
            self.assertEqual(re.findall(r'^\s*network (\S+)',cfg,re.M),re.findall(r'^\s*network (\S+)',out,re.M))
            original=re.findall(r'ip addr add (\S+) dev eth(\d+)',source.fs.readtext(name+'.startup'))
            exported=re.findall(r'ip addr replace (\S+) dev eth(\d+)',(LAB/(name+'.startup')).read_text())
            self.assertEqual(original,exported)
        for name,node in plan['endpoints'].items():
            if name not in source.machines:continue
            original=re.search(r'ip addr add (\S+)/24 dev eth0',source.fs.readtext(name+'.startup'))[1]
            self.assertEqual(node['address'],original)
        self.assertEqual(plan['endpoints']['client_0']['address'],'192.168.0.2')

    def test_four_cases_target_real_devices_peers_and_recover(self):
        from faultbench.scenario import resolve_scenario,parse_scenario
        from tools.configure_nika92_benchmark import render
        config=json.loads((LAB/'benchmark.json').read_text())
        self.assertEqual(len(config['scenarios']),4)
        self.assertEqual(len(config['baseline']),99)
        for path,expected in render().items():self.assertEqual(path.read_text(),expected)
        for ref in config['scenarios']:
            sc=parse_scenario(resolve_scenario(ref))
            self.assertEqual(sc.topology,LAB.name)
            self.assertTrue(sc.pre_check and sc.post_inject_check and sc.recovery_check)
            for inj in (sc.injection,sc.recovery,sc.trigger):
                if inj:subprocess.run(['sh','-n'],input=inj.command,text=True,capture_output=True,check=True)
        roles=json.loads((LAB/'roles.json').read_text())
        all_nodes=roles['routers']+roles['hosts']+sum(roles['servers'].values(),[])
        self.assertEqual(len(all_nodes),92);self.assertEqual(len(set(all_nodes)),92)

class PingErrorStatistics(unittest.TestCase):
    def test_real_unreachable_summary_is_down(self):
        from faultbench.inventory import parse_ping_error_statistics
        evidence=json.loads((ROOT/'docs/validation/soft3888/nika92-reference-external-routing-diagnosis.json').read_text())
        stats=parse_ping_error_statistics(evidence['checks'][0]['output'])
        self.assertEqual(stats['status'],'down')
        self.assertEqual((stats['tx'],stats['rx'],stats['loss_percent']),(2,0,100))

    def test_missing_or_inconsistent_statistics_cannot_be_reachability(self):
        from faultbench.inventory import parse_ping_error_statistics
        for output in ['[TIMEOUT] ping exceeded10s', 'ping: command not found', '',
                       '0 packets transmitted, 0 received, +2 errors, 100% packet loss',
                       '2 packets transmitted, 2 received, +2 errors, 100% packet loss']:
            self.assertIsNone(parse_ping_error_statistics(output))

if __name__=='__main__':unittest.main()
