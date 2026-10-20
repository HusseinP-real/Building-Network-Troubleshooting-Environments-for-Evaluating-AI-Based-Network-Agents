#!/usr/bin/env python3
import json,sys,re,ipaddress
from pathlib import Path
root=Path(__file__).resolve().parent.parent
x=json.loads((root/'topology.json').read_text());nodes=x['nodes'];links=x['links'];assert len(nodes)==75,(len(nodes),'devices');assert sum(n['type']=='router' for n in nodes.values())==30;assert sum(n['type']=='host' for n in nodes.values())==45
pairs={};addresses=set()
for n in nodes:
 assert (root/'lab'/f'{n}.startup').is_file(),n
 if nodes[n]['type']=='router':assert (root/'lab'/n/'etc/frr/frr.conf').is_file(),n
for l in links:
 assert l['a'] in nodes and l['b'] in nodes
 assert l['id'] not in pairs;lmap=pairs.setdefault(l['id'],[]);lmap.extend([l['a'],l['b']]);assert len(lmap)==2
 net=ipaddress.ip_network(f'{l["a_ip"]}/{l["prefix"]}',strict=False);assert ipaddress.ip_address(l['b_ip']) in net
 for v in ['a_ip','b_ip']:
  assert l[v] not in addresses,(l,v);addresses.add(l[v])
conf=(root/'lab/lab.conf').read_text();assert len(re.findall(r'\[image\]=',conf))==75
assert all(len(k)==2 for k in pairs.values())
print(f'STATIC PASS: {len(nodes)} devices, {len(links)} point-to-point domains, 30 routers, 45 hosts, IP uniqueness and files validated.')
print('IMPORTANT: NO runtime Kathara/FRR/BGP/IS-IS verification has been performed.')
