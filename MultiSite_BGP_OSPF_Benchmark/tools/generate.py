#!/usr/bin/env python3
"""Deterministically generate a standalone 80-node Kathara BGP/OSPF laboratory."""
from pathlib import Path
from collections import defaultdict
import json, ipaddress

ROOT=Path(__file__).resolve().parents[1]
ROUTERS=['e1','e2','e3','e4','a1','a2','a3','b1','b2','b3','hq_r1','hq_r2','ba_r1','ba_r2','bb_r1','bb_r2','dc_r1','dc_r2']
SITES={'hq':(6,14,'10.10.10.0/24',['hq_r1','hq_r2']), 'ba':(4,9,'10.20.10.0/24',['ba_r1','ba_r2']), 'bb':(4,9,'10.30.10.0/24',['bb_r1','bb_r2']), 'dc':(4,8,'10.40.10.0/24',['dc_r1','dc_r2'])}
EDGES=[('e1','e2'),('e2','e3'),('e3','e4'),('e4','e1'),('e1','hq_r1'),('e2','hq_r2'),('e2','ba_r1'),('e3','ba_r2'),('e3','bb_r1'),('e4','bb_r2'),('e4','dc_r1'),('e1','dc_r2')]
ISP_A=[('a1','a2'),('a2','a3')]; ISP_B=[('b1','b2'),('b2','b3')]
PEERS=[('e1','a1'),('e3','a3'),('e2','b1'),('e4','b3')]
interfaces=defaultdict(list); networks={}; topology=[]

def link(x,y,name,cidr):
    net=ipaddress.ip_network(cidr,strict=True)
    assert net.prefixlen==31
    addresses=list(net.hosts())
    for node,addr in ((x,addresses[0]),(y,addresses[1])):
        interfaces[node].append({'eth':len(interfaces[node]),'cd':name,'addr':str(addr),'cidr':f'{addr}/31','peer':y if node==x else x,'kind':'p2p'})
    topology.append({'a':x,'b':y,'collision_domain':name,'network':cidr})

def lan(node,cd,addr,subnet,kind='lan'):
    interfaces[node].append({'eth':len(interfaces[node]),'cd':cd,'addr':addr,'cidr':f'{addr}/{ipaddress.ip_network(subnet).prefixlen}' if addr else None,'kind':kind})

def p2ps(pairs,prefix,start,tag):
    for i,(x,y) in enumerate(pairs,start):link(x,y,f'{tag}_{i}',f'{prefix}.{i}.0/31')

p2ps(EDGES,'10.255',1,'core')
p2ps(ISP_A,'172.20',1,'ispa')
p2ps(ISP_B,'172.21',1,'ispb')
p2ps(PEERS,'172.31',1,'ebgp')

# Every switch behaves like a transparent Linux bridge: an uplink to the local
# site collision domain plus individually isolated access collision domains.
sitehosts={}
for site,(switch_count,host_count,subnet,routers) in SITES.items():
    net=ipaddress.ip_network(subnet)
    lan(routers[0],f'{site}_lan',str(net.network_address+1),subnet)
    lan(routers[1],f'{site}_lan',str(net.network_address+2),subnet)
    for i in range(1,switch_count+1):lan(f'{site}_sw{i:02d}',f'{site}_lan',None,subnet,'uplink')
    for i in range(1,host_count+1):
        sw=f'{site}_sw{((i-1)%switch_count)+1:02d}'
        cd=f'{site}_access{i:02d}'
        lan(sw,cd,None,subnet,'access')
        host=f'{site}_h{i:02d}'; address=str(net.network_address+20+i)
        lan(host,cd,address,subnet,'host')
        sitehosts[host]={'site':site,'ip':address,'gateway':str(net.network_address+1),'switch':sw}

for letter,router,netstr in [('a','a2','198.18.10.0/24'),('b','b2','198.18.20.0/24')]:
    net=ipaddress.ip_network(netstr); sw=f'ext_{letter}_sw'; host=f'ext_{letter}_web'
    lan(router,f'ext_{letter}_lan',str(net.network_address+1),netstr)
    lan(sw,f'ext_{letter}_lan',None,netstr,'uplink')
    lan(sw,f'ext_{letter}_access',None,netstr,'access')
    lan(host,f'ext_{letter}_access',str(net.network_address+10),netstr,'host')
    sitehosts[host]={'site':f'isp_{letter}','ip':str(net.network_address+10),'gateway':str(net.network_address+1),'switch':sw}

AS={r:65000 if r.startswith('e') or r.endswith(('r1','r2')) else (65010 if r.startswith('a') else 65020) for r in ROUTERS}
# correct AS for enterprise branches and core; the string condition covers all such nodes.
assert len(AS)==18

def is_ospf_peer(node,entry):
    peer=entry.get('peer')
    return peer is not None and AS[node]==AS[peer]

def frr_config(node):
    asn=AS[node]
    output=['frr version 10.0','frr defaults traditional',f'hostname {node}','service integrated-vtysh-config','!']
    if node.startswith('e'):
        output += ['ip route 10.0.0.0/8 Null0','!']
    output += ['router ospf',f' ospf router-id {router_id(node)}', ' redistribute connected']
    if node.startswith('e'): output += [' redistribute bgp metric 40 metric-type 1']
    if node in ('a1','a3','b1','b3'): output += [' redistribute bgp metric 40 metric-type 1']
    for item in interfaces[node]:
        if (item['kind']=='p2p' and is_ospf_peer(node,item)) or (item['kind']=='lan'):
            output += [f' network {ipaddress.ip_network(item["cidr"],strict=False)} area 0']
    output+=['!']
    if node.startswith('e') or node in ('a1','a3','b1','b3'):
        output += [f'router bgp {asn}',f' bgp router-id {router_id(node)}',' no bgp ebgp-requires-policy']
        for item in interfaces[node]:
            peer=item.get('peer')
            if peer and AS[peer]!=asn:
                remote=next(e['addr'] for e in interfaces[peer] if e.get('peer')==node)
                output += [f' neighbor {remote} remote-as {AS[peer]}']
        if node.startswith('e'): output += [' network 10.0.0.0/8']
        elif node.startswith('a'): output += [' network 198.18.10.0/24']
        else: output += [' network 198.18.20.0/24']
        output += ['!']
    output += ['line vty','!']
    return '\n'.join(output)+'\n'

def router_id(node):
    return f'10.254.0.{ROUTERS.index(node)+1}'

def startup(node):
    lines=['#!/bin/bash','set -Eeuo pipefail',"exec > >(tee -a /tmp/soft3888-startup.log) 2>&1","trap 'echo STARTUP_FAILED line=$LINENO command=$BASH_COMMAND >&2' ERR",'echo ROUTER_STARTUP_BEGIN']
    for item in interfaces[node]:
        lines += [f'ip link set eth{item["eth"]} up',f'ip addr replace {item["cidr"]} dev eth{item["eth"]}']
    lines+=['echo ROUTER_INTERFACES_CONFIGURED','mkdir -p /etc/frr',"sed -i 's/^zebra=no/zebra=yes/;s/^bgpd=no/bgpd=yes/;s/^ospfd=no/ospfd=yes/' /etc/frr/daemons",'chown frr:frr /etc/frr/frr.conf','service frr start','sleep 2',"vtysh -c 'show version' >/dev/null",'echo ROUTER_STARTUP_COMPLETE']
    return '\n'.join(lines)+'\n'

def switch_startup(node):
    lines=['#!/bin/bash','set -e','ip link add br0 type bridge','ip link set br0 up']
    for e in interfaces[node]:
        lines += [f'ip link set eth{e["eth"]} up',f'ip link set eth{e["eth"]} master br0']
    return '\n'.join(lines)+'\n'

def host_startup(node):
    e=interfaces[node][0]; h=sitehosts[node]
    lines=['#!/bin/bash','set -e','ip link set eth0 up',f'ip addr replace {e["cidr"]} dev eth0',f'ip route replace default via {h["gateway"]}']
    if node.startswith('ext_'):
        lines += ['mkdir -p /srv/www',f"echo 'SOFT3888 {node} healthy' > /srv/www/index.html",'cd /srv/www', 'nohup python3 -m http.server 8080 --bind 0.0.0.0 >/tmp/http.log 2>&1 &']
    return '\n'.join(lines)+'\n'

def generate():
    devices=sorted(interfaces)
    assert len(devices)==80,(len(devices),devices)
    assert len(ROUTERS)==18 and len([n for n in devices if '_sw' in n])==20 and len(sitehosts)==42
    conf=['# GENERATED by tools/generate.py; do not manually edit']
    for n in devices:
        image='kathara/frr:10' if n in ROUTERS else 'kathara/base:latest'
        conf += [f'{n}[image]="{image}"']
        if n in ROUTERS:
            # Applied by Kathara/Docker at container creation, not in .startup.
            conf += [f'{n}[sysctl]="net.ipv4.ip_forward=1"']
        for entry in interfaces[n]:conf += [f'{n}[{entry["eth"]}]="{entry["cd"]}"']
        (ROOT/f'{n}.startup').write_text(startup(n) if n in ROUTERS else switch_startup(n) if '_sw' in n else host_startup(n))
        (ROOT/f'{n}.startup').chmod(0o755)
        (ROOT/n).mkdir(exist_ok=True)
        if n in ROUTERS:
            p=ROOT/'configs'/n;p.mkdir(parents=True,exist_ok=True)
            (p/'frr.conf').write_text(frr_config(n))
            mounted=ROOT/n/'etc'/'frr';mounted.mkdir(parents=True,exist_ok=True)
            (mounted/'frr.conf').write_text(frr_config(n))
    (ROOT/'lab.conf').write_text('\n'.join(conf)+'\n')
    inventory={'schema':'soft3888-topology-v1','device_count':len(devices),'router_count':18,'switch_count':20,'endpoint_count':42,'autonomous_systems':{'enterprise':65000,'isp_a':65010,'isp_b':65020},'interfaces':dict(interfaces),'p2p_links':topology,'hosts':sitehosts,'site_networks':{k:v[2] for k,v in SITES.items()},'external_networks':{'isp_a':'198.18.10.0/24','isp_b':'198.18.20.0/24'}}
    (ROOT/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    return inventory

if __name__=='__main__':
    result=generate();print(f'Generated {result["device_count"]} devices, {len(result["p2p_links"])} routed P2P links')
