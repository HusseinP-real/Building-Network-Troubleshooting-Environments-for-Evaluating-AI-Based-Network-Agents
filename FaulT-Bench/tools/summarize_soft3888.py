#!/usr/bin/env python3
"""Report executed lab outcomes; never turn an incomplete run into a pass."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'faultbench/src'))
from faultbench.scenario import resolve_scenario


def current(report):
    root=ROOT/'topology_kathara'/report['topology']
    for rel,digest in report.get('source_sha256',{}).items():
        p=root/rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:return False
    for ref,digest in report.get('scenario_sha256',{}).items():
        try:p=resolve_scenario(ref)
        except (FileNotFoundError,ValueError):return False
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:return False
    if report.get('experiment'):
        e=report['experiment']; p=Path(e['path'])
        if not p.is_absolute():p=ROOT/p
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:return False
    return bool(report.get('source_sha256') and report.get('scenario_sha256'))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    lines=['# Executed SOFT3888 validation','',
           'These are lab/tool tests without LLM inference or agent scores. Historical failures are retained.', '',
           'Current deliverables: Kath5_Jiayuan_75Devices and NIKA_Clos_Jiayuan_92Devices (required range: 75–100 devices each). Clos_Jiayuan_41Devices is an undersized historical prototype; its successful tests do not satisfy Topology 2 acceptance.', '',
           '| Topology / lab | Outcome | Current configuration | Passed stages / attempts | Evidence |',
           '|---|---|---|---|---|']
    for p in sorted((ROOT/'docs/validation/soft3888').glob('*.json')):
        r=json.loads(p.read_text())
        if not isinstance(r,dict):continue
        if r.get('topology')=='Clos_Jiayuan_41Devices':continue
        if r.get('kind')!='live-network-validation-without-llm' or 'topology' not in r:continue
        outcome='PASS' if r.get('passed') and r.get('finished_at') and r.get('cleanup',{}).get('passed') else 'FAIL' if r.get('finished_at') else 'INCOMPLETE'
        if outcome=='FAIL' and r.get('error','').startswith('KeyboardInterrupt'):outcome='ABORTED'
        if outcome=='PASS' and r.get('validation_scope')=='no-fault-control':outcome='CONTROL PASS'
        if outcome=='PASS' and r.get('validation_scope')=='experiment':outcome='EXPERIMENT PASS'
        if outcome=='PASS' and not any(s['passed'] and s['name'].endswith(':fault') for s in r.get('stages',[])):outcome='BASELINE PASS'
        passed=sum(s['passed'] for s in r.get('stages',[]))
        lines.append(f'| {r["topology"]} / {r["lab_name"]} | {outcome} | {"yes" if current(r) else "no"} | {passed} / {len(r.get("stages",[]))} | [JSON](validation/soft3888/{p.name}) |')
    lines+=['','A failed convergence attempt is not a failed final stage if a later attempt passed. A PASS requires successful exact-lab cleanup. “Current configuration” compares saved topology/scenario content hashes with present files; consult the report for runtime and harness hashes.',
            '', 'Paid SADE evaluation remains unrun until Anthropic/OpenAI credentials are supplied securely. MCP smoke tests verify tools and inventory, not model diagnosis quality.','']
    text='\n'.join(lines)
    if args.output:args.output.write_text(text)
    else:print(text)

if __name__=='__main__':main()
