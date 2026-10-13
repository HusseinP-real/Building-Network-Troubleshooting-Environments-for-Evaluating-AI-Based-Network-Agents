#!/usr/bin/env python3
"""Scoped lifecycle, health checks, and reversible faults for this lab only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, text=True, **kwargs)

def execute(node, command, timeout=35):
    marker='__ENTERPRISE_COMMAND_OK__'
    wrapped=f'( {command} ) && printf "\\n{marker}\\n"'
    try:
        p=run(['kathara','exec','-d',str(ROOT),node,'--','bash','-c',wrapped],capture_output=True,timeout=timeout)
        output=p.stdout+p.stderr
        return p.returncode==0 and marker in output, output.replace(marker,'').strip()
    except subprocess.TimeoutExpired:
        return False, f'Command exceeded {timeout}s'

def checks():
    inventory=json.loads((ROOT/'inventory.json').read_text())
    items=[(f'{n}: startup',n,'test -f /tmp/enterprise-ready') for n in inventory['nodes']]
    for n,meta in inventory['nodes'].items():
        if meta['role']=='router':
            expected=sum(p['kind']=='routed' for p in meta['ports'])
            items.append((f'{n}: all OSPF neighbors Full',n,
                          f'test "$(vtysh -c \'show ip ospf neighbor\' | grep -c Full)" -eq {expected}'))
        if meta['role']=='switch':
            items.append((f'{n}: VLAN-aware STP bridge',n,
                          'test "$(cat /sys/class/net/br0/bridge/stp_state)" = 1 && test "$(cat /sys/class/net/br0/bridge/vlan_filtering)" = 1'))
    for n in ['staff','guest','office','engineering']:
        prefix=inventory['nodes'][n]['address'].rsplit('.',1)[0]+'.'
        items += [(f'{n}: DHCP lease',n,f'ip -4 addr show dev eth0 | grep -F {shlex.quote(prefix)}'),
                  (f'{n}: DNS answer',n,"test \"$(dig +short +time=2 +tries=1 @10.40.20.10 app.enterprise.test)\" = 10.30.10.10")]
    for n,meta in inventory['nodes'].items():
        if meta['role']=='host' and n not in ('staff','guest','office','engineering','app','database','dmz','infra','ops'):
            address=meta['address'].split('/')[0]
            items += [(f'{n}: configured address',n,f'ip -4 addr show dev eth0 | grep -F {shlex.quote(address)}'),
                      (f'{n}: VLAN gateway reachable',n,f'ping -c 1 -W 2 {shlex.quote(meta["gateway"])} >/dev/null')]
    for n in ['staff','office','engineering','ops']:
        items.append((f'{n}: application HTTP',n,'curl -fsS --max-time 5 http://app.enterprise.test/ | grep -F "app: healthy"'))
    items += [
        ('guest: DMZ allowed','guest','curl -fsS --max-time 5 http://dmz.enterprise.test/ | grep -F "dmz: healthy"'),
        ('guest: internal application denied','guest','curl -fsS --max-time 5 http://10.40.10.10/ >/dev/null && ! curl -fsS --max-time 3 http://10.30.10.10/'),
        ('office: direct database denied','office','curl -fsS --max-time 5 http://10.30.10.10/ >/dev/null && ! curl -fsS --max-time 3 http://10.30.20.10:8080/'),
        ('application: database allowed','app','curl -fsS --max-time 5 http://10.30.20.10:8080/ | grep -F "database: healthy"'),
        ('ops: database allowed','ops','curl -fsS --max-time 5 http://10.30.20.10:8080/ | grep -F "database: healthy"'),
        ('ops: all router loopbacks reachable','ops','for n in $(seq 1 10); do ping -c 1 -W 2 10.255.255.$n >/dev/null || exit 1; done'),
    ]
    for a,b,vlans in [('r3','r4',[410,420,430]),('r5','r6',[110,120]),('r7','r8',[210,220]),('r9','r10',[310,320])]:
        for node in [a,b]: items.append((f'{node}: VRRP process',node,'pgrep keepalived'))
        prefixes={110:'10.10.10',120:'10.10.20',210:'10.20.10',220:'10.20.20',310:'10.30.10',320:'10.30.20',410:'10.40.10',420:'10.40.20',430:'10.40.30'}
        expected=[prefixes[v]+'.1' for v in vlans]
        for node,primary in [(a,True),(b,False)]:
            assertion='expected <= present' if primary else 'not expected & present'
            code=f'import json,sys; expected=set({expected!r}); present={{a["local"] for i in json.load(sys.stdin) for a in i.get("addr_info",[])}}; assert {assertion}'
            items.append((f'{node}: virtual gateway ownership',node,'ip -j -4 addr | python3 -c '+shlex.quote(code)))
    for node in ['s3','s4','s7','s8','s11','s12']+[f's{i}' for i in range(16,26)]:
        items.append((f'{node}: redundant STP port blocked',node,'test "$(bridge link show | grep -c "state blocking")" -eq 1'))
    return items

def check():
    def one(item):
        title,node,cmd=item; ok,out=execute(node,cmd)
        return {'check':title,'node':node,'passed':ok,'output':out}
    with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(one,checks()))
    for r in results: print(('PASS' if r['passed'] else 'FAIL')+' '+r['check']+('' if r['passed'] else '\n'+r['output'][:600]))
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'passed':all(r['passed'] for r in results),'checks':results}
    out=ROOT/'results';out.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    (out/f'health-{stamp}.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'latest-health.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"{sum(r['passed'] for r in results)}/{len(results)} checks passed")
    return 0 if report['passed'] else 1

FAULTS={
    'core-uplink': ('r5','ip link set eth0 down','ip link set eth0 up'),
    'gateway-service': ('r5','pkill -TERM keepalived','pgrep keepalived >/dev/null || keepalived -f /etc/keepalived/keepalived.conf --log-console'),
    'database-acl': ('app','iptables -C OUTPUT -d 10.30.20.10 -p tcp --dport 8080 -j REJECT 2>/dev/null || iptables -I OUTPUT 1 -d 10.30.20.10 -p tcp --dport 8080 -j REJECT',
                     'if iptables -C OUTPUT -d 10.30.20.10 -p tcp --dport 8080 -j REJECT 2>/dev/null; then iptables -D OUTPUT -d 10.30.20.10 -p tcp --dport 8080 -j REJECT; fi'),
    'core-uplink-r6': ('r6', 'ip link set eth0 down', 'ip link set eth0 up'),
    'gateway-service-r8': ('r8', 'pkill -TERM keepalived', 'pgrep keepalived >/dev/null || keepalived -f /etc/keepalived/keepalived.conf --log-console'),
    'database-ingress-acl': ('database', 'iptables -C INPUT -s 10.30.10.10 -p tcp --dport 8080 -j REJECT 2>/dev/null || iptables -I INPUT 1 -s 10.30.10.10 -p tcp --dport 8080 -j REJECT', 'if iptables -C INPUT -s 10.30.10.10 -p tcp --dport 8080 -j REJECT 2>/dev/null; then iptables -D INPUT -s 10.30.10.10 -p tcp --dport 8080 -j REJECT; fi'),
    'ospf-passive-r7': ('r7', "vtysh -c 'configure terminal' -c 'router ospf' -c 'passive-interface eth0'", "vtysh -c 'configure terminal' -c 'router ospf' -c 'no passive-interface eth0'"),
}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    s=p.add_subparsers(dest='action',required=True)
    for action in ['build','start','stop','status','check','validate']: s.add_parser(action)
    e=s.add_parser('exec'); e.add_argument('node'); e.add_argument('command',nargs=argparse.REMAINDER)
    f=s.add_parser('fault');f.add_argument('operation',choices=['inject','repair']);f.add_argument('name',choices=FAULTS)
    a=p.parse_args()
    if a.action=='build':
        code=run(['docker','build','-f','Dockerfile','-t','enterprise-topology:base','.']).returncode
        if code: return code
        nodes=json.loads((ROOT/'inventory.json').read_text())['nodes']
        for name,meta in nodes.items():
            print(f'Building {name} image ({len(nodes)} devices total)...',flush=True)
            code=run(['docker','build','-f','Dockerfile.device','--build-arg',f'DEVICE={name}',
                      '-t',meta['image'],'.']).returncode
            if code: return code
        return 0
    if a.action=='validate': return run(['kathara','lstart','-d',str(ROOT),'--print']).returncode
    if a.action=='start':
        nodes=list(json.loads((ROOT/'inventory.json').read_text())['nodes'])
        for offset in range(0,len(nodes),10):
            batch=nodes[offset:offset+10]
            print(f'Starting devices {offset+1}-{offset+len(batch)} of {len(nodes)}: {", ".join(batch)}',flush=True)
            code=run(['kathara','lstart','-d',str(ROOT),'--noterminals','--no-hosthome','--no-shared',*batch]).returncode
            if code: return code
        print('Waiting 45 seconds for STP, OSPF, VRRP, and DHCP convergence...',flush=True)
        time.sleep(45)
        return check()
    if a.action=='stop': return run(['kathara','lclean','-d',str(ROOT)]).returncode
    if a.action=='status':
        nodes=json.loads((ROOT/'inventory.json').read_text())['nodes']
        with ThreadPoolExecutor(max_workers=4) as pool:
            states=list(pool.map(lambda n: execute(n,'test -f /tmp/enterprise-ready')[0],nodes))
        for (name,meta),ok in zip(nodes.items(),states):
            print(f'{name:12} {meta["role"]:8} {"READY" if ok else "STOPPED / NOT READY"}')
        return 0 if all(states) else 1
    if a.action=='check': return check()
    if a.action=='exec':
        if a.node not in json.loads((ROOT/'inventory.json').read_text())['nodes']: p.error('Unknown lab node')
        if not a.command: p.error('A command is required')
        ok,out=execute(a.node,shlex.join(a.command));print(out);return 0 if ok else 1
    if a.action=='fault':
        node,inject,repair=FAULTS[a.name]
        ok,out=execute(node,inject if a.operation=='inject' else repair)
        print(out or f'{a.operation}: {a.name} on {node}')
        return 0 if ok else 1

if __name__=='__main__': sys.exit(main())
