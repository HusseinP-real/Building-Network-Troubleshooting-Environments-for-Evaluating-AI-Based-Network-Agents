#!/usr/bin/env python3
"""Recover startup configuration in running containers of ONE Kathara lab.

No containers are removed or recreated. Do not use during an active fault test.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def command(*args, check=False):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=check)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Actually initialise devices; otherwise preview')
    p.add_argument('--lab-id', help='Exact Kathara ID to target if more than one matching lab')
    args=p.parse_args()
    inventory=json.loads((ROOT/'inventory.json').read_text())
    expected=set(inventory['interfaces'])
    out=command('docker','ps','--format','{{.Names}}')
    if out.returncode:
        print(out.stderr,file=sys.stderr);return 2
    # Docker names have the form kathara_<user>_<device>_<lab-id>.
    matches={}
    for name in out.stdout.splitlines():
        for node in expected:
            m=re.search(r'_'+re.escape(node)+r'_([^_]+)$',name)
            if name.startswith('kathara_') and m:
                lab=m.group(1)
                matches.setdefault(lab,{})[node]=name
                break
    if args.lab_id:
        labid=args.lab_id
    else:
        choices=[(lab,nodes) for lab,nodes in matches.items() if 'e1' in nodes]
        if len(choices)!=1:
            print('Cannot uniquely identify the current lab. Options:',
                  {k:len(v) for k,v in matches.items()},file=sys.stderr)
            print('Re-run with --lab-id EXACT_ID',file=sys.stderr)
            return 2
        labid=choices[0][0]
    nodes=matches.get(labid,{})
    print(f'Target lab: {labid}; running matched devices: {len(nodes)}/{len(expected)}')
    missing=sorted(expected-set(nodes))
    if missing:print('Missing running devices:',', '.join(missing))
    if not args.apply:
        print('DRY RUN. To run initialization: python3 tools/recover_running.py --apply')
        return 0
    failed=[]; skipped=[]; fixed=[]
    for node in sorted(nodes):
        container=nodes[node]
        it=inventory['interfaces'][node]
        if '_sw' in node:
            probe=command('docker','exec',container,'ip','link','show','br0')
            initialized=probe.returncode==0
        else:
            address=next((x['addr'] for x in it if x.get('addr')),None)
            probe=command('docker','exec',container,'ip','-o','-4','addr','show')
            initialized=bool(address and re.search(r'(?<!\d)'+re.escape(address)+r'/',probe.stdout))
            if node in inventory.get('autonomous_systems',{}):
                pass
        if initialized:
            skipped.append(node)
            continue
        src=ROOT/f'{node}.startup'
        if not src.exists():
            failed.append((node,'Missing startup source'));continue
        dest='/tmp/soft3888-recovery.sh'
        cp=command('docker','cp',str(src),f'{container}:{dest}')
        if cp.returncode:
            failed.append((node,cp.stderr.strip()));continue
        run=command('docker','exec',container,'bash',dest)
        if run.returncode:
            failed.append((node,(run.stdout+'\n'+run.stderr)[-1400:].strip()))
            print(f'FAIL {node}: {failed[-1][1]}',file=sys.stderr)
        else:
            fixed.append(node)
            print('OK ',node)
    print(f'Finished: initialised {len(fixed)}, already configured {len(skipped)}, failed {len(failed)}, missing {len(missing)}')
    if failed:
        print('First errors:',failed[:5],file=sys.stderr)
    return 1 if failed or missing else 0

if __name__=='__main__':sys.exit(main())
