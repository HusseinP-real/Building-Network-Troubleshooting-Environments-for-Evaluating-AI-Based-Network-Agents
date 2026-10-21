#!/usr/bin/env python3
"""Plan/run SADE and ReAct fairly, or summarize actual outputs without inventing runs."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'faultbench/src'))
from faultbench.evaluation import execute,summarize
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,default=ROOT/'faultbench/benchmarks/soft3888_evaluation.csv')
    ap.add_argument('--agents',default='sade,react-full');ap.add_argument('--repeats',type=int,default=1)
    ap.add_argument('--output',type=Path,default=ROOT/'faultbench/runs/soft3888-evaluation')
    ap.add_argument('--execute',action='store_true');ap.add_argument('--summarize',action='store_true')
    args=ap.parse_args()
    if args.summarize:
        r=summarize(args.output/'runs',args.output/'comparison.json');print('Comparison status:',r['status'])
    else:
        r=execute(args.manifest,[a.strip() for a in args.agents.split(',') if a.strip()],args.output,args.repeats,args.execute)
        print(json.dumps({k:r[k] for k in ['status','planned_runs','missing_credentials']},indent=2))
        if r['status'].startswith('blocked') or r['status']=='stopped_after_failure':raise SystemExit(2)
