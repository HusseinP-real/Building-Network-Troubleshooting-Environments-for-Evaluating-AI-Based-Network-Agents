"""Export source-backed ground truth and audit every repository topology.

Catalogs are evaluator artifacts. Never include them in agent input/context.
Existing scenario prose is preserved verbatim; absence of live evidence is
explicit, not filled with invented diagnoses or pass results.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from .paths import ROOT,KATH_BASE,DATASET,SADE_REPO
from .scenario import parse_scenario

EXCLUDED={'Clos_Jiayuan_41Devices'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files(root):
    return {str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file() and p.suffix!='.md' and '__pycache__' not in p.parts and 'shared' not in p.parts}

def get_labs(names, include_all_directories=False):
    from Kathara.parser.netkit.LabParser import LabParser
    labs={};errors={}
    for p in sorted(KATH_BASE.glob('*/lab.conf')):
        if p.parent.name in EXCLUDED or (not include_all_directories and p.parent.name not in names):continue
        try:labs[p.parent.name]=LabParser().parse(str(p.parent))
        except Exception as e:errors[p.parent.name]=f'{type(e).__name__}: {e}'
    os.environ.setdefault('BASE_DIR',str(SADE_REPO))
    from nika.net_env.net_env_pool import get_net_env_instance
    for name in sorted(set(names)-set(labs)-EXCLUDED):
        try:labs[name]=get_net_env_instance(name).lab
        except Exception as e:errors[name]=f'{type(e).__name__}: {e}'
    return labs,errors

def infer_roles(lab):
    roles=dict(routers=[],switches=[],hosts=[],servers={})
    for name,machine in lab.machines.items():
        image=machine.get_image()
        if 'frr' in image or image.startswith('kathara/dhcp'):
            roles['routers'].append(name)
        elif name.startswith(('switch','sw')):roles['switches'].append(name)
        else:
            category=next((kind for prefix,kind in [('dns','dns'),('dhcp','dhcp'),('web','web'),('lb','load_balancer'),('db','database'),('file','file'),('srv','service')] if name.startswith(prefix)),None)
            if category:roles['servers'].setdefault(category,[]).append(name)
            else:roles['hosts'].append(name)
    return roles

def evidence_index():
    found=defaultdict(list)
    for p in sorted((ROOT/'docs/validation/soft3888').glob('*.json')):
        try:r=json.loads(p.read_text())
        except (ValueError,OSError):continue
        if not isinstance(r,dict):continue
        if r.get('kind')!='live-network-validation-without-llm' or r.get('topology') in EXCLUDED:continue
        if not(r.get('passed') and r.get('finished_at') and r.get('cleanup',{}).get('passed')):continue
        topo=KATH_BASE/r.get('topology','')
        saved=r.get('source_sha256',{})
        current=bool(saved) and saved==source_files(topo)
        ids=r.get('validated_scenarios',[])
        if not ids:
            passed={stage['name'] for stage in r.get('stages',[]) if stage['passed']}
            ids=[sid for sid in r.get('scenario_sha256',{}) if all(sid+':'+suffix in passed for suffix in ['fault','repeated-injection','recovered','whole-baseline-restored'])]
        for sid in ids:
            found[sid].append(dict(path=str(p.relative_to(ROOT)),sha256=digest(p),scenario_sha256=r.get('scenario_sha256',{}).get(sid),topology_matches=current,scope=r.get('validation_scope','full-scenarios')))
    return found

def build(topologies=None):
    scenarios=[];parse_errors=[]
    paths=sorted(DATASET.glob('*_Q/**/*.txt'))+[p for p in sorted(KATH_BASE.glob('**/*.txt')) if not any(x in EXCLUDED for x in p.parts) and any(line.startswith('Scenario:') for line in p.read_text(errors='replace').splitlines()[:40])]
    for p in paths:
        if 'jiayuan_clos_Q' in p.parts:continue
        if topologies:
            header=re.search(r'^Topology:\s*(\S+)\s*$',p.read_text(encoding='utf-8',errors='replace'),re.M)
            if header is None or header.group(1) not in topologies:continue
        try:
            scenario=parse_scenario(p)
            if not topologies or scenario.topology in topologies:scenarios.append(scenario)
        except Exception as e:parse_errors.append(dict(path=str(p.relative_to(ROOT)),error=str(e)))
    labs,lab_errors=get_labs({s.topology for s in scenarios}, include_all_directories=not bool(topologies))
    evidence=evidence_index();counts=Counter(s.scenario_id for s in scenarios)
    archived=Counter()
    manifest=ROOT/'final_results/MANIFEST.csv'
    if manifest.exists():
        with manifest.open(newline='',encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):archived[r.get('scenario_id','')]+=1
    records=[]
    for s in scenarios:
        issues=[];gaps=[];lab=labs.get(s.topology)
        checks=s.pre_check+s.post_inject_check+s.recovery_check
        unknown=sorted({c.device for c in checks if lab is not None and c.device not in lab.machines})
        for phase,op in [('injection',s.injection),('trigger',s.trigger),('recovery',s.recovery)]:
            if op and op.command and lab is not None and op.device not in lab.machines:issues.append(f'{phase} targets missing device {op.device}')
        if unknown:issues.append('checks target missing devices: '+', '.join(unknown))
        if not s.ground_truth:issues.append('missing ground truth')
        if not s.prompt_to_agent:issues.append('missing user scenario')
        if not s.scoring_axes:issues.append('missing scoring axes')
        if not lab:issues.append('topology not constructible')
        if counts[s.scenario_id]!=1:issues.append('duplicate scenario ID')
        negative=s.scenario_class=='false-premise' or 'assert-no-anomaly' in s.scoring_axes
        if negative and s.injection.command:issues.append('negative control mutates the lab')
        if negative and not s.post_inject_check:gaps.append('no executable no-fault service checks')
        if not s.pre_check:gaps.append('no explicit healthy baseline checks')
        if not negative and (not s.recovery or not s.recovery.command or not s.recovery_check):gaps.append('no machine-readable validated recovery contract')
        from .checks import _evaluate_expectation
        unsupported=sorted({c.expect for c in checks if _evaluate_expectation(c.expect,0,'',command=c.command)[1].startswith('unsupported expectation:')})
        if not negative and s.injection.command and 'eigrp' in s.injection.command.lower():
            if 'no network' in s.injection.command and any(c.expect.lower().startswith('loss') for c in checks):gaps.append('EIGRP hot network withdrawal needs a live check against the pinned FRR; related retained runtime experiments observed stale routes')
        if unsupported:gaps.append('unsupported check expectations: '+repr(unsupported))
        if not negative and not s.fix_spec:issues.append('positive case missing fix')
        if s.injection.command and not s.post_inject_check:issues.append('no fault-state checks')
        path=s.source_path
        proofs=[e for e in evidence[s.scenario_id] if e['scenario_sha256']==digest(path) and e['topology_matches']]
        records.append(dict(scenario_id=s.scenario_id,topology=s.topology,source_path=str(path.relative_to(ROOT)),source_sha256=digest(path),ticket_style=s.ticket_style,scenario_class=s.scenario_class,expected_anomaly=not negative,label_basis='existing false-premise class / deterministic no-anomaly axis; otherwise existing positive-fault class',fault_type=s.fault_family,fault_location=[] if negative else [s.injection.device] if s.injection.device and s.injection.device not in ('none','all','-') else [],expected_devices=sorted({a.split(':',1)[1].strip() for a in s.scoring_axes if a.startswith('assert-identifies:')}),root_cause_and_reference=s.ground_truth,user_scenario=s.prompt_to_agent,injection=asdict(s.injection),expected_symptoms=[asdict(c) for c in s.post_inject_check],baseline_checks=[asdict(c) for c in s.pre_check],fix=s.fix_spec,recovery=asdict(s.recovery) if s.recovery else None,recovery_checks=[asdict(c) for c in s.recovery_check],trigger=asdict(s.trigger) if s.trigger else None,scoring_axes=s.scoring_axes,live_validation_status='validated-current-configuration' if proofs else 'not-validated-on-current-runtime',live_evidence=proofs,archived_agent_runs=archived[s.scenario_id],issues=issues,validation_gaps=gaps))
    topology_records=[]
    for name,lab in sorted(labs.items()):
        related=[r for r in records if r['topology']==name]
        roles_path=KATH_BASE/name/'roles.json'
        roles=json.loads(roles_path.read_text()) if roles_path.exists() else infer_roles(lab)
        declared=roles.get('routers',[])+roles.get('switches',[])+roles.get('hosts',[])+[n for group in roles.get('servers',{}).values() for n in group]
        role_ok=len(declared)==len(set(declared)) and set(declared)==set(lab.machines)
        topology_records.append(dict(topology=name,requires_vlan=any(re.search(r'type\s+vlan|vconfig\s+add',lab.fs.readtext(path)) for path in lab.fs.walk.files('/') if path.endswith('.startup')),source_kind='directory' if (KATH_BASE/name/'lab.conf').exists() else 'nika-constructor',devices=len(lab.machines),collision_domains=len(lab.links),images=sorted({m.get_image() for m in lab.machines.values()}),roles=roles,source_path=str((KATH_BASE/name/'lab.conf').relative_to(ROOT)) if (KATH_BASE/name/'lab.conf').exists() else 'SADE-NetworkAgent/src/nika/net_env/net_env_pool.py:'+name,baseline_definition='explicit benchmark.json' if (KATH_BASE/name/'benchmark.json').exists() else 'configuration source only; no validated functional baseline in this pass',source_configuration_sha256=source_files(KATH_BASE/name) if (KATH_BASE/name).exists() else {str(p):hashlib.sha256(lab.fs.readbytes(p)).hexdigest() for p in lab.fs.walk.files('/')},inventory_complete=role_ok,scenarios=len(related),negative_controls=sum(not r['expected_anomaly'] for r in related),scenarios_with_issues=sum(bool(r['issues']) for r in related),scenarios_with_validation_gaps=sum(bool(r['validation_gaps']) for r in related),live_validated_scenarios=sum(bool(r['live_evidence']) for r in related),model_evaluation_status='not-run-in-this-development-pass',gaps=[] if related else ['No scenario points to this lab; assign cases or explicitly classify it as a historical variant.']))
    return dict(records=records,topologies=topology_records,parse_errors=parse_errors,topology_errors=lab_errors)

def export(output=None, topologies=None):
    output=output or ROOT/'ground_truth';output.mkdir(parents=True,exist_ok=True)
    data=build(topologies)
    (output/'scenarios.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data['records']),encoding='utf-8')
    (output/'topologies.json').write_text(json.dumps(data['topologies'],indent=2)+'\n',encoding='utf-8')
    (output/'audit.json').write_text(json.dumps(dict(scenarios=len(data['records']),topologies=len(data['topologies']),live_validated_scenarios=sum(bool(r['live_evidence']) for r in data['records']),records_with_issues=sum(bool(r['issues']) for r in data['records']),records_with_validation_gaps=sum(bool(r['validation_gaps']) for r in data['records']),parse_errors=data['parse_errors'],topology_errors=data['topology_errors'],issues=[dict(scenario_id=r['scenario_id'],issues=r['issues']) for r in data['records'] if r['issues']]),indent=2)+'\n',encoding='utf-8')
    rows=['# Topology and ground-truth audit','', 'Static construction, inventory coverage, source truth and current live evidence are separate. Historical model runs are not new model evaluations. The excluded 41-device prototype is not part of this catalog.', '', '| Topology | Devices / domains | Cases / no-fault | Inventory | Current live cases | Records with validation gaps |','|---|---|---|---|---|---|']
    for t in data['topologies']:rows.append(f"| {t['topology']} | {t['devices']} / {t['collision_domains']} | {t['scenarios']} / {t['negative_controls']} | {'complete' if t['inventory_complete'] else 'INCOMPLETE'} | {t['live_validated_scenarios']} | {t['scenarios_with_validation_gaps']} |")
    rows+=['','See scenarios.jsonl for unchanged source Ground Truth, injection, symptoms, fix, recovery, hashes and actual evidence links; audit.json lists schema/device gaps. An empty recovery field in a legacy case is an unresolved recovery specification, not an executed repair.','', 'These evaluator records must never be supplied to the agents. Source scenarios remain authoritative; regenerate after changes.','']
    (output/'README.md').write_text('\n'.join(rows),encoding='utf-8')
    return data
