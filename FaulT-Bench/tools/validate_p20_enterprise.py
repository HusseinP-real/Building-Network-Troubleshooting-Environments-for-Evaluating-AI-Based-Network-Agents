#!/usr/bin/env python3
"""Run the new P20Enterprise topology and fault suite without LLM/API calls."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from validate_haosenpeng_fault import Lab, ROOT, evaluate
from validate_client_demo import converge, topology_inventory
from faultbench.scenario import parse_scenario, resolve_scenario, load_manifest

NAME='P20Enterprise'
TOPOLOGY=ROOT/'topology_kathara'/NAME
SPEC_PATH=ROOT/'docs/p20-enterprise/topology.json'
MANIFEST=ROOT/'faultbench/benchmarks/p20-enterprise.csv'
IDS={
 'healthy':'p20-enterprise-false-premise-server-unreachable',
 'server-link':'p20-enterprise-r2-server-interface-down',
 'return-route':'p20-enterprise-r3-hq-return-route-missing',
 'gateway':'p20-enterprise-pc1-wrong-gateway',
}
REPAIRS={
 'server-link':('r2','ip link set eth2 up'),
 'return-route':('r3','ip route replace 10.10.10.0/24 via 10.255.23.1'),
 'gateway':('pc1','ip route replace default via 10.10.10.1'),
}
PROBES=[
 ('pc1','10.10.10.12'), # same LAN
 ('pc1','10.20.20.11'), # HQ to branch across 3 routers
 ('pc1','10.30.30.10'), # HQ to server A
 ('pc1','10.40.40.10'), # HQ to server B across 3 routers
 ('pc3','10.30.30.10'), # branch to server A
 ('pc3','10.40.40.10'), # branch to server B
 ('pc3','10.20.20.12'), # same branch LAN
 ('server1','10.40.40.10'), # between server networks
]
FAILURES={
 'healthy':set(),
 'server-link':{('pc1','10.30.30.10'),('pc3','10.30.30.10'),('server1','10.40.40.10')},
 'return-route':{('pc1','10.20.20.11'),('pc1','10.40.40.10')},
 'gateway':{('pc1','10.20.20.11'),('pc1','10.30.30.10'),('pc1','10.40.40.10')},
}

def checks(case):
    result=[(node,f'ping -n -W 1 -c 2 {target}','loss>0' if (node,target) in FAILURES[case] else '0% loss') for node,target in PROBES]
    result += [('r2','flags=$(cat /sys/class/net/eth2/flags) && echo $((flags & 1))','0' if case=='server-link' else '1')]
    result += [('r3',"routes=$(ip -4 route show exact 10.10.10.0/24) && printf '%s\\n' \"$routes\" | awk '$1==\"10.10.10.0/24\" && $2==\"via\" && $3==\"10.255.23.1\" {n++} END {print n+0}'",'0' if case=='return-route' else '1')]
    gateway='10.10.10.254' if case=='gateway' else '10.10.10.1'
    result += [('pc1',f"routes=$(ip -4 route show default) && printf '%s\\n' \"$routes\" | awk '$1==\"default\" && $2==\"via\" && $3==\"{gateway}\" {{n++}} END {{print n+0}}'",'1')]
    return result

def specs():
    spec=json.loads(SPEC_PATH.read_text())
    inventory=topology_inventory(TOPOLOGY)
    if set(spec['nodes'])!=set(inventory['devices']): raise ValueError('Topology devices differ from specification')
    if load_manifest(MANIFEST)!=list(IDS.values()): raise ValueError('Manifest mismatch')
    scenarios={}
    for case,sid in IDS.items():
        scenario=parse_scenario(resolve_scenario(sid))
        if scenario.topology!=NAME: raise ValueError('Scenario topology does not match folder')
        if not scenario.ground_truth or not scenario.prompt_to_agent or not scenario.scoring_axes: raise ValueError('Incomplete scenario')
        actual=[(c.device,c.command,c.expect) for c in scenario.post_inject_check]
        if actual!=checks(case): raise ValueError(f'Case checks drifted: {case}')
        if [(c.device,c.command,c.expect) for c in scenario.pre_check]!=checks('healthy'): raise ValueError('Missing healthy prechecks')
        if case=='healthy':
            if scenario.injection.command or scenario.scenario_class!='false-premise': raise ValueError('Invalid healthy control')
        else:
            if scenario.injection.device!=REPAIRS[case][0] or not scenario.injection.command: raise ValueError('Invalid injection')
            subprocess.run(['sh','-n'],input=scenario.injection.command,text=True,check=True)
        for node,cmd,expect in actual:
            if node not in spec['nodes']: raise ValueError('Check references unknown device')
            evaluate(expect,255,'')
        scenarios[case]=scenario
    for path in TOPOLOGY.glob('*.startup'):subprocess.run(['sh','-n',str(path)],check=True)
    return spec,scenarios

def mutate(lab,node,command):
    rc,out=lab.exec(node,command)
    if rc: raise RuntimeError(f'{node}: configuration change failed: {command}\n{out}')

def snapshot(lab,report,name):
    rows=[]
    for node in json.loads(SPEC_PATH.read_text())['nodes']:
        for cmd in ('ip -j address show','ip -j route show'):
            rc,out=lab.exec(node,cmd)
            rows.append({'device':node,'command':cmd,'rc':rc,'output':out})
            if rc: raise RuntimeError(f'Cannot snapshot {node}')
    report.setdefault('snapshots',[]).append({'name':name,'commands':rows})

def verify_config(lab,spec,report):
    for node,data in spec['nodes'].items():
        rc,out=lab.exec(node,'test -f /tmp/p20-ready && ip -j address show')
        if rc:
            log_rc,log=lab.exec(node,'cat /var/log/startup.log')
            report.setdefault('startup_errors',[]).append({'device':node,'rc':rc,'output':out,'log_rc':log_rc,'log':log})
            raise RuntimeError(f'{node} startup did not finish: {log[-2000:]}')
        addresses={a['ifname']:{f"{v['local']}/{v['prefixlen']}" for v in a.get('addr_info',[]) if v['family']=='inet'} for a in json.loads(out)}
        for iface,(_,addr) in data['interfaces'].items():
            if addr not in addresses.get(iface,set()): raise RuntimeError(f'{node} missing {addr} on {iface}')
        rc,out=lab.exec(node,'ip -j route show')
        if rc:raise RuntimeError(f'Cannot read routes on {node}')
        routes=json.loads(out)
        for dest,gateway in data['routes'].items():
            if not any(r.get('dst')==dest and r.get('gateway')==gateway for r in routes): raise RuntimeError(f'{node} missing route {dest} via {gateway}')
        rc,out=lab.exec(node,'cat /proc/sys/net/ipv4/ip_forward')
        if rc or out.strip()!=('1' if node.startswith('r') else '0'):raise RuntimeError(f'{node} forwarding setting is wrong')
        report.setdefault('configuration_checks',[]).append({'device':node,'passed':True})

def cycle(lab,report,case,scenario,timeout):
    converge(lab,report,'baseline-before-'+case,checks('healthy'),timeout)
    try:
        if scenario.injection.command:mutate(lab,scenario.injection.device,scenario.injection.command)
        converge(lab,report,case,checks(case),timeout)
        snapshot(lab,report,case)
        if scenario.injection.command:
            mutate(lab,scenario.injection.device,scenario.injection.command)
            converge(lab,report,case+'-repeat-injection',checks(case),timeout)
    finally:
        if case in REPAIRS:mutate(lab,*REPAIRS[case])
    converge(lab,report,'recovered-after-'+case,checks('healthy'),timeout)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-only',action='store_true')
    p.add_argument('--case',choices=['all',*IDS],default='all')
    p.add_argument('--repeat',type=int,default=1)
    p.add_argument('--converge-timeout',type=int,default=90)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.repeat<1 or a.converge_timeout<1:p.error('repeat and timeout must be positive')
    spec,scenarios=specs()
    if a.check_only:
        print('PASS: P20Enterprise 9 devices, 6 subnets, 4 scenarios and shell syntax; live tests NOT RUN')
        return 0
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=a.output or ROOT/'faultbench/runs/p20-enterprise'/f'{stamp}.json'
    report={'kind':'p20-enterprise-live-network-no-llm','started_at':stamp,'passed':False,'stages':[],
      'topology':NAME,'repeat':a.repeat,'case':a.case,
      'scenario_sha256':{s.scenario_id:hashlib.sha256(s.source_path.read_bytes()).hexdigest() for s in scenarios.values()},
      'topology_sha256':{str(f.relative_to(TOPOLOGY)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(TOPOLOGY.rglob('*')) if f.is_file()}}
    temporary=None
    try:
        for binary in ('kathara','docker'):
            if not shutil.which(binary):raise RuntimeError(f'{binary} is not on PATH')
        for cmd in (['docker','info','--format','{{.ServerVersion}}'],['kathara','--version']):
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=30,check=True)
            report[cmd[0]+'_version']=result.stdout.strip()
        result=subprocess.run(['docker','image','inspect','kathara/base','--format','{{json .RepoDigests}}'],capture_output=True,text=True,timeout=30,check=True)
        report['image_digests']=result.stdout.strip()
        temporary=Path(tempfile.mkdtemp(prefix='p20-enterprise-'))/NAME
        shutil.copytree(TOPOLOGY,temporary)
        report['temporary_lab']=str(temporary)
        result=subprocess.run(['kathara','lstart','-d',str(temporary),'--noterminals','-H','-S'],capture_output=True,text=True,timeout=300)
        report['deployment']={'rc':result.returncode,'output':result.stdout+result.stderr}
        if result.returncode:raise RuntimeError('Deployment failed: '+report['deployment']['output'])
        lab=Lab(temporary)
        # exec --wait in the shared Lab class waits for startup before executing.
        verify_config(lab,spec,report)
        converge(lab,report,'initial-baseline',checks('healthy'),a.converge_timeout)
        snapshot(lab,report,'initial-baseline')
        for iteration in range(1,a.repeat+1):
            for case in (IDS if a.case=='all' else [a.case]):
                start=len(report['stages'])
                try:cycle(lab,report,case,scenarios[case],a.converge_timeout)
                finally:
                    for stage in report['stages'][start:]:stage.update(iteration=iteration,scenario_id=IDS[case])
        verify_config(lab,spec,report);snapshot(lab,report,'final-recovery');report['passed']=True
    except (Exception,KeyboardInterrupt) as exc:
        report['error']=f'{type(exc).__name__}: {exc}';print(report['error'],flush=True)
    finally:
        if temporary is not None:
            try:
                result=subprocess.run(['kathara','lclean','-d',str(temporary)],capture_output=True,text=True,timeout=180)
                report['cleanup']={'rc':result.returncode,'output':result.stdout+result.stderr}
                if result.returncode:report['passed']=False
            except Exception as exc:report['cleanup']={'error':str(exc)};report['passed']=False
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n');print(f'Report: {output}')
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
