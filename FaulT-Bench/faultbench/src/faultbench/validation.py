"""Isolated, evidence-producing validation of normal/fault/recovered states.

No LLM API calls. A deployment worker is killed on timeout before cleanup,
so late deployment threads cannot recreate resources after cleanup.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .checks import _evaluate_expectation
from .lab import kathara_exec, kathara_container_count, lclean
from .paths import KATH_BASE, ROOT
from .scenario import CheckLine, Injection, parse_scenario, resolve_scenario


def deploy_worker(path: str, name: str):
    os.umask(0o022)  # PyFilesystem's tar modes otherwise inherit restrictive cloud umask.
    from Kathara.setting.Setting import Setting
    from Kathara.parser.netkit.LabParser import LabParser
    from Kathara.manager.Kathara import Kathara
    settings = Setting.get_instance()
    settings.open_terminals = False
    settings.hosthome_mount = False
    settings.shared_mount = False
    lab = LabParser().parse(path)
    lab.name = name
    lab.general_options.update(open_terminals=False, hosthome_mount=False, shared_mount=False)
    from .runtime import prepare_lab_runtime
    prepare_lab_runtime(lab)
    Kathara.get_instance().deploy_lab(lab)


class Validation:
    def __init__(self, name: str, output: Path):
        self.name, self.output = name, output
        self.report = dict(kind='live-network-validation-without-llm',
                           started_at=datetime.now(timezone.utc).isoformat(),
                           lab_name=name, passed=False, stages=[],
                           harness_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')})

    def save(self):
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temp = self.output.with_suffix('.tmp')
        temp.write_text(json.dumps(self.report, indent=2, ensure_ascii=False) + '\n')
        temp.replace(self.output)

    def command(self, device, command, timeout=15):
        import shlex
        # This timeout runs INSIDE the device, so a failed probe cannot leave
        # an unbounded command running after its caller has timed out.
        return kathara_exec(self.name, device, f'timeout {int(timeout)} sh -c ' + shlex.quote(command), timeout=timeout+10)

    def mutate(self, injection):
        rc, output = self.command(injection.device, injection.command, timeout=60)
        self.report.setdefault('mutations', []).append(dict(device=injection.device,
            command=injection.command, rc=rc, output=output))
        self.save()
        if rc != 0:
            raise RuntimeError(f'Mutation failed on {injection.device} (rc={rc}): {output}')

    def stage(self, name, checks, timeout=0):
        if not checks:
            raise ValueError(f'{name}: refusing empty checks')
        deadline = time.monotonic() + timeout
        while True:
            records = []
            for check in checks:
                rc, output = self.command(check.device, check.command)
                passed, rationale = _evaluate_expectation(check.expect, rc, output, command=check.command)
                records.append(dict(**asdict(check), rc=rc, output=output,
                                    passed=passed, rationale=rationale))
            passed = all(r['passed'] for r in records)
            self.report['stages'].append(dict(name=name, at=datetime.now(timezone.utc).isoformat(), passed=passed, checks=records))
            self.save()
            if passed:
                print(f'[{name}] PASS ({len(records)} checks)', flush=True)
                return
            if time.monotonic() >= deadline:
                failed = [r for r in records if not r['passed']]
                raise RuntimeError(f'{name} failed: {json.dumps(failed, ensure_ascii=False)}')
            print(f'[{name}] waiting for convergence', flush=True)
            time.sleep(3)


def validate(topology, output, repeats=2, baseline_only=False, experiment=None):
    src = KATH_BASE / topology
    config = json.loads((src / 'benchmark.json').read_text())
    baseline = [CheckLine(**c) for c in config['baseline']]
    scenarios = [parse_scenario(resolve_scenario(s)) for s in config['scenarios']]
    for sc in scenarios:
        if sc.topology != topology or not (sc.pre_check and sc.post_inject_check and sc.recovery and sc.recovery.command and sc.recovery_check):
            raise ValueError(f'Incomplete or mismatched scenario: {sc.scenario_id}')
    recipe = None
    if experiment is not None:
        recipe = json.loads(experiment.read_text())
        if baseline_only or recipe['topology'] != topology:
            raise ValueError('Experiment topology mismatch or baseline-only combination')
        scenarios = [parse_scenario(resolve_scenario(recipe['scenario']))]
        sc = scenarios[0]
        if sc.topology != topology or not (sc.pre_check and sc.recovery and sc.recovery_check):
            raise ValueError('Incomplete experiment scenario')
        if not recipe.get('steps') or recipe['steps'][-1]['action'] != 'check':
            raise ValueError('Experiment requires steps and a final check')
        for step in recipe['steps']:
            if step['action'] not in {'inject', 'recover', 'mutate', 'check'}:
                raise ValueError('Unknown experiment action')
    reports = []
    for cycle in range(1, repeats + 1):
        name = f'soft3888-{uuid.uuid4().hex[:12]}'
        out = output / f'{topology}-cycle{cycle}-{name}.json'
        run = Validation(name, out)
        run.report.update(topology=topology, cycle=cycle, validation_scope=('no-fault-control' if scenarios[0].scenario_class=='false-premise' else 'experiment') if recipe else 'baseline-only' if baseline_only else 'full-scenarios', validated_scenarios=[],
            source_sha256={str(p.relative_to(src)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(src.rglob('*')) if p.is_file() and p.suffix != '.md' and '__pycache__' not in p.parts and 'shared' not in p.parts},
            scenario_sha256={s.scenario_id: hashlib.sha256(s.source_path.read_bytes()).hexdigest() for s in scenarios})
        if recipe:
            run.report['experiment'] = dict(name=recipe['name'], path=str(experiment.relative_to(ROOT)), sha256=hashlib.sha256(experiment.read_bytes()).hexdigest())
        temp = Path(tempfile.mkdtemp(prefix=name + '-'))
        path = temp / topology
        shutil.copytree(src, path, ignore=shutil.ignore_patterns('shared', '__pycache__'))
        run.report['temporary_lab'] = str(path)
        try:
            import docker
            from contextlib import closing
            with closing(docker.from_env()) as client:
                run.report['docker_version'] = client.version()['Version']
                info = client.info()
                run.report['storage_driver'] = info['Driver']
                if info['Driver'] == 'vfs':
                    from Kathara.parser.netkit.LabParser import LabParser
                    parsed = LabParser().parse(str(path))
                    from .runtime import prepare_lab_runtime
                    run.report['runtime'] = prepare_lab_runtime(parsed)
                    estimate = sum(client.images.get(m.get_image()).attrs['Size'] for m in parsed.machines.values())
                    free = shutil.disk_usage(ROOT).free
                    run.report['disk_preflight'] = dict(estimated_container_bytes=estimate, free_bytes=free)
                    if estimate * 3 > free:
                        raise RuntimeError(f'vfs requires approximately {estimate / 2**30:.1f} GiB for containers; only {free / 2**30:.1f} GiB free. No deployment attempted.')
                run.report['images'] = {image: dict(id=client.images.get(image).id, repo_digests=client.images.get(image).attrs.get('RepoDigests', [])) for image in config['images']}
            print(f'[deploy] {topology} cycle {cycle}: {name}', flush=True)
            proc = subprocess.run([sys.executable, '-m', 'faultbench.validation', '--deploy-worker', str(path), name],
                                  text=True, capture_output=True, timeout=1200)
            run.report['deploy'] = dict(rc=proc.returncode, output=proc.stdout + proc.stderr)
            run.save()
            if proc.returncode:
                raise RuntimeError(f'Deploy failed: {proc.stderr[-2500:]}')
            count = kathara_container_count(name)
            run.report['running_devices'] = count
            from Kathara.parser.netkit.LabParser import LabParser
            declared_links = len(LabParser().parse(str(path)).links)
            run.report['declared_collision_domains'] = declared_links
            if declared_links != config['collision_domains']:
                raise RuntimeError('Collision-domain declaration count mismatch')
            if count != config['devices']:
                raise RuntimeError(f'Expected {config["devices"]} devices, got {count}')
            run.stage('healthy-baseline', baseline, timeout=300)
            if config.get('mcp_probe'):
                from .mcp_smoke import run_smoke
                run.report['mcp_smoke'] = []
                try:
                    run_smoke(name, topology, config['mcp_probe'], run.report['mcp_smoke'])
                finally:
                    run.save()
                print('[MCP] diagnostic servers and inventory PASS', flush=True)
            if recipe:
                sc = scenarios[0]
                run.stage(sc.scenario_id + ':pre', sc.pre_check, timeout=60)
                for step in recipe['steps']:
                    action = step['action']
                    if action == 'check':
                        run.stage(sc.scenario_id + ':' + step['name'], [CheckLine(**c) for c in step['checks']], timeout=60)
                    elif action == 'mutate':
                        run.mutate(Injection(device=step['device'], action=step.get('name', 'partial repair'), command=step['command']))
                    else:
                        run.mutate(sc.injection if action == 'inject' else sc.recovery)
                run.stage(sc.scenario_id + ':recovered', sc.recovery_check, timeout=60)
                run.stage(sc.scenario_id + ':whole-baseline-restored', baseline, timeout=60)
                run.report['validated_scenarios'].append(sc.scenario_id)
            elif not baseline_only:
                for sc in scenarios:
                    run.stage(sc.scenario_id + ':pre', sc.pre_check, timeout=60)
                    run.mutate(sc.injection)
                    if sc.trigger is not None:
                        run.mutate(sc.trigger)
                    run.stage(sc.scenario_id + ':fault', sc.post_inject_check, timeout=120)
                    run.mutate(sc.injection)
                    if sc.trigger is not None:
                        run.mutate(sc.trigger)
                    run.stage(sc.scenario_id + ':repeated-injection', sc.post_inject_check, timeout=30)
                    run.mutate(sc.recovery)
                    if sc.trigger is not None:
                        run.mutate(sc.trigger)
                    run.stage(sc.scenario_id + ':recovered', sc.recovery_check, timeout=120)
                    run.stage(sc.scenario_id + ':whole-baseline-restored', baseline, timeout=60)
                    run.report['validated_scenarios'].append(sc.scenario_id)
                for stage in config.get('auxiliary', []):
                    run.stage(stage['name'] + ':pre', baseline, timeout=60)
                    run.mutate(Injection(**stage['injection']))
                    run.stage(stage['name'], [CheckLine(**c) for c in stage['checks']], timeout=120)
                    run.mutate(Injection(**stage['recovery']))
                    run.stage(stage['name'] + ':restored', [CheckLine(**c) for c in stage['recovery_checks']], timeout=120)
                    run.stage(stage['name'] + ':whole-baseline-restored', baseline, timeout=60)
            run.report['passed'] = True
        except BaseException as exc:
            import traceback
            run.report['error'] = f'{type(exc).__name__}: {exc}'
            run.report['error_traceback'] = traceback.format_exc()
            print(run.report['error'], file=sys.stderr, flush=True)
        finally:
            try:
                lclean(name)
                run.report['cleanup'] = dict(passed=True)
            except Exception as exc:
                run.report['cleanup'] = dict(passed=False, error=str(exc))
                run.report['passed'] = False
            run.report['finished_at'] = datetime.now(timezone.utc).isoformat()
            run.save()
            reports.append(out)
            print(f'Report: {out}', flush=True)
        if not run.report['passed']:
            return 1
    return 0


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--deploy-worker':
        deploy_worker(sys.argv[2], sys.argv[3])
        return 0
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('topology')
    ap.add_argument('--output', type=Path, default=ROOT / 'docs/validation/soft3888')
    ap.add_argument('--repeats', type=int, default=2)
    ap.add_argument('--baseline-only', action='store_true')
    ap.add_argument('--experiment', type=Path, help='Optional compound-fault recipe; runs separately from core cases')
    args = ap.parse_args()
    if args.repeats < 1:
        ap.error('--repeats must be positive')
    return validate(args.topology, args.output, args.repeats, args.baseline_only, args.experiment.resolve() if args.experiment else None)


if __name__ == '__main__':
    raise SystemExit(main())
