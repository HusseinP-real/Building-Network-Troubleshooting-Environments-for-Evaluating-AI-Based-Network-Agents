#!/usr/bin/env python3
"""Curate team runs from source truth, keeping persona rewrites separate."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'faultbench/src'))
from faultbench.ground_truth import build

def main():
    data=build();selected=[]
    def ref(r):return r['scenario_id'] if r['source_path'].startswith('dataset/') else r['source_path']
    for t in data['topologies']:
        rows=[r for r in data['records'] if r['topology']==t['topology'] and r['ticket_style']=='standard']
        core_file=ROOT/'topology_kathara'/t['topology']/'benchmark.json'
        if core_file.exists():
            preferred=json.loads(core_file.read_text())['scenarios'];rows=sorted(rows,key=lambda r:(r['scenario_id'] not in preferred,r['scenario_id']))
        for anomaly in (True,False):
            chosen=next((r for r in rows if r['expected_anomaly']==anomaly),None)
            if chosen:selected.append(ref(chosen))
    outputs={'team_pilot.csv':selected,'team_standard.csv':[ref(r) for r in data['records'] if r['ticket_style']=='standard']}
    for name,refs in outputs.items():(ROOT/'faultbench/benchmarks'/name).write_text('scenario\n'+'\n'.join(refs)+'\n')
    print({name:len(refs) for name,refs in outputs.items()})

if __name__=='__main__':main()
