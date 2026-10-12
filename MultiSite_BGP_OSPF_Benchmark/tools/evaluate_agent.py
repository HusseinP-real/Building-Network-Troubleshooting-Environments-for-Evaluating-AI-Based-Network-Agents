#!/usr/bin/env python3
"""Offline scoring harness. Does not claim or simulate actual SADE execution."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('predictions',help='JSON array containing scenario_id, ticket_id, fault_detected, fault_type, fault_devices, elapsed_seconds, tool_calls')
a=p.parse_args()
raw=json.loads(Path(a.predictions).read_text());assert isinstance(raw,list)
results=[]
for prediction in raw:
    fid=prediction['scenario_id'];gt=json.loads((ROOT/'scenarios'/fid/'ground_truth.json').read_text())
    items=json.loads((ROOT/'scenarios'/fid/'tickets.json').read_text())
    assert prediction['ticket_id'] in [x['ticket_id'] for x in items]
    row={'scenario_id':fid,'ticket_id':prediction['ticket_id'],
         'detection_correct':prediction.get('fault_detected') is True,
         'type_correct':prediction.get('fault_type')==gt['fault_type'],
         'location_correct':set(prediction.get('fault_devices',[]))==set(gt['fault_devices']),
         'elapsed_seconds':prediction.get('elapsed_seconds'), 'tool_calls':prediction.get('tool_calls')}
    results.append(row)
summary={'count':len(results),'metrics':{k:sum(x[k] for x in results)/len(results) if results else None for k in ('detection_correct','type_correct','location_correct')},'individual':results,'disclaimer':'Offline prediction scoring ONLY; the file is not proof of SADE integration or runtime performance.'}
print(json.dumps(summary,indent=2));dest=ROOT/'results';dest.mkdir(exist_ok=True);(dest/'agent_scores_latest.json').write_text(json.dumps(summary,indent=2)+'\n')
