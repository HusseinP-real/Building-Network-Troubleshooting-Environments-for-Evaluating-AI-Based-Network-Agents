#!/usr/bin/env python3
"""Export all available topology/scenario truth without inventing test results."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'faultbench/src'))
from faultbench.ground_truth import export
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path);ap.add_argument('--topology',action='append',help='Limit the catalog to named topologies; repeat for multiple labs');args=ap.parse_args()
    d=export(args.output,args.topology)
    print(f"Catalog: {len(d['topologies'])} topologies / {len(d['records'])} cases; {len(d['parse_errors'])} parse errors / {len(d['topology_errors'])} constructor errors")
    print('Records with issues:',sum(bool(r['issues']) for r in d['records']))
