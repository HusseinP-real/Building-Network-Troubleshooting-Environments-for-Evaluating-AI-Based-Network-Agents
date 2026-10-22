#!/usr/bin/env python3
"""Real deploy/inventory/gateway/MCP smoke tests; never claim fault validation."""
import argparse,hashlib,ipaddress,json,os,subprocess,sys,tempfile,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'faultbench/src'))
from faultbench.ground_truth import get_labs,infer_roles
from faultbench.lab import kathara_exec,kathara_container_count,lclean,check_storage_budget,prepare_nika_startup_runtime
from faultbench.runtime import prepare_lab_runtime


def worker(topology,name):
    from Kathara.setting.Setting import Setting
    from Kathara.manager.Kathara import Kathara
    os.umask(0o022)
    s=Setting.get_instance();s.open_terminals=False;s.hosthome_mount=False;s.shared_mount=False
    lab=get_labs({topology})[0][topology];lab.name=name
    lab.general_options.update(open_terminals=False,hosthome_mount=False,shared_mount=False)
    if not (ROOT/'topology_kathara'/topology/'lab.conf').exists():prepare_nika_startup_runtime(lab)
    prepare_lab_runtime(lab);check_storage_budget(lab);Kathara.get_instance().deploy_lab(lab)


def smoke(topology,output):
    from contextlib import closing
    import docker
    lab=get_labs({topology})[0][topology]
    original_images={n:m.get_image() for n,m in lab.machines.items()}
    name='team-smoke-'+uuid.uuid4().hex[:12]
    report=dict(harness_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),kind='team-live-integration-smoke-without-llm',scope='Deployment, exact inventory, representative local gateway and real MCP tools only; not comprehensive healthy-state, fault, repair or model-score validation.',topology=topology,lab_name=name,passed=False,started_at=datetime.now(timezone.utc).isoformat(),probes=[])
    target=output/f'{topology}-{name}.json';target.parent.mkdir(parents=True,exist_ok=True)
    def save():target.write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        with closing(docker.from_env()) as client:
            available={tag for image in client.images.list() for tag in image.tags}
            missing=[m.get_image() for m in lab.machines.values() if m.get_image() not in available and m.get_image()+':latest' not in available]
        if missing:
            report.update(status='blocked_missing_images',missing_images=sorted(set(missing)));return report
        report['startup_overrides']=prepare_nika_startup_runtime(lab) if not (ROOT/'topology_kathara'/topology/'lab.conf').exists() else []
        report['runtime']=prepare_lab_runtime(lab);check_storage_budget(lab)
        proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',topology,name],capture_output=True,text=True,timeout=1200)
        report['deploy']=dict(rc=proc.returncode,output=proc.stdout+proc.stderr);save()
        if proc.returncode:raise RuntimeError('Deployment worker failed')
        report['running_devices']=kathara_container_count(name)
        if report['running_devices']!=len(lab.machines):raise RuntimeError('Device count mismatch')
        from Kathara.manager.Kathara import Kathara
        from faultbench.inventory import apply_roles
        from types import SimpleNamespace
        api=SimpleNamespace(lab=Kathara.get_instance().get_lab_from_api(lab_name=name))
        if not apply_roles(api,topology=topology):raise RuntimeError('Explicit role metadata missing')
        report['inventory_complete']=True
        candidates=api.hosts+[h for group in api.servers.values() for h in group]
        # Prefer the source's deterministic pc0/client1 paths, not arbitrary guesses.
        ordered=sorted(candidates,key=lambda n:(n not in ('pc0','pc1','client1','client_0'),n))
        if not ordered:raise RuntimeError('No endpoint role available')
        host=ordered[0];deadline=time.monotonic()+120
        while True:
            rc,route=kathara_exec(name,host,'ip -4 route show default',timeout=15)
            import re
            gateway=re.search(r'\bvia ([0-9.]+)',route)
            rc2,address=kathara_exec(name,host,'ip -4 -o addr show scope global',timeout=15)
            match=re.search(r'\binet ([0-9.]+/\d+)',address)
            if rc==0 and rc2==0 and gateway and match:break
            if time.monotonic()>=deadline:raise RuntimeError('Representative endpoint has no IPv4 address/default route')
            time.sleep(3)
        command='ping -n -c2 -W1 '+gateway[1]
        from faultbench.checks import _evaluate_expectation
        deadline=time.monotonic()+120
        while True:
            rc,ping=kathara_exec(name,host,command,timeout=15)
            ok,reason=_evaluate_expectation('0% loss',rc,ping,command=command)
            report['probes'].append(dict(device=host,command=command,rc=rc,output=ping,passed=ok,rationale=reason));save()
            if ok:break
            if time.monotonic()>=deadline:raise RuntimeError('Representative local-gateway ping failed after convergence gate')
            time.sleep(3)
        routers=[r for r in api.routers if 'frr' in original_images[r] or r.startswith(('router','r','core','leaf','spine'))]
        if not routers:raise RuntimeError('No FRR diagnostic router')
        # Use one router directly sharing the endpoint LAN when available.
        host_domains={p.link.name for p in lab.machines[host].interfaces.values()}
        router=next((r for r in routers if host_domains & {p.link.name for p in lab.machines[r].interfaces.values()}),routers[0])
        from faultbench.mcp_smoke import run_smoke
        report['mcp_smoke']=[]
        try:run_smoke(name,topology,dict(host=host,destination=gateway[1],router=router,route=str(ipaddress.ip_interface(match[1]).network)),report['mcp_smoke'])
        finally:save()
        if topology=='ospf_enterprise_static' and api.servers.get('dns'):
            dns=api.servers['dns'][0]
            startup=lab.fs.readtext(dns+'.startup')
            dns_ip=re.search(r'ip addr(?:ess)? add ([0-9.]+)/',startup)
            zone=lab.fs.readtext(dns+'/etc/bind/db.local')
            record=re.search(r'^web0\s+IN\s+A\s+([0-9.]+)',zone,re.M)
            if not dns_ip or not record:raise RuntimeError('Reference service record could not be extracted')
            checks=[(f'dig @{dns_ip[1]} web0.local +short +time=1 +tries=1','equals: '+record[1]),(f"curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{{http_code}}' http://{record[1]}/",'200')]
            for command,expect in checks:
                rc,out=kathara_exec(name,dns,command,timeout=15)
                ok,why=_evaluate_expectation(expect,rc,out,command=command)
                report['probes'].append(dict(device=dns,command=command,expect=expect,rc=rc,output=out,passed=ok,rationale=why));save()
                if not ok:raise RuntimeError('Reference DNS/HTTP server-farm check failed')
        report.update(status='passed',passed=True)
    except BaseException as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}')
    finally:
        try:lclean(name);report['cleanup']=dict(passed=True)
        except Exception as exc:report.update(passed=False,cleanup=dict(passed=False,error=str(exc)))
        report['finished_at']=datetime.now(timezone.utc).isoformat();save();print(topology,report.get('status'),str(target),flush=True)
    return report

if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='--worker':worker(sys.argv[2],sys.argv[3]);raise SystemExit(0)
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--topology',action='append');ap.add_argument('--output',type=Path,default=ROOT/'docs/validation/team-integration');args=ap.parse_args()
    names=args.topology or ['Kath1','Kath2','Kath3','Kath4','Kath5','simple_bgp','ospf_enterprise_static','dc_clos_bgp']
    rows=[smoke(name,args.output) for name in names]
    (args.output/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
    raise SystemExit(0 if all(r['passed'] for r in rows) else 1)
