#!/usr/bin/env python3
"""Validate P20Enterprise v3 on live Kathara/FRR without an LLM or API keys."""
from __future__ import annotations
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid

from validate_haosenpeng_fault import Lab, ROOT, evaluate
from faultbench.scenario import parse_scenario, resolve_scenario, load_manifest
from p20_enterprise_model import NAME, VERSION, SPEC, CASES, checks, rendered_files

TOPOLOGY = ROOT / 'topology_kathara' / NAME
SPEC_PATH = ROOT / 'docs/p20-enterprise/topology.json'
MANIFEST = ROOT / 'faultbench/benchmarks/p20-enterprise.csv'
IDS = {case: data['id'] for case, data in CASES.items()}
REPAIRS = {case: (data['node'], data['repair']) for case, data in CASES.items() if data['repair']}


def specs():
    for name, expected in rendered_files().items():
        path = ROOT / name
        if not path.exists() or path.read_text() != expected:
            raise ValueError(f'Configuration/scenario drift: {name}; run tools/build_p20_enterprise.py after reviewing the model')
    if load_manifest(MANIFEST) != list(IDS.values()):
        raise ValueError('Manifest mismatch')
    scenarios = {}
    for case, sid in IDS.items():
        scenario = parse_scenario(resolve_scenario(sid))
        if scenario.topology != NAME or not scenario.ground_truth or not scenario.scoring_axes:
            raise ValueError(f'Incomplete scenario: {sid}')
        for field, expected in [('pre_check', checks('healthy')), ('post_inject_check', checks(case))]:
            actual = [(c.device, c.command, c.expect) for c in getattr(scenario, field)]
            if actual != expected:
                raise ValueError(f'Check mismatch: {sid} {field}')
        if [line.strip() for line in (scenario.injection.command or '').splitlines()] != [line.strip() for line in CASES[case]['inject'].splitlines()]:
            raise ValueError(f'Injection mismatch: {sid}')
        if case == 'healthy' and scenario.scenario_class != 'false-premise':
            raise ValueError('Healthy case must be a false-premise control')
        for command in (CASES[case]['inject'], CASES[case]['repair']):
            subprocess.run(['sh', '-n'], input=command, text=True, check=True)
        for node, command, expect in checks(case):
            if node not in SPEC['nodes']:
                raise ValueError(f'Unknown device {node}')
            evaluate(expect, 255, '')
        scenarios[case] = scenario
    for startup in TOPOLOGY.glob('*.startup'):
        subprocess.run(['sh', '-n', str(startup)], check=True)
    return SPEC, scenarios


def mutate(lab, node, command):
    rc, output = lab.exec(node, command)
    if rc:
        raise RuntimeError(f'{node} mutation failed ({rc}): {command}\n{output}')


def execute_batch(lab, node, commands):
    """Amortise CLI startup while retaining each command's output and exit code."""
    token = '__P20_' + uuid.uuid4().hex
    script = []
    for i, command in enumerate(commands):
        script += [f"printf '\\n{token}_{i}_BEGIN\\n'", f'sh -c {shlex.quote(command)}',
                   '_p20_rc=$?', f"printf '\\n{token}_{i}_END:%s\\n' \"$_p20_rc\""]
    rc, output = lab.exec(node, '\n'.join(script))
    if rc:
        raise RuntimeError(f'{node}: batch wrapper failed')
    results = []
    for i in range(len(commands)):
        match = re.search(rf'{token}_{i}_BEGIN\n(.*?)\n{token}_{i}_END:(\d+)(?:\n|$)', output, re.S)
        if not match:
            raise RuntimeError(f'{node}: missing command result {i}')
        results.append((int(match.group(2)), match.group(1).strip()))
    return results


def run_stage(lab, report, label, rows):
    groups = defaultdict(list)
    for index, (node, command, expect) in enumerate(rows):
        groups[node].append((index, command, expect))
    jobs = [(node, entries[i:i+4]) for node, entries in groups.items() for i in range(0, len(entries), 4)]

    def run(job):
        node, entries = job
        outputs = execute_batch(lab, node, [e[1] for e in entries])
        return [(index, {'device': node, 'command': command, 'expect': expect,
                         'rc': rc, 'output': out, 'passed': evaluate(expect, rc, out)})
                for (index, command, expect), (rc, out) in zip(entries, outputs)]

    indexed = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for result in pool.map(run, jobs):
            indexed.extend(result)
    records = [record for _, record in sorted(indexed)]
    passed = all(r['passed'] for r in records)
    report['stages'].append({'name': label, 'passed': passed, 'checks': records})
    failures = [f'{r["device"]}: expected {r["expect"]}' for r in records if not r['passed']]
    print(f'[{label}] {"PASS" if passed else "WAIT"}' + (f' ({", ".join(failures)})' if failures else ''), flush=True)
    return passed


def converge(lab, report, label, rows, timeout=120):
    deadline, consecutive = time.monotonic() + timeout, 0
    while True:
        passed = run_stage(lab, report, label, rows)
        consecutive = consecutive + 1 if passed else 0
        if consecutive == 2:
            return
        if time.monotonic() >= deadline:
            raise RuntimeError(f'{label} did not stabilise; see failed checks in report')
        time.sleep(2)


def verify_config(lab, spec, report):
    def inspect(item):
        node, data = item
        commands = ['test -f /tmp/p20-ready && ip -j address show', 'ip -j route show', 'cat /proc/sys/net/ipv4/ip_forward']
        outputs = execute_batch(lab, node, commands)
        if any(rc for rc, _ in outputs):
            _, log = lab.exec(node, 'cat /var/log/startup.log')
            raise RuntimeError(f'{node} startup/configuration incomplete: {log[-2000:]}')
        addresses = {a['ifname']: {f"{v['local']}/{v['prefixlen']}" for v in a.get('addr_info', []) if v['family'] == 'inet'} for a in json.loads(outputs[0][1])}
        for iface, (_, addr) in data['interfaces'].items():
            if addr not in addresses.get(iface, set()):
                raise RuntimeError(f'{node} missing {addr} on {iface}')
        routes = json.loads(outputs[1][1])
        if 'ospf' in data:
            # Router static/default routes could hide a broken OSPF advertisement.
            if any(r.get('dst') == 'default' or r.get('protocol') in ('static', 'boot') for r in routes):
                raise RuntimeError(f'{node} has an unexpected static/default route')
        else:
            gateway = data['routes']['default']
            if not any(r.get('dst') == 'default' and r.get('gateway') == gateway for r in routes):
                raise RuntimeError(f'{node} has wrong default gateway')
        if outputs[2][1].strip() != ('1' if 'ospf' in data else '0'):
            raise RuntimeError(f'{node} has wrong forwarding state')
        return {'device': node, 'passed': True}
    with ThreadPoolExecutor(max_workers=8) as pool:
        report.setdefault('configuration_checks', []).extend(pool.map(inspect, spec['nodes'].items()))


def snapshot(lab, report, label):
    def inspect(node):
        commands = ['ip -j address show', 'ip -j route show']
        if 'ospf' in SPEC['nodes'][node]:
            commands += ["vtysh -c 'show ip ospf neighbor'", "vtysh -c 'show ip ospf route'", "vtysh -c 'show running-config'"]
        outputs = execute_batch(lab, node, commands)
        if any(rc for rc, _ in outputs):
            raise RuntimeError(f'Could not snapshot {node}')
        return [{'device': node, 'command': cmd, 'rc': rc, 'output': out} for cmd, (rc, out) in zip(commands, outputs)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = [r for group in pool.map(inspect, SPEC['nodes']) for r in group]
    report.setdefault('snapshots', []).append({'name': label, 'commands': rows})


def cycle(lab, report, case, scenario, timeout):
    converge(lab, report, 'baseline-before-' + case, checks('healthy'), timeout)
    try:
        if scenario.injection.command:
            mutate(lab, scenario.injection.device, scenario.injection.command)
        converge(lab, report, case, checks(case), timeout)
        snapshot(lab, report, case)
        if scenario.injection.command:
            mutate(lab, scenario.injection.device, scenario.injection.command)
            converge(lab, report, case + '-repeat-injection', checks(case), timeout)
    finally:
        if case in REPAIRS:
            mutate(lab, *REPAIRS[case])
    converge(lab, report, 'recovered-after-' + case, checks('healthy'), timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--converge-timeout', type=int, default=120)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--exec-backend', choices=['docker', 'kathara'], default='docker',
                        help='docker avoids repeated Kathara CLI startup; both use the same isolated lab')
    args = parser.parse_args()
    if args.repeat < 1 or args.converge_timeout < 1:
        parser.error('repeat and timeout must be positive')
    spec, scenarios = specs()
    if args.check_only:
        print('PASS: v3: 75 devices, 47 subnets, 8 OSPF areas, 6 scenarios; generated files and shell syntax match. Live tests NOT RUN.')
        return 0
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = args.output or ROOT / 'faultbench/runs/p20-enterprise' / f'{stamp}.json'
    report = {'kind': 'p20-enterprise-live-network-no-llm', 'version': VERSION, 'started_at': stamp,
              'passed': False, 'stages': [], 'topology': NAME, 'repeat': args.repeat, 'case': args.case,
              'exec_backend': args.exec_backend,
              'scenario_sha256': {s.scenario_id: hashlib.sha256(s.source_path.read_bytes()).hexdigest() for s in scenarios.values()},
              'topology_sha256': {str(f.relative_to(TOPOLOGY)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(TOPOLOGY.rglob('*')) if f.is_file() and f.name != '.DS_Store'}}
    temporary = None
    try:
        for binary in ('kathara', 'docker'):
            if not shutil.which(binary):
                raise RuntimeError(f'{binary} is not on PATH')
        for cmd in (['docker', 'info', '--format', '{{.ServerVersion}}'], ['kathara', '--version']):
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
            report[cmd[0] + '_version'] = proc.stdout.strip()
        for image in ('kathara/base', 'kathara/frr'):
            proc = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{json .RepoDigests}}'], capture_output=True, text=True, timeout=30, check=True)
            report.setdefault('image_digests', {})[image] = json.loads(proc.stdout)
        temporary = Path(tempfile.mkdtemp(prefix='p20-enterprise-v3-')) / NAME
        shutil.copytree(TOPOLOGY, temporary, ignore=shutil.ignore_patterns('.DS_Store', 'shared'))
        report['temporary_lab'] = str(temporary)
        print(f'[deploy] 75 devices in isolated lab {temporary}', flush=True)
        proc = subprocess.run(['kathara', 'lstart', '-d', str(temporary), '--noterminals', '-H', '-S'], capture_output=True, text=True, timeout=600)
        report['deployment'] = {'rc': proc.returncode, 'output': proc.stdout + proc.stderr}
        if proc.returncode:
            raise RuntimeError('Deployment failed: ' + report['deployment']['output'])
        if args.exec_backend == 'docker':
            from p20_docker_lab import DockerLab
            lab = DockerLab(temporary, spec['nodes'])
        else:
            lab = Lab(temporary)
        verify_config(lab, spec, report)
        converge(lab, report, 'initial-baseline', checks('healthy'), args.converge_timeout)
        snapshot(lab, report, 'initial-baseline')
        for iteration in range(1, args.repeat + 1):
            for case in (CASES if args.case == 'all' else [args.case]):
                start = len(report['stages'])
                try:
                    cycle(lab, report, case, scenarios[case], args.converge_timeout)
                finally:
                    for stage in report['stages'][start:]:
                        stage.update(iteration=iteration, scenario_id=IDS[case])
        verify_config(lab, spec, report)
        snapshot(lab, report, 'final-recovery')
        report['passed'] = True
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        print(report['error'], flush=True)
    finally:
        if temporary is not None:
            try:
                proc = subprocess.run(['kathara', 'lclean', '-d', str(temporary)], capture_output=True, text=True, timeout=300)
                report['cleanup'] = {'rc': proc.returncode, 'output': proc.stdout + proc.stderr}
                if proc.returncode:
                    report['passed'] = False
            except Exception as exc:
                report['cleanup'] = {'error': str(exc)}
                report['passed'] = False
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(f'Report: {output}', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
