#!/usr/bin/env python3
"""Index actual integration reports separately from source truth/fault validation."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def main():
    latest={};attempts=[]
    for p in sorted((ROOT/'docs/validation/team-integration').glob('*.json')):
        r=json.loads(p.read_text())
        if not isinstance(r,dict) or r.get('kind')!='team-live-integration-smoke-without-llm':continue
        r['evidence_path']=str(p.relative_to(ROOT));attempts.append(r)
        if r.get('finished_at','')>latest.get(r['topology'],{}).get('finished_at',''):latest[r['topology']]=r
    env=json.loads((ROOT/'docs/validation/soft3888/environment-preflight.json').read_text())
    catalog=json.loads((ROOT/'ground_truth/audit.json').read_text())
    model=json.loads((ROOT/'docs/validation/soft3888/model-evaluation-preflight.json').read_text())
    result=dict(kind='current-development-completion-status',ground_truth_catalog=catalog,team_integration=[dict(topology=name,status=r.get('status'),passed=r.get('passed'),error=r.get('error'),evidence_path=r['evidence_path'],cleanup=r.get('cleanup')) for name,r in sorted(latest.items())],model_evaluation=dict(status=model['status'],executed_runs=len(model.get('executed_runs',[])),missing_credentials=model['missing_credentials']),external_blockers=dict(missing_model_credentials=env['missing_credentials'],missing_images=[dict(topology=t['topology'],images=t['missing_images']) for t in env['topologies'] if t['missing_images']],vlan_capability=env.get('vlan_capability')))
    (ROOT/'docs/validation/soft3888/completion-status.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Team integration: actual current outcomes','', 'These are recorded reference integration outcomes. Read ground_truth/audit.json for the active catalog scope; this report does not establish current acceptance of other team configurations. A passing smoke checks deployment, exact device inventory, one local gateway and real MCP tools. It is not a claim that every route/service/fault is correct.', '', '| Topology | Latest outcome | Actual evidence |','|---|---|---|']
    for name,r in sorted(latest.items()):lines.append(f"| {name} | {r.get('status')} | [JSON](../{r['evidence_path']}) |")
    lines+=['', 'The 75/92-device personal deliverables have separate full fault/recovery and no-fault reports in [the validation index](soft3888-validation-results.md).', '', 'Kath3/Kath4 startup and isolated capability probes show VLAN creation failures in this environment. Kath1 needs the unavailable kathara/dhcp image or its original Dockerfile. Source configurations were retained; failed attempts were not relabeled as passes.', '', 'No new model diagnosis or grading ran: the attempted pilot stopped at credential preflight. Source scenario prose is preserved; legacy healthy/recovery contract gaps remain explicitly listed in ground_truth/.', '', 'Historical 50-device variants are not included in the active delivery catalog. Recorded reference results must not be treated as current validation of the entire team repository.','']
    (ROOT/'docs/soft3888-team-integration.md').write_text('\n'.join(lines))
    print('Integration outcomes:',{name:r.get('status') for name,r in latest.items()})

if __name__=='__main__':main()
