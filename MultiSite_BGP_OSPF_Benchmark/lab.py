#!/usr/bin/env python3
"""Unified CLI for generating, launching, validating and faulting the Kathara lab."""
import argparse, json, subprocess, sys, time, shlex, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def call(args, capture=False, timeout=120):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=capture, timeout=timeout)

def exec_cmd(node, command, timeout=60):
    """Run through one Kathara COMMAND argument, capturing the *inner* shell status.

    Kathara's CLI expects DEVICE_NAME COMMAND (one command string). Supplying
    `bash`, `-lc`, and the script as separate argv entries is not portable.
    """
    marker = '__SOFT3888_RC__='
    shell_script = command + "\nrc=$?; printf '\n__SOFT3888_RC__=%s\n' \"$rc\""
    remote_command = 'bash -lc ' + shlex.quote(shell_script)
    outer = call(['kathara', 'exec', '-d', str(ROOT), node, remote_command], True, timeout)
    # The container's exit status may not always be propagated by `kathara exec`.
    match = re.search(r'(?m)^' + re.escape(marker) + r'(\d+)\s*$', outer.stdout)
    if not match:
        return subprocess.CompletedProcess(outer.args, 1, outer.stdout,
            (outer.stderr or '') + '\nMissing inner command exit marker; no PASS can be asserted.')
    stdout = re.sub(r'(?m)^' + re.escape(marker) + r'\d+\s*$', '', outer.stdout).rstrip()
    return subprocess.CompletedProcess(outer.args, int(match.group(1)), stdout, outer.stderr)

def ok(node,cmd):
    result=exec_cmd(node,cmd)
    if result.returncode: print(f'ERROR on {node}: {cmd}\n{result.stderr or result.stdout}',file=sys.stderr)
    return result.returncode==0

def run_checks():
    # Functional probes; not just a configuration-file lint.
    inv=json.loads((ROOT/'inventory.json').read_text())
    checks=[]
    def check(label,node,cmd):
        try: passed=ok(node,cmd)
        except Exception as e: passed=False;print(f'{label}: {e}',file=sys.stderr)
        checks.append({'check':label,'passed':passed,'node':node,'command':cmd})
        print(('PASS' if passed else 'FAIL')+' '+label)
    for node in ('e1','e2','e3','e4'):
        peer=next(e for e in inv['interfaces'][node] if e.get('peer') in ('a1','a3','b1','b3'))['peer']
        remote=next(e['addr'] for e in inv['interfaces'][peer] if e.get('peer')==node)
        check(f'bgp_established_{node}',node,
              f"vtysh -c 'show bgp neighbors {remote}' | grep -q 'BGP state = Established'")
    for site in ('hq','ba','bb','dc'):
        check(f'site_{site}_to_dc',f'{site}_h01','ping -c 2 -W 2 10.40.10.21')
        check(f'site_{site}_to_isp_a',f'{site}_h01','ping -c 2 -W 2 198.18.10.10')
        check(f'site_{site}_to_isp_b',f'{site}_h01','ping -c 2 -W 2 198.18.20.10')
    check('isp_a_http','hq_h01','curl -fsS --max-time 8 http://198.18.10.10:8080/ | grep -q healthy')
    check('isp_b_http','hq_h01','curl -fsS --max-time 8 http://198.18.20.10:8080/ | grep -q healthy')
    result={'passed':sum(x['passed'] for x in checks),'total':len(checks),'checks':checks,'timestamp_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
    dest=ROOT/'results';dest.mkdir(exist_ok=True)
    (dest/'baseline_latest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Baseline: {result["passed"]}/{result["total"]} passed')
    return 0 if result['passed']==result['total'] else 1

FAULTS={
'F01':{'desc':'Disable both enterprise-to-ISP-A peer interfaces; ISP-B remains available',
 'nodes':['a1','a3'],'apply':["ip link set eth1 down","ip link set eth1 down"],'repair':["ip link set eth1 up","ip link set eth1 up"],
 'source':'hq_h01','fail':'ping -c 2 -W 2 198.18.10.10','pass':'ping -c 2 -W 2 198.18.20.10'},
'F02':{'desc':'Withdraw ISP-A service prefix from both eBGP speakers without dropping peer links',
 'nodes':['a1','a3'],'apply':["vtysh -c 'configure terminal' -c 'router bgp 65010' -c 'no network 198.18.10.0/24'","vtysh -c 'configure terminal' -c 'router bgp 65010' -c 'no network 198.18.10.0/24'"],
 'repair':["vtysh -c 'configure terminal' -c 'router bgp 65010' -c 'network 198.18.10.0/24'","vtysh -c 'configure terminal' -c 'router bgp 65010' -c 'network 198.18.10.0/24'"],
 'source':'hq_h01','fail':'ping -c 2 -W 2 198.18.10.10','pass':'ping -c 2 -W 2 198.18.20.10'},
'F03':{'desc':'Disable OSPF on both Branch-A routers to isolate their routes',
 'nodes':['ba_r1','ba_r2'],'apply':['service frr stop','service frr stop'],
 'repair':['service frr start','service frr start'],
 'source':'hq_h01','fail':'ping -c 2 -W 2 10.20.10.21','pass':'ping -c 2 -W 2 10.40.10.21'},
}

def fault(which,action):
    item=FAULTS[which]
    commands=item['apply' if action=='inject' else 'repair']
    good=True
    for node,cmd in zip(item['nodes'],commands):good=ok(node,cmd) and good
    print(f'{action}: {which}: {"OK" if good else "FAILED"}')
    return 0 if good else 1

def fault_test(which,delay=12):
    item=FAULTS[which]; output={'id':which,'description':item['desc']}
    before=ok(item['source'],item['fail']) and ok(item['source'],item['pass'])
    print('Baseline before fault:',before)
    if not before:return 2
    try:
        if fault(which,'inject'):return 3
        time.sleep(delay)
        # expected failure is inverse of probe exit status
        affected=not ok(item['source'],item['fail'])
        unaffected=ok(item['source'],item['pass'])
        output.update(fault_impact_observed=affected,control_path_healthy=unaffected)
    finally:
        fault(which,'repair')
    time.sleep(delay)
    recovered=ok(item['source'],item['fail'])
    output['recovered']=recovered
    output['passed']=all((output.get('fault_impact_observed'),output.get('control_path_healthy'),recovered))
    directory=ROOT/'results';directory.mkdir(exist_ok=True)
    (directory/f'{which}_latest.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
    return 0 if output['passed'] else 1

def main():
    p=argparse.ArgumentParser(description='SOFT3888 Multi-Site BGP/OSPF benchmark')
    sub=p.add_subparsers(dest='cmd',required=True)
    for x in ('generate','start','stop','check','inventory'):sub.add_parser(x)
    for x in ('inject','repair','test-fault'):
        q=sub.add_parser(x);q.add_argument('fault',choices=sorted(FAULTS))
        if x=='test-fault':q.add_argument('--settle-seconds',type=int,default=25)
    args=p.parse_args()
    if args.cmd=='generate':
        from tools.generate import generate
        print(json.dumps({k:v for k,v in generate().items() if k.endswith('_count')},indent=2));return 0
    if args.cmd=='inventory':
        data=json.loads((ROOT/'inventory.json').read_text());print(json.dumps({k:v for k,v in data.items() if k.endswith('_count') or k=='autonomous_systems'},indent=2));return 0
    if args.cmd=='start':return call(['kathara','lstart','-d',str(ROOT),'--noterminals'],timeout=None).returncode
    if args.cmd=='stop':return call(['kathara','lclean','-d',str(ROOT)],timeout=None).returncode
    if args.cmd=='check':return run_checks()
    if args.cmd in ('inject','repair'):return fault(args.fault,args.cmd)
    if args.cmd=='test-fault':return fault_test(args.fault,args.settle_seconds)
    return 1

if __name__=='__main__':sys.exit(main())
