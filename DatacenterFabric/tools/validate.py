#!/usr/bin/env python3
"""Check inventory, physical wiring, addressing and generated routing intent offline."""
from collections import Counter
import ipaddress
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    inv = json.loads((root/'inventory.json').read_text())
    nodes, links = inv['nodes'], inv['links']
    assert len(nodes) == 75 and len(links) == 84, 'Wrong device/link count'
    roles = Counter(n['role'] for n in nodes.values())
    assert roles == dict(spine=3, leaf=6, switch=6, server=6, client=54), roles
    assert Counter(l['kind'] for l in links) == dict(fabric=18, rack=6, access=60)
    for rack in range(1, 7):
        switch = nodes[f'rack{rack}']
        assert [p['peer'] for p in switch['ports']] == [f'leaf{rack}'] + [f'rack{rack}h{h}' for h in range(1, 11)], 'Wrong rack membership or port order'
        script = (root/f'rack{rack}.startup').read_text()
        for port in switch['ports']:
            assert f'ip link set {port["interface"]} master br0' in script, 'Missing bridge port'
    used, addresses, graph = set(), set(), {name:set() for name in nodes}
    conf = (root/'lab.conf').read_text()
    wiring = dict(((n, f'eth{p}'), wire) for n,p,wire in re.findall(r'^(\w+)\[(\d+)\]=(\w+)$', conf, re.M))
    assert len(wiring) == 168, 'Wrong lab.conf interface count'
    for link in links:
        assert len(link['endpoints']) == 2
        endpoints = link['endpoints']
        a,b = (e['node'] for e in endpoints)
        graph[a].add(b); graph[b].add(a)
        ips = []
        for endpoint in endpoints:
            n, interface = endpoint['node'], endpoint['interface']
            key = (n, interface)
            assert key not in used, f'Duplicate port {key}'
            used.add(key)
            assert wiring[key] == link['name'], key
            port = next(p for p in nodes[n]['ports'] if p['interface'] == interface)
            assert port['link'] == link['name'] and port['peer'] == (b if n == a else a)
            if 'address' in port:
                addr = ipaddress.ip_interface(port['address'])
                assert addr.ip not in addresses, f'Duplicate address {addr.ip}'
                addresses.add(addr.ip)
                ips.append(addr)
        if link['kind'] == 'fabric':
            assert {nodes[n]['role'] for n in (a,b)} == {'leaf','spine'}
            assert len(ips) == 2 and ips[0].network == ips[1].network == ipaddress.ip_network(link['subnet'])
    reached, queue = set(), ['spine1']
    while queue:
        n = queue.pop()
        if n not in reached:
            reached.add(n); queue.extend(graph[n]-reached)
    assert reached == set(nodes), 'Disconnected topology'
    for name, node in nodes.items():
        script = root/f'{name}.startup'
        subprocess.run(['bash','-n',str(script)], check=True, capture_output=True)
        if node['role'] in ('leaf','spine'):
            cfg = (root/name/'etc/frr/frr.conf').read_text()
            assert f'router bgp {node["asn"]}' in cfg
            assert f'network {node["loopback"]}' in cfg
            assert 'bgp ebgp-requires-policy' in cfg and 'bgp network import-check' in cfg
            assert 'maximum-paths 3' in cfg
            for port in node['ports']:
                if port['kind'] == 'fabric':
                    peer = nodes[port['peer']]
                    remote = next(p for p in peer['ports'] if p['link']==port['link'])['address'].split('/')[0]
                    assert f'neighbor {remote} remote-as {peer["asn"]}' in cfg
                    for direction in ('in','out'):
                        assert re.search(rf'neighbor {re.escape(remote)} prefix-list \w+ {direction}\b', cfg)
            if node['role'] == 'leaf':
                assert len([p for p in node['ports'] if p['kind']=='fabric']) == 3
                assert f'network {node["subnet"]}' in cfg
        elif node['role'] in ('server','client'):
            addr = ipaddress.ip_interface(node['address'])
            assert addr.ip not in addresses
            addresses.add(addr.ip)
            assert ipaddress.ip_address(node['gateway']) in addr.network
            assert f'ip route replace default via {node["gateway"]}' in script.read_text()
    report = dict(passed=True, devices=75, roles=dict(roles), links=84, interfaces=168,
                  connected_devices=len(reached), startup_scripts_checked=75,
                  runtime_validation='75-device live validation pending; saved live reports describe the historical 39-device topology')
    (root/'results').mkdir(exist_ok=True)
    (root/'results/structural-validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    validate()
