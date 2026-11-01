#!/usr/bin/env python3
"""Generate a fixed three-spine, six-rack eBGP data-centre fabric."""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'soft3888-fabric:v1'


def inventory():
    nodes = {}
    for s in range(1, 4):
        nodes[f'spine{s}'] = dict(role='spine', asn=65000, loopback=f'10.254.0.{s}/32', ports=[])
    for r in range(1, 7):
        nodes[f'leaf{r}'] = dict(role='leaf', asn=65100+r, loopback=f'10.254.1.{r}/32', rack=r, subnet=f'10.60.{r}.0/24', ports=[])
        nodes[f'rack{r}'] = dict(role='switch', rack=r, ports=[])
        for h in range(1, 11):
            nodes[f'rack{r}h{h}'] = dict(role='server' if h == 1 else 'client', rack=r, address=f'10.60.{r}.{10+h}/24', gateway=f'10.60.{r}.1', ports=[])
    links = []

    def link(a, b, kind, subnet=None):
        name = f'wire{len(links)+1:02}'
        ends = []
        for index, (node, peer) in enumerate([(a, b), (b, a)]):
            port = dict(interface=f'eth{len(nodes[node]["ports"])}', peer=peer, link=name, kind=kind)
            if subnet:
                # /31 has two usable addresses, including the network address.
                import ipaddress
                port['address'] = f'{ipaddress.ip_network(subnet)[index]}/31'
            nodes[node]['ports'].append(port)
            ends.append(dict(node=node, interface=port['interface']))
        links.append(dict(name=name, kind=kind, endpoints=ends, **({'subnet': subnet} if subnet else {})))

    for r in range(1, 7):
        for s in range(1, 4):
            link(f'leaf{r}', f'spine{s}', 'fabric', f'172.22.0.{2*((r-1)*3+s-1)}/31')
    for r in range(1, 7):
        link(f'leaf{r}', f'rack{r}', 'rack')
        nodes[f'leaf{r}']['ports'][-1]['address'] = f'10.60.{r}.1/24'
        for h in range(1, 5):
            link(f'rack{r}', f'rack{r}h{h}', 'access')
    for r in range(1, 7):
        for h in range(5, 11):
            link(f'rack{r}', f'rack{r}h{h}', 'access')
    return dict(schema_version=1, image=IMAGE, nodes=nodes, links=links,
                services=dict(application='rack5h1', backend='rack6h1', port=8080))


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def router_config(name, node, inv):
    all_prefixes = [m['subnet'] for m in inv['nodes'].values() if m['role'] == 'leaf']
    all_prefixes += [m['loopback'] for m in inv['nodes'].values() if 'loopback' in m]
    local = [node['loopback']] + ([node['subnet']] if node['role'] == 'leaf' else [])
    lines = ['frr defaults traditional', f'hostname {name}', 'log file /var/log/frr/fabric.log', 'service integrated-vtysh-config', '!']
    for i, prefix in enumerate(all_prefixes, 1):
        lines.append(f'ip prefix-list FABRIC seq {i*10} permit {prefix}')
    for i, prefix in enumerate(local, 1):
        lines.append(f'ip prefix-list LOCAL seq {i*10} permit {prefix}')
    # Each spine accepts only the two exact prefixes owned by its leaf peer.
    for port in node['ports']:
        if port['kind'] != 'fabric':
            continue
        peer = inv['nodes'][port['peer']]
        if node['role'] == 'spine':
            label = port['peer'].upper()
            lines += [f'ip prefix-list {label} seq 10 permit {peer["subnet"]}', f'ip prefix-list {label} seq 20 permit {peer["loopback"]}']
    lines += [f'router bgp {node["asn"]}', f' bgp router-id {node["loopback"].split("/")[0]}', ' bgp ebgp-requires-policy', ' bgp network import-check', ' no bgp default ipv4-unicast', ' timers bgp 3 9']
    peers = []
    for port in node['ports']:
        if port['kind'] != 'fabric':
            continue
        peer = inv['nodes'][port['peer']]
        remote = next(p for p in peer['ports'] if p['link'] == port['link'])['address'].split('/')[0]
        peers.append((remote, port['peer']))
        lines += [f' neighbor {remote} remote-as {peer["asn"]}', f' neighbor {remote} description {port["peer"]}']
    lines += [' address-family ipv4 unicast', '  maximum-paths 3']
    lines += [f'  network {prefix}' for prefix in local]
    for remote, peer in peers:
        incoming = peer.upper() if node['role'] == 'spine' else 'FABRIC'
        outgoing = 'FABRIC' if node['role'] == 'spine' else 'LOCAL'
        lines += [f'  neighbor {remote} activate', f'  neighbor {remote} prefix-list {incoming} in', f'  neighbor {remote} prefix-list {outgoing} out']
    return '\n'.join(lines + [' exit-address-family', '!', 'line vty', '!']) + '\n'


APP = '''from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urlopen('http://10.60.6.11:8080/', timeout=2) as response:
                backend = response.read()
            status, body = 200, b'application: healthy\\n' + backend
        except Exception:
            status, body = 503, b'application: backend unavailable\\n'
        self.send_response(status)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(body)

HTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
'''


def generate(root=ROOT):
    inv = inventory()
    conf = ['LAB_NAME="SOFT3888 Three-Spine Data Centre Fabric"', 'LAB_DESCRIPTION="75 devices, 84 links, eBGP and three-path ECMP"']
    for name, node in inv['nodes'].items():
        router = node['role'] in ('spine', 'leaf')
        conf += [f'{name}[image]="{IMAGE}"', f'{name}[sysctl]="net.ipv4.ip_forward={int(router)}"', f'{name}[sysctl]="net.ipv4.conf.all.rp_filter=0"', f'{name}[sysctl]="net.ipv4.conf.default.rp_filter=0"']
        script = ['#!/bin/bash', 'set -euo pipefail', 'exec > /var/log/fabric-startup.log 2>&1', 'ip link set lo up']
        for p in node['ports']:
            conf.append(f'{name}[{p["interface"][3:]}]={p["link"]}')
            script.append(f'ip link set {p["interface"]} up')
            if 'address' in p:
                script.append(f'ip addr add {p["address"]} dev {p["interface"]}')
        if router:
            script += [f'ip addr add {node["loopback"]} dev lo', "sed -i -E 's/^(zebra|bgpd)=no/\\1=yes/; s/^(ospfd|ospf6d|isisd|ripd|ripngd)=yes/\\1=no/' /etc/frr/daemons", 'chown frr:frr /etc/frr/frr.conf', 'chmod 640 /etc/frr/frr.conf', 'service frr start']
            write(root, f'{name}/etc/frr/frr.conf', router_config(name, node, inv))
        elif node['role'] == 'switch':
            script += ['ip link add br0 type bridge stp_state 0', 'ip link set br0 up']
            script += [f'ip link set {p["interface"]} master br0' for p in node['ports']]
        else:
            script += [f'ip addr add {node["address"]} dev eth0', f'ip route replace default via {node["gateway"]}']
            if node['role'] == 'server':
                if name == 'rack5h1':
                    write(root, f'{name}/srv/app.py', APP)
                    script += ['python3 /srv/app.py > /var/log/service.log 2>&1 &']
                else:
                    write(root, f'{name}/srv/www/index.html', f'{name}: healthy\n')
                    script += ['python3 -m http.server 8080 --bind 0.0.0.0 --directory /srv/www > /var/log/service.log 2>&1 &']
        script.append('touch /tmp/fabric-ready')
        write(root, f'{name}.startup', '\n'.join(script)+'\n')
    write(root, 'lab.conf', '\n'.join(conf)+'\n')
    write(root, 'inventory.json', json.dumps(inv, indent=2)+'\n')
    (root/'docs').mkdir(exist_ok=True)
    with (root/'docs/interfaces.csv').open('w') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['node', 'interface', 'peer', 'link', 'kind', 'address'])
        for name, node in inv['nodes'].items():
            for port in node['ports']:
                writer.writerow([name, port['interface'], port['peer'], port['link'], port['kind'], port.get('address', '')])
    print(f'Generated {len(inv["nodes"])} devices, {len(inv["links"])} links')


if __name__ == '__main__':
    generate()
