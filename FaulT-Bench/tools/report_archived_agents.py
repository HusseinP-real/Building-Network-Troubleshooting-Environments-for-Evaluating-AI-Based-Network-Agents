#!/usr/bin/env python3
"""Reproduce alternative-agent comparisons from archived runs, never label them new."""
from pathlib import Path
import csv,json,statistics
from collections import defaultdict,Counter
ROOT=Path(__file__).resolve().parents[1]

def build():
    source=ROOT/'final_results/MANIFEST.csv';groups=defaultdict(list)
    with source.open(newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):groups[row['arm'],row['agent']].append(row)
    result=[]
    for (arm,agent),rows in sorted(groups.items()):
        scored=[r for r in rows if r['status']=='scored']
        def mean(key,selected):
            values=[float(r[key]) for r in selected if r.get(key) not in ('',None)]
            return statistics.mean(values) if values else None
        confusion=Counter()
        for r in rows:
            if r['submitted'].lower()!='true' or r['is_anomaly'].lower() not in ('true','false'):continue
            truth='false-premise' not in r['scenario_id'];obs=r['is_anomaly'].lower()=='true'
            confusion['tp' if truth and obs else 'fn' if truth else 'fp' if obs else 'tn']+=1
        result.append(dict(arm=arm,agent=agent,runs=len(rows),scored=len(scored),status_counts=dict(Counter(r['status'] for r in rows)),mean_outcome=mean('outcome_score',scored),mean_fix=mean('fix_score',scored),mean_reasoning=mean('reasoning_score',scored),mean_agent_reported_cost_usd=mean('cost_usd',rows),mean_lifecycle_seconds=mean('wall_seconds',rows),mean_tool_calls=mean('tool_calls',rows),confusion=dict(confusion)))
    return dict(kind='historical-agent-comparison-reproduction',source=str(source.relative_to(ROOT)),new_model_calls=0,scope='Archived original dataset only. Not a new evaluation of Kath5_Jiayuan_75Devices or NIKA_Clos_Jiayuan_92Devices.',latency_note='Archived wall_seconds includes lifecycle work; not isolated model investigation time.',cost_note='Archived agent cost: SDK-reported Claude cost and pricing-derived GPT estimates; excludes judge billing.',groups=result)

if __name__=='__main__':
    r=build();p=ROOT/'docs/validation/soft3888/archived-agent-comparison.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2)+'\n')
    lines=['# Alternative-agent comparison: archived evidence','',r['scope'],'','This reproduction calls no models. Group by experiment arm; do not pool persona rewrites into a new topology score.', '', '| Arm | Agent | Runs / scored | Outcome | Agent cost/run USD | Lifecycle seconds/run |','|---|---|---|---|---|---|']
    for row in r['groups']:
        if row['arm'] in ('base80','cex120'):
            lines.append(f"| {row['arm']} | {row['agent']} | {row['runs']} / {row['scored']} | {row['mean_outcome']:.3f} | {row['mean_agent_reported_cost_usd']:.4f} | {row['mean_lifecycle_seconds']:.1f} |")
    lines+=['',r['latency_note'],r['cost_note'],'','The new SOFT3888 pipeline separately times agent investigation and lifecycle. Run both SADE and react-full on the same soft3888_evaluation.csv (8 faults +2 no-fault controls), with identical repeats/tools, before making new accuracy, speed or cost claims. Missing credentials block those new experiments.','']
    (ROOT/'docs/soft3888-agent-comparison.md').write_text('\n'.join(lines))
    print('Reproduced',sum(g['runs'] for g in r['groups']),'archived runs; no new model evaluations')
