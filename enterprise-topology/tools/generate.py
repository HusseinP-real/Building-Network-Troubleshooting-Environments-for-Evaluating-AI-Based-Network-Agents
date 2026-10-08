#!/usr/bin/env python3
"""Generate the complete, independently authored Kathara lab (stdlib only)."""
import csv
import ipaddress
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_PREFIX = 'enterprise-topology'
nodes = {f'r{i}': {'role': 'router', 'ports': []} for i in range(1, 11)}
nodes.update({f's{i}': {'role': 'switch', 'ports': []} for i in range(1, 26)})
segments = [
    (110, '10.10.10', 'staff', 's3', 10), (120, '10.10.20', 'guest', 's4', 10),
    (210, '10.20.10', 'office', 's7', 20), (220, '10.20.20', 'engineering', 's8', 20),
    (310, '10.30.10', 'app', 's11', 30), (320, '10.30.20', 'database', 's12', 30),
    (410, '10.40.10', 'dmz', 's13', 0), (420, '10.40.20', 'infra', 's14', 0),
    (430, '10.40.30', 'ops', 's15', 0),
]
links = []

def link(a, b, kind, **data):
    name = f'wire{len(links)+1:02}'
    ends = []
    for node, peer in [(a,b),(b,a)]:
        port = {'interface': f'eth{len(nodes[node]["ports"])}', 'peer': peer,
                'link': name, 'kind': kind, **data}
        nodes[node]['ports'].append(port)
        ends.append({'node': node, 'interface': port['interface']})
    links.append({'name': name, 'endpoints': ends, 'kind': kind, **data})

pairs = [('r1','r2'),('r1','r3'),('r2','r4'),('r1','r4'),('r2','r3'),('r3','r4'),
         ('r1','r5'),('r2','r6'),('r1','r7'),('r2','r8'),('r1','r9'),('r2','r10'),
         ('r2','r5'),('r1','r6'),('r2','r7'),('r1','r8'),('r2','r9'),('r1','r10'),
         ('r5','r6'),('r7','r8'),('r9','r10')]
for i,(a,b) in enumerate(pairs):
    net = ipaddress.ip_network(f'10.255.0.{i*4}/30')
    area = 0 if i < 18 else (i-17)*10
    link(a,b,'routed',area=area,subnet=str(net))
    for n, ip in [(a,net[1]),(b,net[2])]: nodes[n]['ports'][-1]['address']=f'{ip}/30'

for region, (ra,rb,sa,sb,ac,bc) in enumerate([(5,6,1,2,3,4),(7,8,5,6,7,8),(9,10,9,10,11,12)]):
    vlans=[segments[region*2][0],segments[region*2+1][0]]
    for a,b in [(f'r{ra}',f's{sa}'),(f'r{rb}',f's{sb}'),(f's{sa}',f's{sb}'),
                (f's{sa}',f's{ac}'),(f's{sb}',f's{ac}'),(f's{sa}',f's{bc}'),(f's{sb}',f's{bc}')]:
        link(a,b,'trunk',vlans=vlans)
# Ten further dual-homed access switches extend the three regional fabrics.
# Each has its own bridge and container, rather than acting as an alias for a link.
extra_switches = [(16,1,2),(17,1,2),(18,1,2),(19,1,2),
                  (20,5,6),(21,5,6),(22,5,6),
                  (23,9,10),(24,9,10),(25,9,10)]
for number, left, right in extra_switches:
    vlans = [segments[0 if number < 20 else 2 if number < 23 else 4][0],
             segments[1 if number < 20 else 3 if number < 23 else 5][0]]
    link(f's{left}', f's{number}', 'trunk', vlans=vlans)
    link(f's{right}', f's{number}', 'trunk', vlans=vlans)
for vlan,sub,host,sw,area in segments[6:]:
    for r in ['r3','r4']: link(r,sw,'trunk',vlans=[vlan])
for vlan,sub,host,sw,area in segments:
    nodes[host]={'role':'host','ports':[], 'vlan':vlan, 'address':sub+'.10/24', 'gateway':sub+'.1', 'dhcp':vlan<300}
    link(sw,host,'access',vlans=[vlan])

# 31 additional independent endpoints: 40 hosts + 25 switches + 10 routers.
# Static addresses avoid making topology size depend on DHCP lease timing.
extra_hosts = [
    (110,'staff',6,[16,17,18,19]), (120,'guest',5,[16,17,18,19]),
    (210,'office',5,[20,21,22]), (220,'engineering',5,[20,21,22]),
    (310,'app_client',5,[23,24,25]), (320,'db_client',5,[23,24,25]),
]
for vlan, prefix, count, switches in extra_hosts:
    sub = next(s[1] for s in segments if s[0] == vlan)
    for index in range(1, count + 1):
        name = f'{prefix}{index:02}'
        nodes[name] = {'role':'host','ports':[], 'vlan':vlan,
                       'address':f'{sub}.{19+index}/24', 'gateway':f'{sub}.1', 'dhcp':False}
        link(f's{switches[(index-1) % len(switches)]}', name, 'access', vlans=[vlan])

def write(name, text):
    p=ROOT/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)

def base():
    return ['#!/bin/bash','set -euo pipefail','exec > /var/log/enterprise-startup.log 2>&1',
            'ip link set lo up']

def policies():
    return [
        'iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.2 -d 10.40.20.10 -p udp --sport 67 --dport 67 -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.3 -d 10.40.20.10 -p udp --sport 67 --dport 67 -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.0/24 -d 10.40.20.10 -p udp --dport 53 -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.0/24 -d 10.40.20.10 -p tcp --dport 53 -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.0/24 -d 10.40.10.10 -p tcp --dport 80 -j ACCEPT',
        'iptables -A FORWARD -s 10.10.20.0/24 -j REJECT',
        'iptables -A FORWARD -d 10.30.20.10 -s 10.30.10.10 -p tcp --dport 8080 -j ACCEPT',
        'iptables -A FORWARD -d 10.30.20.10 -s 10.40.30.0/24 -j ACCEPT',
        'iptables -A FORWARD -d 10.30.20.10 -j REJECT',
    ]

lab=['LAB_NAME="Independent Enterprise Topology 75"','LAB_DESCRIPTION="10 routers, 25 switches, 40 endpoints"']
for name,node in nodes.items():
    node['image'] = f'{IMAGE_PREFIX}:{name}'
    lab.append(f'{name}[image]="{node["image"]}"')
    for key,value in [('net.ipv4.ip_forward', int(node['role']=='router')), ('net.ipv4.conf.all.rp_filter',0), ('net.ipv4.conf.default.rp_filter',0)]:
        lab.append(f'{name}[sysctl]="{key}={value}"')
    for p in node['ports']: lab.append(f'{name}[{p["interface"][3:]}]={p["link"]}')
    sh=base()
    for p in node['ports']: sh.append(f'ip link set {p["interface"]} up')
    if node['role']=='router':
        num=int(name[1:]); sh += [f'ip addr add 10.255.255.{num}/32 dev lo']
        frr=[f'hostname {name}','service integrated-vtysh-config','log file /var/log/frr/enterprise.log','interface lo',' ip ospf area 0','!']
        active=[]; vr=[]; relays=[]
        for p in node['ports']:
            intf=p['interface']
            if p['kind']=='routed':
                sh.append(f'ip addr add {p["address"]} dev {intf}')
                frr += [f'interface {intf}',f' ip ospf area {p["area"]}',' ip ospf network point-to-point',' ip ospf hello-interval 1',' ip ospf dead-interval 4','!']
                active.append(intf)
            else:
                for vlan in p['vlans']:
                    seg=next(s for s in segments if s[0]==vlan); _,sub,_,_,area=seg
                    iface=f'{intf}.{vlan}'; primary=num%2==1; actual=2 if primary else 3
                    sh += [f'ip link add link {intf} name {iface} type vlan id {vlan}',f'ip addr add {sub}.{actual}/24 dev {iface}',f'ip link set {iface} up']
                    frr += [f'interface {iface}',f' ip ospf area {area}','!']
                    vr += [f'vrrp_instance V{vlan} {{',' state BACKUP',f' interface {iface}',f' virtual_router_id {vlan//10}',f' priority {150 if primary else 100}',' advert_int 1',' virtual_ipaddress {',f'  {sub}.1/24 dev {iface}',' }','}']
                    if vlan<300: relays.append(f'dhcp-relay={sub}.{actual},10.40.20.10')
        frr += ['router ospf',f' ospf router-id 10.255.255.{num}',' passive-interface default']+[f' no passive-interface {i}' for i in active]+['!']
        write(f'{name}/etc/frr/frr.conf','\n'.join(frr)+'\n')
        write(f'{name}/etc/keepalived/keepalived.conf','\n'.join(vr)+'\n')
        sh += ["sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons",'chown frr:frr /etc/frr/frr.conf','service frr start']
        if vr: sh.append('keepalived -f /etc/keepalived/keepalived.conf --log-console')
        if relays:
            write(f'{name}/etc/dnsmasq-relay.conf','port=0\n'+'\n'.join(relays)+'\n')
            sh.append('dnsmasq --conf-file=/etc/dnsmasq-relay.conf')
        sh += policies()
    elif node['role']=='switch':
        n=int(name[1:]); priority=4096 if n in (1,5,9) else 8192 if n in (2,6,10) else 32768
        sh += [f'ip link add br0 type bridge vlan_filtering 1 stp_state 1 priority {priority} forward_delay 400', 'ip link set br0 up']
        for p in node['ports']:
            iface=p['interface']; sh += [f'ip link set {iface} master br0',f'bridge vlan del dev {iface} vid 1']
            for v in p['vlans']:
                suffix=' pvid untagged' if p['kind']=='access' else ''
                sh.append(f'bridge vlan add dev {iface} vid {v}{suffix}')
        # Disable bridge netfilter if available: policy is enforced only on routers.
        # No switch ACLs; bridge forwarding remains unrestricted.
    else:
        # IP forwarding is disabled through lab.conf sysctl metadata.
        if node['dhcp']:
            sh.append('dhclient -4 -nw eth0')
        else:
            sh += [f'ip addr add {node["address"]} dev eth0',f'ip route replace default via {node["gateway"]}',"printf 'nameserver 10.40.20.10\\n' > /etc/resolv.conf"]
        if name=='infra':
            conf=['interface=eth0','bind-interfaces','no-resolv','domain=enterprise.test','dhcp-authoritative','log-dhcp',
                  'address=/app.enterprise.test/10.30.10.10','address=/dmz.enterprise.test/10.40.10.10','address=/database.enterprise.test/10.30.20.10']
            for v,sub,*_ in segments[:4]:
                conf += [f'dhcp-range=set:v{v},{sub}.100,{sub}.150,255.255.255.0,1h',f'dhcp-option=tag:v{v},option:router,{sub}.1',f'dhcp-option=tag:v{v},option:dns-server,10.40.20.10']
            write('infra/etc/dnsmasq.conf','\n'.join(conf)+'\n'); sh += ['mkdir -p /var/lib/misc','dnsmasq --conf-file=/etc/dnsmasq.conf']
        if name in ('app','database','dmz'):
            write(f'{name}/srv/www/index.html',f'{name}: healthy\n')
            port=8080 if name=='database' else 80
            if name=='app':
                write('app/srv/app.py', '''from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with urlopen('http://10.30.20.10:8080/', timeout=2) as response:
                data=response.read()
            status, body=200, b'app: healthy\\n' + data
        except Exception:
            status, body=503, b'app: database dependency unavailable\\n'
        self.send_response(status)
        self.send_header('Content-Type','text/plain')
        self.end_headers()
        self.wfile.write(body)

HTTPServer(('0.0.0.0',80),Handler).serve_forever()
''')
                sh.append('python3 /srv/app.py > /var/log/service.log 2>&1 &')
            else:
                sh.append(f'python3 -m http.server {port} --bind 0.0.0.0 --directory /srv/www > /var/log/service.log 2>&1 &')
    sh.append('touch /tmp/enterprise-ready')
    write(f'{name}.startup','\n'.join(sh)+'\n')
write('lab.conf','\n'.join(lab)+'\n')
write('inventory.json',json.dumps({'base_image':f'{IMAGE_PREFIX}:base','nodes':nodes,'links':links},indent=2)+'\n')
with (ROOT/'docs/interfaces.csv').open('w') as f:
    w=csv.writer(f, lineterminator="\n"); w.writerow(['node','interface','peer','link','kind','address','area','vlans'])
    for name,node in nodes.items():
        for p in node['ports']: w.writerow([name,p['interface'],p['peer'],p['link'],p['kind'],p.get('address',''),p.get('area',''),','.join(map(str,p.get('vlans',[])))])
print(f'Generated {len(nodes)} nodes and {len(links)} point-to-point links in {ROOT}')
