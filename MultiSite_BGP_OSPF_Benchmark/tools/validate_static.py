#!/usr/bin/env python3
"""Static, offline validator: device count, link pairs, IP collision and files."""
import json,ipaddress,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'inventory.json').read_text())
assert (data['device_count'],data['router_count'],data['switch_count'],data['endpoint_count'])==(80,18,20,42)
assert sum(map(len,data['interfaces'].values()))==len([x for x in (ROOT/'lab.conf').read_text().splitlines() if ']="' in x and '[image]' not in x and '[sysctl]' not in x])
addresses={}; cds={}
for node,entries in data['interfaces'].items():
    assert (ROOT/(node+'.startup')).is_file() and (ROOT/node).is_dir()
    assert [e['eth'] for e in entries]==list(range(len(entries)))
    for e in entries:
        cds.setdefault(e['cd'],[]).append(node)
        if e['addr']:
            ipaddress.ip_interface(e['cidr']);assert e['addr'] not in addresses,(e['addr'],node,addresses.get(e['addr']))
            addresses[e['addr']]=node
for l in data['p2p_links']:
    assert sorted(cds[l['collision_domain']])==sorted([l['a'],l['b']])
for cd,members in cds.items():
    assert len(members)>=2,(cd,members)
for node in data['interfaces']:
    if node in ('e1','e2','e3','e4','a1','a2','a3','b1','b2','b3') or node.endswith(('_r1','_r2')):
        assert (ROOT/node/'etc/frr/frr.conf').is_file()
print(f'STATIC PASS: {data["device_count"]} devices; {len(cds)} collision domains; {len(addresses)} distinct IPs; {len(data["p2p_links"])} routed P2P links')
