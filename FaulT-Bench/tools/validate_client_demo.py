#!/usr/bin/env python3
"""Validate the project's Kath3 client demo in a unique temporary lab; no LLM calls."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone

from validate_haosenpeng_fault import (
    Lab, ROOT, TOPOLOGY, RULE, FIX_ROUTE, evaluate, run_stage, state_checks,
)
from faultbench.scenario import load_manifest, parse_scenario, resolve_scenario

MANIFEST=ROOT/'faultbench/benchmarks/client-demo.csv'
IDS={
 'healthy':'kath3-client-demo-false-premise-connectivity',
 'gateway':'kath3-client-demo-wrong-gateway',
 'filter':'kath3-client-demo-icmp-filter',
 'compound':'kath3-laptop0-wrong-gateway-and-icmp-drop',
}

def topology_inventory(path=TOPOLOGY):
    domains={}; nodes={}
    for node,number,domain in re.findall(r'^([a-zA-Z0-9_]+)\[(\d+)\]\s*=\s*"?([^"\s#]+)',(path/'lab.conf').read_text(),re.M):
        domains.setdefault(domain,[]).append(f'{node}:eth{number}')
        nodes.setdefault(node,{})[f'eth{number}']=domain
    connected={d:e for d,e in domains.items() if len(e)>1}
    return {'device_count':len(nodes),'devices':nodes,'connected_segments':connected,
            'unconnected_port_count':sum(len(v)==1 for v in domains.values())}

def specs():
    refs=load_manifest(MANIFEST)
    if set(refs)!=set(IDS.values()) or len(refs)!=len(IDS):
        raise ValueError('client-demo.csv must contain each expected scenario exactly once')
    nodes=topology_inventory()['devices']; result={}
    for case,sid in IDS.items():
        sc=parse_scenario(resolve_scenario(sid))
        if sc.topology!='Kath3' or not sc.prompt_to_agent or not sc.ground_truth or not sc.scoring_axes:
            raise ValueError(f'Incomplete scenario {sid}')
        if not sc.post_inject_check: raise ValueError(f'No checks: {sid}')
        if case=='healthy':
            if sc.injection.command or sc.scenario_class!='false-premise':
                raise ValueError('Healthy control must not inject a fault')
        elif sc.injection.device!='laptop0' or not sc.injection.command or not sc.fix_spec:
            raise ValueError(f'Missing injection or fix: {sid}')
        if sc.injection.command:
            subprocess.run(['sh','-n'],input=sc.injection.command,text=True,check=True)
        for check in sc.pre_check+sc.post_inject_check:
            if check.device not in nodes: raise ValueError(f'Unknown device {check.device}')
            evaluate(check.expect,255,'')  # rejects unsupported expectations
        result[case]=sc
    return result

def checks(case):
    return state_checks('172.16.20.99' if case in ('gateway','compound') else '172.16.20.1',
                        case in ('filter','compound'),case not in ('gateway','compound'),case=='healthy')

def converge(lab,report,label,rows,timeout=240):
    deadline=time.monotonic()+timeout; consecutive=0
    while True:
        passed=run_stage(lab,report,label,rows,required=False)
        consecutive=consecutive+1 if passed else 0
        if consecutive==2: return
        if time.monotonic()>=deadline: raise RuntimeError(f'{label} failed to stabilise')
        time.sleep(2)

def restore(lab):
    errors=[]
    # Do not flush other rules, and attempt both repairs even if one fails.
    for command in (FIX_ROUTE,f'while iptables -C {RULE} 2>/dev/null; do iptables -D {RULE} || exit 1; done'):
        try: lab.mutate(command)
        except Exception as exc: errors.append(str(exc))
    if errors: raise RuntimeError('Restore failed: '+'; '.join(errors))

def snapshot(lab,report,label):
    rows=[]
    for node in ('laptop0','pc4','router0','router1','router2'):
        commands=['ip address show','ip route show']
        if node.startswith('router'): commands+=['vtysh -c "show ip rip"']
        if node=='laptop0': commands+=['iptables -S OUTPUT','iptables -L OUTPUT -n -v -x']
        for command in commands:
            rc,output=lab.exec(node,command)
            rows.append({'device':node,'command':command,'rc':rc,'output':output})
            if rc: raise RuntimeError(f'Snapshot failed: {node} {command}')
    report.setdefault('snapshots',[]).append({'name':label,'commands':rows})

def cycle(lab,report,case,sc,timeout):
    converge(lab,report,'baseline-before-'+case,checks('healthy'),timeout)
    try:
        if sc.injection.command: lab.mutate(sc.injection.command)
        converge(lab,report,case,[(c.device,c.command,c.expect) for c in sc.post_inject_check],timeout)
        snapshot(lab,report,case)
        if case!='healthy':
            lab.mutate(sc.injection.command)
            converge(lab,report,case+'-repeat-injection',checks(case),timeout)
        if case=='compound':
            lab.mutate(FIX_ROUTE)
            converge(lab,report,'gateway-repaired-filter-remains',checks('filter'),timeout)
            rc,counters=lab.exec('laptop0','iptables -L OUTPUT -n -v -x')
            tagged=[line for line in counters.splitlines() if 'haosenpeng-compound-icmp' in line]
            report.setdefault('filter_counter_evidence',[]).append({'rc':rc,'output':counters})
            if rc or len(tagged)!=1 or int(tagged[0].split()[0])<1:
                raise RuntimeError('Tagged filter did not record dropped packets after gateway repair')
            snapshot(lab,report,'gateway-repaired-filter-remains')
    finally:
        restore(lab)
    converge(lab,report,'recovered-after-'+case,checks('healthy'),timeout)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--case',choices=['all',*IDS],default='all')
    parser.add_argument('--repeat',type=int,default=1)
    parser.add_argument('--converge-timeout',type=int,default=240)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.repeat<1 or args.converge_timeout<1: parser.error('repeat and timeout must be positive')
    scenarios=specs();inventory=topology_inventory()
    if args.check_only:
        print(f'PASS: {len(scenarios)} native scenarios, {inventory["device_count"]} topology devices; no live tests run')
        return 0
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=args.output or ROOT/'faultbench/runs/client-demo'/f'{stamp}.json'
    report={'kind':'client-demo-live-network-without-llm','started_at':stamp,'passed':False,
            'stages':[],'inventory':inventory,'repeat':args.repeat,'case':args.case,
            'scenario_sha256':{s.scenario_id:hashlib.sha256(s.source_path.read_bytes()).hexdigest() for s in scenarios.values()},
            'topology_sha256':{str(p.relative_to(TOPOLOGY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(TOPOLOGY.rglob('*')) if p.is_file() and p.name!='.DS_Store'}}
    lab_path=None
    try:
        for binary in ('kathara','docker'):
            if not shutil.which(binary): raise RuntimeError(f'{binary} is not on PATH')
        for cmd in (['docker','info','--format','{{.ServerVersion}}'],['kathara','--version']):
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=30,check=True)
            report[cmd[0]+'_version']=proc.stdout.strip()
        for image in ('kathara/frr','kathara/base'):
            proc=subprocess.run(['docker','image','inspect',image,'--format','{{json .RepoDigests}}'],capture_output=True,text=True,timeout=30)
            report.setdefault('image_digests',{})[image]={'rc':proc.returncode,'output':proc.stdout,'stderr':proc.stderr}
        lab_path=Path(tempfile.mkdtemp(prefix='p20-client-demo-'))/'Kath3'
        shutil.copytree(TOPOLOGY,lab_path,ignore=shutil.ignore_patterns('shared','.DS_Store'))
        report['temporary_lab']=str(lab_path)
        proc=subprocess.run(['kathara','lstart','-d',str(lab_path),'--noterminals','-H','-S'],capture_output=True,text=True,timeout=300)
        report['deploy']={'rc':proc.returncode,'output':proc.stdout+proc.stderr}
        if proc.returncode: raise RuntimeError('Deployment failed: '+report['deploy']['output'])
        lab=Lab(lab_path)
        # Device count comes from source, while these commands verify each deployed node is accessible.
        for node in inventory['devices']:
            rc,out=lab.exec(node,'command -v ip >/dev/null && ip link show lo')
            report.setdefault('devices',[]).append({'device':node,'rc':rc,'output':out})
            if rc: raise RuntimeError(f'Device {node} unavailable')
        cases=list(IDS) if args.case=='all' else [args.case]
        for iteration in range(1,args.repeat+1):
            report['current_iteration']=iteration
            for case in cases:
                report['current_case']=case
                stage_start=len(report['stages'])
                try:
                    cycle(lab,report,case,scenarios[case],args.converge_timeout)
                finally:
                    for stage in report['stages'][stage_start:]:
                        stage['iteration']=iteration
                        stage['scenario_id']=scenarios[case].scenario_id
        report['passed']=True
    except (Exception,KeyboardInterrupt) as exc:
        report['error']=f'{type(exc).__name__}: {exc}'; print(report['error'],flush=True)
    finally:
        if lab_path is not None:
            try:
                proc=subprocess.run(['kathara','lclean','-d',str(lab_path)],capture_output=True,text=True,timeout=180)
                report['cleanup']={'rc':proc.returncode,'output':proc.stdout+proc.stderr}
                if proc.returncode: report['passed']=False
            except Exception as exc:
                report['cleanup']={'error':str(exc)};report['passed']=False
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,indent=2)+'\n')
        print(f'Report: {output}')
    return 0 if report['passed'] else 1

if __name__=='__main__': raise SystemExit(main())
