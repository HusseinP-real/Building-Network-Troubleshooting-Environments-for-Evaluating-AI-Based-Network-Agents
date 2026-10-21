#!/usr/bin/env python3
"""Create explicit no-fault cases; keep published core manifests unchanged."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def render():
    outputs={};ids=[]
    specs=[('Kath5_Jiayuan_75Devices','jiayuan75','jiayuan75-false-premise-internal-application','A Branch F user reports that the internal application is down and suspects an inter-area routing fault. Investigate the reported internal service path and determine whether an actionable fault is present.'),('NIKA_Clos_Jiayuan_92Devices','nika92','nika92-false-premise-pod1-web','External client_1 reports that web0.pod1 cannot be opened and suspects a routing or server fault. Investigate the reported service path and determine whether an actionable fault is present.')]
    for topo,folder,sid,prompt in specs:
        config=json.loads((ROOT/'topology_kathara'/topo/'benchmark.json').read_text())
        if folder=='jiayuan75':
            checks=[c for c in config['baseline'] if c['device'] in ('f1','mgmt3') or ('192.168.251.' in c['command'] and c['device'] in ('a1','b1'))]
            if not checks:checks=config['baseline'][-6:]
        else:
            checks=[c for c in config['baseline'] if (c['device']=='client_1' and ('10.1.1.2' in c['command'] or '10.0.1.80' in c['command'])) or (c['device']=='leaf_router_1_1') or (c['device']=='client_2' and 'dig @10.1.0.2' in c['command'])]
        if folder=='jiayuan75':
            checks += [dict(device='f1',command="dig @192.168.251.11 app.internal.test +short +time=1 +tries=1",expect='equals: 192.168.251.12'),dict(device='f1',command="curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{http_code}' http://192.168.251.12/",expect='200')]
        else:
            checks += [dict(device='client_1',command="dig @10.0.0.2 web0.pod1 +short +time=1 +tries=1",expect='equals: 10.1.1.2'),dict(device='client_1',command="curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{http_code}' http://10.1.1.2:80/",expect='200')]
        assert checks
        textchecks='\n'.join(f"{c['device']}  {c['command']}  => expect {c['expect']}" for c in checks)
        boundary=('The configured Internal resolver is queried explicitly; not every legacy endpoint has a default resolver.' if folder=='jiayuan75' else 'Some external-client to external-client paths are down in the retained reference because Super-Spines share AS65000. Those paths are outside this service ticket and are not newly injected faults.')
        text=f'''Scenario: {sid}
Topology: {topo}
Validation: strict
Fault family: No fault / false-premise service report

[PROMPT-TO-AGENT]
{prompt}

[PRE-CHECK]
{textchecks}

[INJECTION]
device: none
action: no fault injected
note: Healthy-state negative control; do not mutate configuration.

[POST-INJECT-CHECK]
{textchecks}

[GROUND-TRUTH]
Fault location: none.
Fault type: no injected fault.
Root cause: the reported service outage is not reproduced in the checked healthy topology.
Expected symptoms: the declared service/routing checks succeed. {boundary}
Expected diagnosis: no actionable fault on the reported service path. Support the conclusion with actual observations; do not invent a device fault.

[FIX]
No configuration change is required. Document the successful checks and ask for the time or conditions of any intermittent report. Do not change working routes or services.

[RECOVERY]
device: {checks[0]['device']}
action: no repair required
note: No fault was injected, so preserve the healthy configuration.

[RECOVERY-CHECK]
{textchecks}

[SCORING-AXES]
assert-no-anomaly
assert-no-faulty-devices
must-verify-service: backs the healthy conclusion with live service/routing evidence
must-avoid-invented-cause: does not diagnose the reported service as broken without evidence

[NIKA-LABEL]
nika_label: not assigned
nika_category: NO_FAULT
in_taxonomy: not verified
'''
        outputs[ROOT/'dataset'/f'{folder}_Q/custom'/(sid+'.txt')]=text
        outputs[ROOT/'faultbench/benchmarks'/f'{folder}_controls.csv']='scenario\n'+sid+'\n'
        recipe=dict(name=sid,topology=topo,scenario=sid,steps=[dict(action='check',name='no-fault-service-path',checks=checks)])
        outputs[ROOT/'faultbench/experiments'/f'{folder}_control.json']=json.dumps(recipe,indent=2)+'\n'
        ids.append(sid)
    core=[]
    for topo,_,_,_ in specs:core+=json.loads((ROOT/'topology_kathara'/topo/'benchmark.json').read_text())['scenarios']
    for filename,refs in [('soft3888_controls.csv',ids),('soft3888_core.csv',core),('soft3888_evaluation.csv',core+ids),('soft3888_pilot.csv',[core[0],core[4],*ids])]:outputs[ROOT/'faultbench/benchmarks'/filename]='scenario\n'+'\n'.join(refs)+'\n'
    return outputs

if __name__=='__main__':
    outputs=render()
    for p,text in outputs.items():
        if p.exists() and p.read_text()!=text:raise SystemExit(f'Refusing changed file {p}')
    for p,text in outputs.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    print('Rendered 2 no-fault controls and isolated pilot/core/evaluation manifests')
