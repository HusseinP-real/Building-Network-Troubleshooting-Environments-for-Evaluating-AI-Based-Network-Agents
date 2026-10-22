#!/usr/bin/env python3
"""Export pinned NIKA DCClosService(l), preserving its graph, then add 4 services."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
NAME = 'NIKA_Clos_Jiayuan_92Devices'
PIN = 'aa8488a09ddb3a57e08f8137afd04bc87886e734'
SOURCE = 'src/nika/net_env/data_center_routing/dc_clos_bgp/lab_services.py'


def render():
    dependency = ROOT / 'SADE-NetworkAgent'
    commit = subprocess.check_output(['git', '-C', str(dependency), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != PIN:
        raise ValueError(f'Expected pinned NIKA reference {PIN}, got {commit}; review before regenerating')
    pinned_source = subprocess.check_output(['git', '-C', str(dependency), 'show', PIN + ':' + SOURCE])
    if pinned_source != (dependency / SOURCE).read_bytes():
        raise ValueError('Reference source differs from pinned commit; preserve and review before exporting')
    # Source constructor only creates an in-memory Lab; it does not deploy it.
    os.environ.setdefault('BASE_DIR', str(dependency))
    from nika.net_env.data_center_routing.dc_clos_bgp.lab_services import DCClosService
    import nika.net_env.data_center_routing.dc_clos_bgp.lab_services as source_module
    previous_base = source_module.BASE_DIR
    source_module.BASE_DIR = str(dependency)
    try:
        original = DCClosService(topo_size='l').lab
    finally:
        source_module.BASE_DIR = previous_base
    assert len(original.machines) == 88 and len(original.links) == 228
    files = {}
    def put(path, text): files[path] = text.rstrip() + '\n'
    # Reuse already tested service lifecycle scripts, not a new service framework.
    templates = ROOT / 'tools/soft3888-templates'
    dns_control = (templates / 'dns-control').read_text()
    lb_control = (templates / 'lb-control').read_text()
    router_names = [n for n in original.machines if 'router' in n]
    source_graph = {n: {str(i): port.link.name for i, port in m.interfaces.items()} for n, m in original.machines.items()}
    graph = {n: dict(v) for n, v in source_graph.items()}
    source_files = {p: hashlib.sha256(original.fs.readbytes(p)).hexdigest() for p in original.fs.walk.files('/')}
    addresses, peers, asns, router_ids = {}, {}, {}, {}
    for name in original.machines:
        text = original.fs.readtext(name + '.startup')
        addresses[name] = {int(eth): addr for addr, eth in re.findall(r'ip addr add (\S+) dev eth(\d+)', text)}
        if name in router_names:
            cfg = original.fs.readtext(name + '/etc/frr/frr.conf')
            asns[name] = int(re.search(r'router bgp (\d+)', cfg)[1])
            router_ids[name] = re.search(r'bgp router-id (\S+)', cfg)[1]
            peers[name] = [(ip, int(asn)) for ip, asn in re.findall(r'neighbor (\S+) remote-as (\d+)', cfg)]
            networks = re.findall(r'^\s*network (\S+)', cfg, re.M)
            lines = [f'hostname {name}', 'log file /var/log/frr/frr.log', f'router bgp {asns[name]}',
                     f' bgp router-id {router_ids[name]}', ' no bgp ebgp-requires-policy',
                     ' bgp bestpath as-path multipath-relax', ' timers bgp 5 15']
            for ip, asn in peers[name]:
                lines += [f' neighbor {ip} remote-as {asn}', f' neighbor {ip} timers connect 3']
            lines += [' address-family ipv4 unicast', '  maximum-paths 32']
            lines += [f'  network {net}' for net in networks]
            lines += [' exit-address-family', '!']
            put(name + '/etc/frr/frr.conf', '\n'.join(lines))
    # Join existing reference LANs; none of the 88 devices or 228 links is removed.
    extras = {'dhcp1': ('client_0', '192.168.0.67/24'),
              'lb1': ('webserver0_pod0', '10.0.1.80/24'),
              'monitor1': ('webserver6_pod2', '10.2.7.200/24'),
              'monitor2': ('webserver6_pod3', '10.3.7.200/24')}
    for name, (anchor, addr) in extras.items():
        graph[name] = {'0': graph[anchor]['0']}
        addresses[name] = {0: addr}
    conf = []
    for name, ports in graph.items():
        conf += [f'{name}[{i}]="{domain}"' for i, domain in ports.items()]
        conf += [f'{name}[image]="soft3888/{"frr:10.5.3-v1" if name in router_names else "host:bookworm-v1"}"']
    put('lab.conf', '\n'.join(conf))
    resolver = "printf 'nameserver 10.0.0.2\\nnameserver 10.1.0.2\\noptions timeout:1 attempts:1\\n' > /etc/resolv.conf"
    for name in graph:
        startup = []
        for eth, addr in addresses[name].items():
            startup += [f'ip addr replace {addr} dev eth{eth}', f'ip link set eth{eth} up']
        if name in router_names:
            startup += ["sed -i 's/bgpd=no/bgpd=yes/g' /etc/frr/daemons", '/etc/init.d/frr start',
                        'for attempt in 1 2 3 4 5; do vtysh -b && break; sleep 2; done']
        else:
            net = ipaddress.ip_interface(addresses[name][0]).network
            startup += [f'ip route replace default via {net.network_address+1}', resolver]
        if name == 'client_0':
            startup = ['ip link set eth0 down', 'ip link set eth0 address 02:38:88:00:00:01', 'ip link set eth0 up',
                       'for attempt in 1 2 3 4 5; do sh /opt/soft3888/dhcp-client renew && break; sleep 2; done']
        if name.startswith('dns_pod') or name == 'dhcp1':
            startup += ['sh /opt/soft3888/dns-control start']
            put(name + '/opt/soft3888/dns-control', dns_control)
        if name.startswith('webserver'):
            addr = addresses[name][0].split('/')[0]
            startup += [f'nohup python3 -m http.server 80 --bind {addr} --directory /var/www/html > /var/log/web.log 2>&1 < /dev/null &']
            put(name + '/var/www/html/index.html', f'<!doctype html><h1>SOFT3888 NIKA Backend {name}</h1>')
        if name == 'lb1': startup += ['sh /opt/soft3888/lb-control start']
        put(name + '.startup', '\n'.join(startup))
    for pod in range(4):
        lines = [f'port=53', f'listen-address=10.{pod}.0.2', 'bind-interfaces', 'no-resolv', 'no-hosts',
                 'host-record=api.nika.test,10.0.1.80']
        for other in range(4):
            lines += [f'host-record=ns{other}.pod{other},10.{other}.0.2']
            lines += [f'host-record=web{web}.pod{other},10.{other}.{web+1}.2' for web in range(7)]
        put(f'dns_pod{pod}/etc/dnsmasq.d/clos.conf', '\n'.join(lines))
    put('dhcp1/etc/dnsmasq.d/clos.conf', '''port=0
interface=eth0
bind-interfaces
dhcp-authoritative
dhcp-range=192.168.0.100,192.168.0.120,255.255.255.0,5m
dhcp-host=02:38:88:00:00:01,client-0,192.168.0.2
dhcp-option=option:router,192.168.0.1
dhcp-option=option:dns-server,10.0.0.2,10.1.0.2
dhcp-leasefile=/var/lib/misc/dnsmasq.leases
log-dhcp
log-facility=/var/log/dhcp.log''')
    put('client_0/opt/soft3888/dhcp-client', (templates/'dhcp-client').read_text())
    put('lb1/opt/soft3888/lb-control', lb_control)
    cfg = (templates/'haproxy-nika.cfg').read_text()
    put('lb1/etc/haproxy/haproxy.cfg', cfg)
    monitor = (templates/'monitor-nika.py').read_text()
    for name in ['monitor1','monitor2']: put(name+'/opt/soft3888/check-services.py',monitor)
    servers = dict(dns=[f'dns_pod{p}' for p in range(4)], web=[n for n in graph if n.startswith('webserver')], dhcp=['dhcp1'], load_balancer=['lb1'])
    roles = dict(routers=router_names, hosts=[f'client_{p}' for p in range(4)]+['monitor1','monitor2'], servers=servers, reachability_destinations=['client_0','client_1'])
    put('roles.json', json.dumps(roles, indent=2))
    plan = dict(routers={n:dict(asn=asns[n],router_id=router_ids[n],interfaces=[dict(domain=graph[n][str(i)],address=a) for i,a in addresses[n].items()],peers=[dict(address=ip,asn=asn) for ip,asn in peers[n]]) for n in router_names}, endpoints={n:dict(address=addresses[n][0].split('/')[0],domain=graph[n]['0'],dhcp=n=='client_0') for n in graph if n not in router_names})
    put('address-plan.json', json.dumps(plan,indent=2))
    provenance = dict(upstream='https://github.com/Overlxrd-uwu/SADE-NetworkAgent', commit=commit, source_path=SOURCE, source_sha256=hashlib.sha256((dependency/SOURCE).read_bytes()).hexdigest(), constructor="DCClosService(topo_size='l')", original_devices=88, original_collision_domains=228, final_devices=len(graph), final_collision_domains=len(original.links), original_graph=source_graph, added_graph={n:graph[n] for n in extras}, reference_generated_file_sha256=source_files, adaptations=['Explicit compact images and verified shared runtime on vfs; no stress limits.', 'FRR IPv4 address-family syntax, explicit interface up, bounded startup replay, faster BGP timers; preserve ASN/router-id/network/neighbor values.', 'dnsmasq replaces systemctl/BIND startup; preserve all original webX.podY records, replicate across four DNS endpoints.', 'Add real web content and reuse existing service lifecycle/validation tools.', 'client_0 keeps reference IP .2 via a real DHCP reservation; added 4 service/management endpoints share existing LANs.'])
    put('reference-provenance.json', json.dumps(provenance,indent=2))
    assert len(graph)==92
    return files


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,default=ROOT/'topology_kathara'/NAME)
    args=ap.parse_args();files=render()
    for rel,text in files.items():
        p=args.output/rel
        if p.exists() and p.read_text()!=text:raise SystemExit(f'Refusing to overwrite changed file: {p}')
    for rel,text in files.items():
        p=args.output/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    print(f'Exported pinned NIKA(88) + 4 = 92 devices / 228 collision domains: {args.output}')

if __name__=='__main__':main()
