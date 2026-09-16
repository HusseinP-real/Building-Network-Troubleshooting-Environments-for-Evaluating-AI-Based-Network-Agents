"""P20Enterprise v2 design and reproducible Kathara/scenario file generation.

The model describes configuration and expected observations, not an OSPF simulator.
Run build_p20_enterprise.py to regenerate files after an intentional design change.
"""
import ipaddress
import json
import shlex

NAME = 'P20Enterprise'
VERSION = 2


def build_spec():
    nodes = {f'r{i}': {'role': 'core' if i <= 4 else 'abr' if i <= 12 else 'site',
                       'interfaces': {}, 'ospf': {}, 'routes': {},
                       'router_id': f'10.255.255.{i}'} for i in range(1, 17)}
    links = []

    def interface(node, segment, address, area=None, cost=10, passive=False):
        data = nodes[node]
        iface = f'eth{len(data["interfaces"])}'
        data['interfaces'][iface] = [segment, address]
        if area is not None:
            data['ospf'][iface] = {'area': area, 'cost': cost, 'passive': passive}
        return iface

    def link(left, right, area, cost=10):
        number = len(links) + 1
        segment = f'T{number:02}'
        network = f'10.255.{number}.0/30'
        li = interface(left, segment, f'10.255.{number}.1/30', area, cost)
        ri = interface(right, segment, f'10.255.{number}.2/30', area, cost)
        links.append({'segment': segment, 'network': network, 'area': area,
                      'cost': cost, 'ends': [[left, li], [right, ri]]})

    # A ring plus a diagonal; every backbone link has an alternate path.
    for left, right in [(1, 2), (2, 3), (3, 4), (4, 1), (1, 3)]:
        link(f'r{left}', f'r{right}', 0)
    sites = {}
    for site in range(1, 5):
        primary, backup, edge = f'r{2*site+3}', f'r{2*site+4}', f'r{site+12}'
        link(f'r{site}', primary, 0)
        link(f'r{site % 4 + 1}', backup, 0)
        link(primary, edge, site, 10)
        link(backup, edge, site, 100)
        interface(edge, f'USERS{site}', f'10.10.{site}.1/24', site, 1, True)
        interface(edge, f'SERVERS{site}', f'10.40.{site}.1/24', site, 1, True)
        endpoints = []
        for kind, count, base in [('pc', 4, 10), ('server', 2, 40)]:
            for j in range(1, count+1):
                node = f'{kind}{(site-1)*count+j}'
                nodes[node] = {'role': kind, 'site': site, 'interfaces': {},
                               'routes': {'default': f'10.{base}.{site}.1'}}
                interface(node, f'{"USERS" if kind == "pc" else "SERVERS"}{site}',
                          f'10.{base}.{site}.{10+j}/24')
                endpoints.append(node)
        sites[str(site)] = {'router': edge, 'primary_abr': primary, 'backup_abr': backup,
                            'endpoints': endpoints}
    return {'version': VERSION, 'name': NAME, 'nodes': nodes, 'links': links, 'sites': sites}


SPEC = build_spec()


def address(node):
    return str(ipaddress.ip_interface(SPEC['nodes'][node]['interfaces']['eth0'][1]).ip)


def uplink_gateway(interface):
    network = ipaddress.ip_interface(SPEC['nodes']['r13']['interfaces'][interface][1]).network
    return str(network.network_address + 1)


CASES = {
    'healthy': {
        'id': 'p20-enterprise-v2-false-premise-outage', 'node': 'pc1', 'inject': '', 'repair': '',
        'ticket': 'A user reports that HQ cannot reach the other three sites or their servers. Check whether the report is supported by current network evidence.',
        'truth': 'No fault is injected. All nominated paths work and OSPF uses the preferred HQ uplink. Do not invent an outage or change healthy configuration.'},
    'failover': {
        'id': 'p20-enterprise-v2-primary-uplink-failover', 'node': 'r13',
        'inject': 'ip link set eth0 down', 'repair': 'ip link set eth0 up',
        'ticket': 'HQ raised a primary-uplink alarm, but users can still reach the other sites. Determine whether service is down or operating through redundancy.',
        'truth': 'R13 eth0, the preferred HQ uplink to R5, is administratively down. OSPF converges through eth1 and R6. Reachability recovers on the backup path, but redundancy is degraded. Restore eth0 and verify return to the preferred next hop. This test does not establish zero packet loss during convergence.'},
    'isolation': {
        'id': 'p20-enterprise-v2-hq-both-uplinks-down', 'node': 'r13',
        'inject': 'set -e\nip link set eth0 down\nip link set eth1 down',
        'repair': 'set -e\nip link set eth0 up\nip link set eth1 up',
        'ticket': 'HQ PCs and servers can communicate locally but cannot reach other sites. The other three sites can still communicate with one another.',
        'truth': 'Both R13 uplinks eth0 and eth1 are administratively down, isolating HQ from the backbone. Local HQ user/server routing remains available. Restore both uplinks; restoring just the preferred link does not restore redundancy.'},
    'advertisement': {
        'id': 'p20-enterprise-v2-hq-server-ospf-withdrawal', 'node': 'r13',
        'inject': "set -e\nconfig=$(vtysh -c 'show running-config')\npresent=$(printf '%s\\n' \"$config\" | awk '$1==\"network\" && $2==\"10.40.1.0/24\" {n++} END {print n+0}')\nif test \"$present\" -eq 1; then\n  vtysh -c 'configure terminal' -c 'router ospf' -c 'no network 10.40.1.0/24 area 0.0.0.1'\nelif test \"$present\" -ne 0; then\n  exit 1\nfi",
        'repair': "vtysh -c 'configure terminal' -c 'router ospf' -c 'network 10.40.1.0/24 area 0.0.0.1'",
        'ticket': 'Remote sites cannot reach HQ servers, but HQ PCs can reach those servers. Remote access to HQ PCs still works. Investigate routing advertisements as well as interfaces.',
        'truth': 'R13 no longer advertises the HQ server network 10.40.1.0/24 into OSPF area 1. The server interface is up and its connected route remains, so local HQ traffic works. Remote routers lose the OSPF route. Restore the precise network statement; do not add a static-route workaround.'},
    'server-link': {
        'id': 'p20-enterprise-v2-hq-server-interface-down', 'node': 'r13',
        'inject': 'ip link set eth3 down', 'repair': 'ip link set eth3 up',
        'ticket': 'HQ and remote PCs cannot reach HQ servers. The two HQ servers can still reach each other, and communication between PC networks is healthy.',
        'truth': 'R13 eth3, the HQ server-facing interface, is administratively down. Routed access to both HQ servers fails, while their shared-LAN traffic continues. Restore eth3 and verify local and remote access.'},
    'gateway': {
        'id': 'p20-enterprise-v2-pc1-wrong-gateway', 'node': 'pc1',
        'inject': 'ip route replace default via 10.10.1.254',
        'repair': 'ip route replace default via 10.10.1.1',
        'ticket': 'Only PC1 cannot communicate outside its local LAN. PC1 can reach PC2, and the other HQ devices and remote sites work.',
        'truth': 'PC1 uses the unassigned gateway 10.10.1.254 instead of R13 at 10.10.1.1. Its local LAN works, but off-subnet exchanges fail in either direction. Restore the correct default gateway.'},
}

# Site 2 probes every other endpoint; extra probes disambiguate local and remote failures.
PROBES = [('pc5', n) for n, d in SPEC['nodes'].items() if d['role'] in ('pc', 'server') and n != 'pc5']
PROBES += [('pc1', 'pc5'), ('pc1', 'pc2'), ('pc1', 'server1'),
           ('server1', 'server2'), ('pc9', 'pc13'), ('server3', 'server5')]


def expected_ping(case, source, target):
    a, b = SPEC['nodes'][source], SPEC['nodes'][target]
    local = a['interfaces']['eth0'][0] == b['interfaces']['eth0'][0]
    hq_servers = {'server1', 'server2'}
    if case == 'isolation':
        return (a['site'] == 1) == (b['site'] == 1)
    if case == 'server-link':
        return local or not ({source, target} & hq_servers)
    if case == 'advertisement':
        return not ((source in hq_servers and b['site'] != 1) or (target in hq_servers and a['site'] != 1))
    if case == 'gateway':
        return local or 'pc1' not in (source, target)
    return True


def route_count(prefix, gateway=None, protocol=None):
    terms = []
    if gateway:
        terms += [f'via=="{gateway}"']
    if protocol:
        terms += [f'proto=="{protocol}"']
    # Modern iproute2 may insert "nhid N" before "via"; do not assume columns.
    condition = ' && '.join(terms) or '1'
    awk = (f'$1=="{prefix}" {{via=""; proto=""; '
           'for(i=2;i<NF;i++) {if($i=="via") via=$(i+1); if($i=="proto") proto=$(i+1)} '
           f'if({condition}) n++}} END {{print n+0}}')
    return f"routes=$(ip -4 route show exact {prefix}) && printf '%s\\n' \"$routes\" | awk {shlex.quote(awk)}"


def checks(case):
    rows = [(a, f'ping -n -W 1 -c 2 {address(b)}', '0% loss' if expected_ping(case, a, b) else 'loss>0') for a, b in PROBES]
    for iface in ('eth0', 'eth1', 'eth3'):
        down = (iface == 'eth0' and case in ('failover', 'isolation')) or (iface == 'eth1' and case == 'isolation') or (iface == 'eth3' and case == 'server-link')
        rows.append(('r13', f'flags=$(cat /sys/class/net/{iface}/flags) && echo $((flags & 1))', '0' if down else '1'))
    for node, data in SPEC['nodes'].items():
        if 'ospf' not in data:
            continue
        neighbors = sum(not d['passive'] for d in data['ospf'].values())
        if case in ('failover', 'isolation') and node in ('r5', 'r13'):
            neighbors -= 1
        if case == 'isolation' and node in ('r6', 'r13'):
            neighbors -= 1
        cmd = "neighbors=$(vtysh -c 'show ip ospf neighbor') && printf '%s\\n' \"$neighbors\" | awk '/Full/ {n++} END {print n+0}'"
        rows.append((node, cmd, str(neighbors)))
    via = uplink_gateway('eth1' if case == 'failover' else 'eth0')
    rows.append(('r13', route_count('10.10.2.0/24', via, 'ospf'), '0' if case == 'isolation' else '1'))
    rows.append(('r14', route_count('10.40.1.0/24', protocol='ospf'), '0' if case in ('isolation', 'advertisement', 'server-link') else '1'))
    rows.append(('r13', route_count('10.40.1.0/24'), '0' if case == 'server-link' else '1'))
    cmd = "config=$(vtysh -c 'show running-config') && printf '%s\\n' \"$config\" | awk '$1==\"network\" && $2==\"10.40.1.0/24\" {n++} END {print n+0}'"
    rows.append(('r13', cmd, '0' if case == 'advertisement' else '1'))
    rows.append(('pc1', route_count('default', '10.10.1.254' if case == 'gateway' else '10.10.1.1'), '1'))
    return rows


def rendered_files():
    files = {}
    root = f'topology_kathara/{NAME}'
    lab = ['LAB_NAME="P20Enterprise"', 'LAB_VERSION="2.0"',
           'LAB_DESCRIPTION="Four-site redundant multi-area OSPF enterprise"']
    for node, data in SPEC['nodes'].items():
        router = 'ospf' in data
        lab += [f'{node}[image]="kathara/{"frr" if router else "base"}"',
                f'{node}[sysctl]="net.ipv4.ip_forward={int(router)}"']
        startup = ['#!/bin/sh', 'set -eu', 'ip link set lo up']
        for iface, (segment, addr) in data['interfaces'].items():
            lab.append(f'{node}[{iface[3:]}]="{segment}"')
            startup += [f'ip link set {iface} up', f'ip address replace {addr} dev {iface}']
        for destination, gateway in data['routes'].items():
            startup.append(f'ip route replace {destination} via {gateway}')
        if router:
            config = [f'hostname {node}', 'password zebra', 'log file /var/log/frr/ospfd.log', '!']
            for iface, detail in data['ospf'].items():
                config += [f'interface {iface}', f' ip ospf cost {detail["cost"]}']
                if not detail['passive']:
                    config += [' ip ospf network point-to-point', ' ip ospf hello-interval 1', ' ip ospf dead-interval 4']
                config += ['!']
            config += ['router ospf', f' ospf router-id {data["router_id"]}', ' passive-interface default']
            for iface, detail in data['ospf'].items():
                network = ipaddress.ip_interface(data['interfaces'][iface][1]).network
                config.append(f' network {network} area 0.0.0.{detail["area"]}')
                if not detail['passive']:
                    config.append(f' no passive-interface {iface}')
            config += ['!', 'line vty', '!']
            files[f'{root}/{node}/etc/frr/frr.conf'] = '\n'.join(config) + '\n'
            startup += ["sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons",
                        'chown frr:frr /etc/frr/frr.conf', 'chmod 640 /etc/frr/frr.conf',
                        '/etc/init.d/frr start', "vtysh -c 'show ip ospf' >/dev/null"]
        startup += ['touch /tmp/p20-ready']
        files[f'{root}/{node}.startup'] = '\n'.join(startup) + '\n'
    files[f'{root}/lab.conf'] = '\n'.join(lab) + '\n'
    files['docs/p20-enterprise/topology.json'] = json.dumps(SPEC, indent=2) + '\n'
    table = ['# P20Enterprise v2 addressing', '', '| Device | Role | Interface | Segment | Address | OSPF area |', '|---|---|---|---|---|---|']
    for node, data in SPEC['nodes'].items():
        for iface, (segment, addr) in data['interfaces'].items():
            area = data.get('ospf', {}).get(iface, {}).get('area', '—')
            table.append(f'| {node} | {data["role"]} | {iface} | {segment} | {addr} | {area} |')
    table += ['', 'Routers learn remote LANs through OSPF; no static/default router routes mask withdrawals.',
              'Hosts use .1 in their own /24 as the default gateway. 10.10.1.254 is deliberately unassigned.',
              'The backbone is area 0. Four sites use areas 1–4. Transit networks use /30 prefixes.',
              'R13–R16 use eth0 as primary (cost 10), eth1 as backup (cost 100), eth2 for users, and eth3 for servers.']
    files['docs/p20-enterprise/addressing.md'] = '\n'.join(table) + '\n'
    for case, definition in CASES.items():
        lines = [f'Scenario: {definition["id"]}', f'Topology: {NAME}', f'Fault family: {case}',
                 '', '[PROMPT-TO-AGENT]', definition['ticket'], '', '[PRE-CHECK]']
        lines += [f'{node}  {cmd} => expect {expect}' for node, cmd, expect in checks('healthy')]
        lines += ['', '[INJECTION]', f'device: {definition["node"]}', f'action: {case}']
        if definition['inject']:
            lines += ['cmd: |'] + ['  ' + line for line in definition['inject'].splitlines()]
        lines += ['', '[POST-INJECT-CHECK]']
        lines += [f'{node}  {cmd} => expect {expect}' for node, cmd, expect in checks(case)]
        lines += ['', '[GROUND-TRUTH]', definition['truth'], '', '[FIX]',
                  f'On {definition["node"]}:\n{definition["repair"]}' if definition['repair'] else 'No repair is required.',
                  'Repeat healthy checks, including preferred routing and all OSPF adjacencies.', '', '[DIAGNOSTIC-PROCESS]',
                  'Compare local and remote paths. Inspect interface state, OSPF neighbors, advertisements and installed routes. Distinguish successful failover from an outage.',
                  '', '[SCORING-AXES]', 'must-identify-cause: ' + definition['truth'],
                  'must-scope-impact: explain affected and unaffected paths',
                  'must-verify-recovery: verify configuration and full baseline after the precise repair',
                  '', '[NIKA-LABEL]', 'nika_label: none', 'nika_category: PROJECT_REFERENCE',
                  'in_taxonomy: false', 'note: NIKA task separation is the reference; native NIKA/SADE execution is not established.']
        files[f'dataset/p20enterprise_Q/custom/{definition["id"]}.txt'] = '\n'.join(lines) + '\n'
    files['faultbench/benchmarks/p20-enterprise.csv'] = 'scenario\n' + '\n'.join(d['id'] for d in CASES.values()) + '\n'
    return files
