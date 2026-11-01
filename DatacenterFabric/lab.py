#!/usr/bin/env python3
"""Manage and validate only this directory's Kathara fabric."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
NAME = 'soft3888_datacenter_fabric_v1'


def manager():
    from Kathara.manager.Kathara import Kathara
    return Kathara.get_instance()


def parsed_lab():
    from Kathara.parser.netkit.LabParser import LabParser
    network = LabParser().parse(str(ROOT))
    network.name = NAME
    network.general_options['shared_mount'] = False
    network.general_options['hosthome_mount'] = False
    network.global_machine_metadata['num_terms'] = 0
    return network


def inventory():
    return json.loads((ROOT/'inventory.json').read_text())


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, text=True, **kwargs)


def execute(node, command, timeout=75):
    if node not in inventory()['nodes']:
        return False, 'Unknown device'
    try:
        stdout, stderr, code = manager().exec(
            node, ['timeout', str(timeout), 'bash', '-c', command],
            lab_name=NAME, stream=False)
        decode = lambda data: data.decode(errors='replace') if isinstance(data, bytes) else str(data or '')
        return code == 0, decode(stdout)+decode(stderr)
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


def python_assert(command, code):
    return command + ' | python3 -c ' + shlex.quote(code)


def ecmp_command(prefix, expected=3):
    code = ('import json,sys; rows=json.load(sys.stdin); assert rows, "missing route"; '
            'hops=rows[0].get("nexthops", []); '
            'active=[h for h in hops if "dead" not in h.get("flags", [])]; '
            f'assert len(active)=={expected}, rows; '
            f'assert len({{h["gateway"] for h in active}})=={expected}, rows; print(rows)')
    return python_assert(f'ip -j route show exact {prefix}', code)


def checks():
    nodes = inventory()['nodes']
    items = [(f'{n}: startup complete', n, 'test -f /tmp/fabric-ready') for n in nodes]
    hosts = {n:m for n,m in nodes.items() if m['role'] in ('server','client')}
    for name, node in nodes.items():
        if node['role'] in ('leaf', 'spine'):
            count = sum(p['kind'] == 'fabric' for p in node['ports'])
            code = ('import json,sys; d=json.load(sys.stdin); peers=d["ipv4Unicast"]["peers"]; '
                    f'assert len(peers)=={count}, peers; '
                    'assert all(p["state"]=="Established" and p["pfxRcd"]>0 for p in peers.values()), peers; print(peers)')
            items.append((f'{name}: all eBGP peers established and receiving routes', name, python_assert("vtysh -c 'show bgp summary json'", code)))
        if node['role'] == 'leaf':
            for rack in range(1, 7):
                if rack != node['rack']:
                    prefix = f'10.60.{rack}.0/24'
                    items.append((f'{name}: three installed ECMP paths to {prefix}', name, ecmp_command(prefix)))
        if node['role'] == 'switch':
            code = f'import json,sys; d=json.load(sys.stdin); assert len(d)=={len(node["ports"])}; assert all(i["master"]=="br0" for i in d)'
            items.append((f'{name}: {len(node["ports"])} ports on isolated rack bridge', name, python_assert('ip -j link show master br0', code)))
    for name, node in hosts.items():
        address = node['address'].split('/')[0]
        code = f'import json,sys; d=json.load(sys.stdin); assert any(a["local"]=={address!r} for i in d for a in i.get("addr_info",[]))'
        cmd = python_assert('ip -j -4 addr show dev eth0', code)
        cmd += f' && ping -n -c 1 -W 2 {node["gateway"]} >/dev/null'
        items.append((f'{name}: address and gateway', name, cmd))
        targets = ' '.join(m['address'].split('/')[0] for n,m in hosts.items() if n != name)
        cmd = f'for target in {targets}; do ping -n -c 1 -W 2 "$target" >/dev/null || {{ echo "unreachable: $target"; exit 1; }}; done'
        items.append((f'{name}: all {len(hosts)-1} other endpoints reachable', name, cmd))
        items.append((f'{name}: application and backend dependency healthy', name, "curl -fsS --max-time 6 http://10.60.5.11:8080/ | grep -F 'application: healthy'"))
    for rack in range(1, 7):
        expected = 'application: healthy' if rack == 5 else f'rack{rack}h1: healthy'
        items.append((f'rack{rack}: HTTP service reachable from rack1', 'rack1h2', f"curl -fsS --max-time 6 http://10.60.{rack}.11:8080/ | grep -F '{expected}'"))
    return items


def save_report(prefix, report):
    dest = ROOT/'results'
    dest.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path = dest/f'{prefix}-{stamp}.json'
    report['timestamp'] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(report, indent=2)+'\n')
    (dest/f'latest-{prefix}.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'Report: {path}')
    return path


def check():
    def probe(item):
        title, node, cmd = item
        ok, output = execute(node, cmd)
        return dict(check=title, node=node, passed=ok, command=cmd, output=output)
    manager()  # Initialise the SDK singleton before worker threads.
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(probe, checks()))
    for row in results:
        print(('PASS ' if row['passed'] else 'FAIL ')+row['check'], flush=True)
        if not row['passed']:
            print(row['output'][:1000])
    passed = all(r['passed'] for r in results)
    save_report('health', dict(passed=passed, checks=results, endpoint_pairs=sum(n['role'] in ('server','client') for n in inventory()['nodes'].values()) * (sum(n['role'] in ('server','client') for n in inventory()['nodes'].values())-1)))
    print(f'{sum(r["passed"] for r in results)}/{len(results)} checks passed')
    return 0 if passed else 1


def failover():
    report = dict(passed=False, injected=False, recovered=False, checks=[])
    changed = False

    def require(title, node, command):
        ok, output = execute(node, command)
        report['checks'].append(dict(check=title, node=node, passed=ok, command=command, output=output))
        if not ok:
            raise RuntimeError(f'{title}: {output}')
    try:
        if check():
            raise RuntimeError('Baseline failed; no link changed')
        changed = True  # Also restore if injection only partially succeeds.
        require('Disable leaf1 first spine uplink', 'leaf1', 'ip link set eth0 down')
        report['injected'] = True
        time.sleep(12)
        require('Uplink administratively down', 'leaf1', python_assert('ip -j link show eth0', 'import json,sys; assert "UP" not in json.load(sys.stdin)[0]["flags"]'))
        for rack in range(2, 7):
            require(f'Two remaining paths to rack{rack}', 'leaf1', ecmp_command(f'10.60.{rack}.0/24', 2))
        for title, node, cmd in checks():
            if 'other endpoints reachable' in title or 'dependency healthy' in title:
                require(title, node, cmd)
        report['passed'] = True
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if changed:
            try:
                require('Restore leaf1 first spine uplink', 'leaf1', 'ip link set eth0 up')
                time.sleep(12)
                report['recovered'] = check() == 0
            except Exception as exc:
                report['recovery_error'] = str(exc)
        report['passed'] = report['passed'] and report['recovered']
        save_report('failover', report)
    return 0 if report['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('build','start','stop','status','check','validate','failover'):
        sub.add_parser(action)
    cmd = sub.add_parser('exec')
    cmd.add_argument('node', choices=list(inventory()['nodes']))
    cmd.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'build':
        return run(['docker','build','-t',inventory()['image'],'.']).returncode
    if args.action == 'validate':
        from tools.validate import validate
        validate(ROOT)
        network = parsed_lab()
        network.check_integrity()
        print(f'Kathara parsed {len(network.machines)} devices and {len(network.links)} links')
        return 0
    if args.action == 'start':
        if manager().get_machines_api_objects(lab_name=NAME):
            raise RuntimeError('This lab already exists; use check or stop before starting again')
        manager().deploy_lab(parsed_lab())
        print('Waiting 25 seconds for BGP convergence...', flush=True)
        time.sleep(25)
        return check()
    if args.action == 'stop':
        manager().undeploy_lab(lab_name=NAME)
        return 0
    if args.action == 'status':
        machines = manager().get_machines_api_objects(lab_name=NAME)
        for container in machines:
            print(container.name, container.status)
        expected = len(inventory()['nodes'])
        print(f'{len(machines)}/{expected} containers present')
        return 0 if len(machines) == expected else 1
    if args.action == 'check':
        return check()
    if args.action == 'failover':
        return failover()
    if not args.command:
        parser.error('A command is required')
    ok, output = execute(args.node, shlex.join(args.command))
    print(output)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
