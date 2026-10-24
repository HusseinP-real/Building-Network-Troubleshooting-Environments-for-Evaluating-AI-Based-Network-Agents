#!/usr/bin/env python3
"""Campus80: the same routing_daemon_down fault family as Enterprise80 v2.
Python 3 standard library only. Docker commands always use exact container names.
"""
import argparse
import datetime as dt
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / 'manifest.json').read_text())
DEVICES = MANIFEST['devices']
ROUTERS = sorted(n for n in DEVICES if re.fullmatch(r'r\d\d', n))
TARGET = 'r01'
PREFIX = '10.10.1.0/24'

class Failure(RuntimeError):
    pass

class Lab:
    def __init__(self):
        (ROOT / 'logs').mkdir(exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.log = (ROOT / 'logs' / (stamp + '.log')).open('w')
        names = self.run(['docker', 'ps', '--format', '{{.Names}}']).splitlines()
        anchors = [n for n in names if re.fullmatch(r'kathara_.+_r01_[^_]+', n)]
        selected = os.environ.get('CAMPUS_ANCHOR')
        if selected:
            anchors = [n for n in anchors if n == selected]
        require(len(anchors) == 1, 'Need exactly one Campus r01; use CAMPUS_ANCHOR=exact_container_name if multiple copies run.')
        before, after = anchors[0].rsplit('_r01_', 1)
        self.containers = {n: before + '_' + n + '_' + after for n in DEVICES}
        missing = set(self.containers.values()) - set(names)
        require(not missing, 'Selected lab does not have all 80 running devices: ' + str(sorted(missing)))
        self.say('Selected lab: ' + anchors[0])
        # Validate the anchor's actual addresses before any mutation.
        self.addresses(TARGET)

    def say(self, message):
        line = dt.datetime.now(dt.timezone.utc).isoformat() + ' ' + message
        print(line, flush=True)
        self.log.write(line + '\n')
        self.log.flush()

    def run(self, args, accepted=(0,), timeout=35):
        try:
            p = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise Failure(str(e)) from e
        self.say('$ ' + repr(args) + '\n' + p.stdout + p.stderr + '\nexit=' + str(p.returncode))
        require(p.returncode in accepted, 'Command failed: ' + repr(args))
        return p.stdout

    def dev(self, name, *args, **kwargs):
        return self.run(['docker', 'exec', self.containers[name], *args], **kwargs)

    def process(self, name, proc, present=True):
        # The sentinel distinguishes an absent process from a Docker/exec failure.
        out = self.dev(name, 'sh', '-c',
            'command -v pgrep >/dev/null || exit 127; pgrep -x "$1" >/dev/null; rc=$?; '
            'case "$rc" in 0) echo PRESENT;; 1) echo ABSENT;; *) exit "$rc";; esac', 'sh', proc)
        require(out.strip() == ('PRESENT' if present else 'ABSENT'), name + ': unexpected process state for ' + proc)

    def addresses(self, name):
        rows = json.loads(self.dev(name, 'ip', '-j', '-4', 'addr', 'show'))
        for wanted in DEVICES[name]:
            matches = [r for r in rows if r['ifname'] == wanted['interface']]
            require(len(matches) == 1, name + ': missing ' + wanted['interface'])
            row = matches[0]
            require('UP' in row['flags'], name + ': interface is administratively down')
            addresses = {a['local'] + '/' + str(a['prefixlen']) for a in row['addr_info']}
            require(wanted['ip'] in addresses, name + ': missing ' + wanted['ip'])

    def ping(self, name, dest, reachable=True):
        out = self.dev(name, 'sh', '-c',
            'command -v ping >/dev/null || exit 127; LC_ALL=C ping -n -c 2 -W 2 "$1"; rc=$?; '
            '[ "$rc" -le 1 ] || exit "$rc"; echo PING_RC="$rc"', 'sh', dest)
        received = re.search(r'(\d+) (?:packets )?received', out)
        require(received is not None, 'Cannot parse ping output')
        require(int(received.group(1)) == (2 if reachable else 0), name + ' -> ' + dest + ': unexpected reachability')
        require(('PING_RC=0' if reachable else 'PING_RC=1') in out, 'Unexpected ping status')

    def neighbors(self, router, faulty=False):
        expected = set()
        for link in MANIFEST['links']:
            if router in (link['a'], link['b']):
                peer = link['b'] if router == link['a'] else link['a']
                if not (faulty and peer == TARGET):
                    expected.add('10.255.0.' + str(int(peer[1:])))
        out = self.dev(router, 'vtysh', '-c', 'show ip ospf neighbor')
        actual = {line.split()[0] for line in out.splitlines() if re.search(r'\bFull\b', line, re.I)}
        require(actual == expected, router + ': expected FULL peers ' + str(expected) + ', got ' + str(actual))

    def route(self, router, present):
        out = self.dev(router, 'ip', '-4', 'route', 'show', 'exact', PREFIX)
        require(bool(out.strip()) == present, router + ': unexpected route to ' + PREFIX)

    def healthy(self):
        for name in sorted(DEVICES):
            self.addresses(name)
        for router in ROUTERS:
            self.process(router, 'ospfd')
            self.process(router, 'zebra')
            require(self.dev(router, 'cat', '/proc/sys/net/ipv4/ip_forward').strip() == '1', router + ': forwarding disabled')
            self.neighbors(router)
        for name in sorted(DEVICES):
            if name not in ROUTERS:
                # Every endpoint must reach a different LAN, including all servers.
                on_lan01 = DEVICES[name][0]['domain'] == 'LAN01'
                dest = '10.10.12.24' if on_lan01 else '10.10.1.20'
                self.ping(name, dest)
        self.route('r12', True)
        self.say('PASS: healthy baseline (all 80 addresses, all router peers, all 68 endpoint probes)')

    def faulty(self):
        self.addresses(TARGET)
        self.process(TARGET, 'ospfd', False)
        self.process(TARGET, 'watchfrr', False)
        self.process(TARGET, 'zebra')
        for router in ROUTERS[1:]:
            self.process(router, 'ospfd')
            self.neighbors(router, faulty=True)
            self.route(router, False)
        for i in range(1, 6):
            name = 'pc%02d' % i
            self.ping(name, '10.10.1.1')
            self.ping(name, '10.10.3.100', False)
        self.ping('pc01', '10.10.1.21')
        self.ping('srv01', '10.10.1.20', False)
        for i in range(2, 13):
            self.ping('pc%02d' % ((i - 1) * 5 + 1), '10.10.3.100')
        self.say('PASS: expected fault, local LAN preserved, other LANs reachable')

    def wait(self, check, seconds):
        deadline = time.monotonic() + seconds
        while True:
            try:
                check()
                return
            except Failure as e:
                if time.monotonic() >= deadline:
                    raise
                self.say('Waiting for convergence: ' + str(e))
                time.sleep(5)

    def inject(self):
        self.healthy()
        self.say('INJECT: stop watchdog then ospfd on r01; leave zebra and interfaces intact')
        self.dev(TARGET, 'sh', '-c',
            'command -v pkill >/dev/null || exit 127; '
            'pkill -TERM -x watchfrr; rc=$?; [ "$rc" -le 1 ] || exit "$rc"; '
            'for i in 1 2 3 4 5; do pgrep -x watchfrr >/dev/null || break; sleep 1; done; '
            'if pgrep -x watchfrr >/dev/null; then exit 1; fi; '
            'pkill -TERM -x ospfd')
        self.wait(self.faulty, 180)

    def recover(self):
        # Campus has persistent frr.conf; restart reloads its OSPF configuration.
        self.dev(TARGET, '/etc/init.d/frr', 'restart', timeout=90)
        self.wait(self.healthy, 180)
        self.process(TARGET, 'watchfrr')
        self.say('PASS: recovery including watchdog and end-to-end connectivity')


def require(condition, message):
    if not condition:
        raise Failure(message)


def static_check():
    conf = (ROOT / 'lab.conf').read_text()
    connected = re.findall(r'^(\w+)\[(\d+)\]="([^"]+)"', conf, re.M)
    require(len(DEVICES) == 80, 'Wrong device count')
    require(set(n for n, _, _ in connected) == set(DEVICES), 'Manifest/lab device mismatch')
    domains = {}
    for name, interface, domain in connected:
        entry = next((a for a in DEVICES[name] if a['interface'] == 'eth' + interface), None)
        require(entry is not None and entry['domain'] == domain, 'Interface/domain mismatch')
        startup = (ROOT / (name + '.startup')).read_text()
        require('ip addr replace ' + entry['ip'] + ' dev eth' + interface in startup, 'Address mismatch')
        domains.setdefault(domain, []).append((name, ipaddress.ip_interface(entry['ip'])))
    for domain, members in domains.items():
        require(len({a.network for _, a in members}) == 1, 'Subnet mismatch: ' + domain)
        require(len({a.ip for _, a in members}) == len(members), 'Duplicate IP: ' + domain)
        if domain.startswith('BACK'):
            require(len(members) == 2, 'Backbone must have two endpoints')
    for name in ROUTERS:
        config = (ROOT / name / 'etc/frr/frr.conf').read_text()
        require('ospf router-id 10.255.0.' + str(int(name[1:])) + '\n' in config, 'Router ID mismatch')
        for a in DEVICES[name]:
            require('network ' + str(ipaddress.ip_interface(a['ip']).network) + ' area 0' in config, 'Missing OSPF network')
    # Removing r01 must leave the other eleven routers connected.
    seen = {'r02'}
    while True:
        old = len(seen)
        for link in MANIFEST['links']:
            a, b = link['a'], link['b']
            if TARGET not in (a, b) and (a in seen or b in seen):
                seen.update((a, b))
        if len(seen) == old:
            break
    require(len(seen) == 11, 'Fault partitions the remaining backbone')
    print('PASS: static topology/address/OSPF checks; remaining backbone connected without r01')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['static', 'healthy', 'inject', 'fault', 'recover', 'demo'])
    action = parser.parse_args().action
    static_check()
    if action == 'static':
        return
    lab = Lab()
    if action == 'demo':
        lab.healthy()
        try:
            lab.inject()
        finally:
            lab.recover()
    else:
        {'healthy': lab.healthy, 'inject': lab.inject, 'fault': lab.faulty, 'recover': lab.recover}[action]()

if __name__ == '__main__':
    try:
        main()
    except (Failure, ValueError, KeyError) as e:
        print('FAIL: ' + str(e), file=sys.stderr)
        sys.exit(1)
