"""Comparable model runs and honest detection/root-cause/cost summaries."""
from __future__ import annotations
import hashlib
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .paths import ROOT
from .scenario import load_manifest,resolve_scenario,parse_scenario
from .preflight import missing_credentials


def plan(manifest,agents,repeats=1):
    if repeats<1 or not agents or len(agents)!=len(set(agents)):raise ValueError('Positive repeats and distinct agents are required')
    refs=load_manifest(manifest)
    if not refs or len(refs)!=len(set(refs)):raise ValueError('Manifest must contain distinct nonempty references')
    cells=[]
    for ref in refs:
        sc=parse_scenario(resolve_scenario(ref))
        for repeat in range(1,repeats+1):
            for agent in agents:
                # Validate names even when no keys are present.
                missing_credentials([agent])
                cells.append(dict(scenario_id=sc.scenario_id,scenario_path=str(sc.source_path.relative_to(ROOT)),scenario_sha256=hashlib.sha256(sc.source_path.read_bytes()).hexdigest(),topology=sc.topology,agent=agent,repeat=repeat))
    return dict(kind='planned-agent-evaluation',manifest=str(manifest.resolve().relative_to(ROOT)) if manifest.resolve().is_relative_to(ROOT) else str(manifest.resolve()),manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),agents=agents,repeats=repeats,cells=cells,planned_runs=len(cells),judge_cost_included=False)


def runtime_preflight(cells):
    from .ground_truth import get_labs
    from .runtime import prepare_lab_runtime
    from .lab import check_storage_budget
    labs,errors=get_labs({c['topology'] for c in cells})
    failures=[dict(topology=name,error=message) for name,message in errors.items()]
    vlan_needed=[]
    for name in sorted({c['topology'] for c in cells}):
        if name not in labs:continue
        try:
            lab=labs[name]
            text='\n'.join(lab.fs.readtext(path) for path in lab.fs.walk.files('/') if path.endswith('.startup'))
            if re.search(r'type\s+vlan|vconfig\s+add',text):vlan_needed.append(name)
            prepare_lab_runtime(lab);check_storage_budget(lab)
        except Exception as exc:failures.append(dict(topology=name,error=f'{type(exc).__name__}: {exc}'))
    if vlan_needed:
        import docker
        from contextlib import closing
        try:
            with closing(docker.from_env()) as client:
                client.containers.run('kathara/base:latest',command=['sh','-c','ip link add preflighta type veth peer name preflightb && ip link add link preflighta name preflighta.100 type vlan id 100'],network_mode='none',cap_add=['NET_ADMIN'],remove=True)
        except Exception as exc:
            failures.append(dict(topologies=vlan_needed,error='VLAN capability preflight failed before model calls: '+str(exc)))
    return failures


def execute(manifest,agents,output,repeats=1,run=False):
    p=plan(manifest,agents,repeats)
    output.mkdir(parents=True,exist_ok=True)
    missing=missing_credentials(agents)
    status='planned' if not run else 'blocked_missing_credentials' if missing else 'running'
    p.update(status=status,missing_credentials=missing,created_at=datetime.now(timezone.utc).isoformat(),executed_runs=[])
    target=output/'plan.json';target.write_text(json.dumps(p,indent=2)+'\n')
    if not run:return p
    if missing:return p
    failures=runtime_preflight(p['cells'])
    if failures:
        p.update(status='blocked_runtime',runtime_errors=failures)
        target.write_text(json.dumps(p,indent=2)+'\n');return p
    from .orchestrator import run_one
    for cell in p['cells']:
        row=run_one(ROOT/cell['scenario_path'],cell['agent'],runs_root=output/'runs',run_group=manifest.stem)
        p['executed_runs'].append(dict(cell=cell,result=row));target.write_text(json.dumps(p,indent=2)+'\n')
        # Do not burn the rest of the budget after auth/infrastructure failure.
        if row['status'] not in ('scored','no_submission','no_output'):
            p['status']='stopped_after_failure';break
    else:p['status']='finished'
    target.write_text(json.dumps(p,indent=2)+'\n')
    return p


def aggregate(details):
    groups=defaultdict(list)
    seen=set()
    for path,detail in details:
        row=detail.get('result') or detail.get('row') or {}
        if not row:continue
        sc=detail.get('scenario',{})
        if not sc.get('scenario_id'):continue
        key=(row.get('agent'),sc['scenario_id'],row.get('run_id'),row.get('timestamp'))
        if key in seen:continue
        seen.add(key)
        groups[(sc['topology'],row['agent'])].append((path,detail,row,sc))
    summaries=[]
    for (topology,agent),runs in sorted(groups.items()):
        confusion=Counter();status=Counter();causes=[];devices=[];agent_times=[];total_times=[];costs=[];unknown_cost=0;unparsed=0
        for path,d,row,sc in runs:
            status[row.get('status','unknown')]+=1
            truth=sc.get('scenario_class')!='false-premise' and 'assert-no-anomaly' not in sc.get('scoring_axes',[])
            observed=row.get('is_anomaly')
            phase=d.get('phases',{}).get('agent',{})
            submitted=bool(row.get('submitted'))
            if submitted and isinstance(observed,bool):
                confusion['tp' if truth and observed else 'fn' if truth else 'fp' if observed else 'tn']+=1
            else:unparsed+=1
            expected={a.split(':',1)[1].strip().lower() for a in sc.get('scoring_axes',[]) if a.startswith('assert-identifies:')}
            if row.get('status')=='scored' and submitted:
                got={str(x).lower() for x in row.get('faulty_devices',[])}
                if not truth or expected:devices.append(got==(expected if truth else set()))
                axes=d.get('phases',{}).get('score',{}).get('per_axis',[])
                mechanism=[a for a in axes if a.get('kind')=='must' and re.search(r'root[- _]?cause|mechanism',a.get('axis',''),re.I)]
                if truth and mechanism:causes.append(all(a.get('score',0)>=1 for a in mechanism))
            if isinstance(phase,dict) and isinstance(phase.get('wall_seconds'),(int,float)):agent_times.append(phase['wall_seconds'])
            if isinstance(row.get('wall_seconds'),(int,float)):total_times.append(row['wall_seconds'])
            # Only a real returned agent phase establishes a reported cost.
            if isinstance(phase,dict) and phase and isinstance(row.get('cost_usd'),(int,float)):costs.append(row['cost_usd'])
            else:unknown_cost+=1
        tp,tn,fp,fn=[confusion[k] for k in ('tp','tn','fp','fn')]
        ratio=lambda n,d:n/d if d else None
        summaries.append(dict(topology=topology,agent=agent,attempted_runs=len(runs),status_counts=dict(status),classification_coverage=ratio(tp+tn+fp+fn,len(runs)),unparsed_or_unsubmitted=unparsed,tp=tp,tn=tn,fp=fp,fn=fn,accuracy=ratio(tp+tn,tp+tn+fp+fn),precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),false_positive_rate=ratio(fp,fp+tn),device_exact_accuracy=ratio(sum(devices),len(devices)),device_graded_runs=len(devices),root_cause_accuracy=ratio(sum(causes),len(causes)),root_cause_graded_runs=len(causes),mean_agent_seconds=statistics.mean(agent_times) if agent_times else None,agent_timed_runs=len(agent_times),mean_lifecycle_seconds=statistics.mean(total_times) if total_times else None,agent_reported_cost_usd=sum(costs) if costs else None,runs_without_cost=unknown_cost,judge_cost_usd=None,judge_cost_note='Judge billing is not supplied by the existing scorer; do not treat agent cost as full evaluation cost.'))
    return summaries


def summarize(runs_root,output):
    details=[];errors=[]
    for p in sorted(runs_root.rglob('result.json')) if runs_root.exists() else []:
        try:details.append((str(p),json.loads(p.read_text())))
        except (OSError,ValueError) as e:errors.append(dict(path=str(p),error=str(e)))
    rows=aggregate(details)
    result=dict(kind='agent-comparison-from-actual-runs',status='available' if rows else 'not_run',source_root=str(runs_root),summary=rows,invalid_files=errors,definitions=dict(detection='Confusion counts use submitted boolean diagnoses only; missing outputs and infrastructure failures reduce classification coverage and are reported separately.',root_cause='Fraction of graded positive runs satisfying all must root-cause/mechanism axes; not an invented free-text match or overall outcome score.',device='Exact deterministic device set, where source truth defines it.',latency='Agent phase is timed separately from deployment/judging/cleanup; older runs without phase timing remain null.',cost='Returned agent cost only; judge billing unavailable. No model runs means null metrics.'))
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    return result
