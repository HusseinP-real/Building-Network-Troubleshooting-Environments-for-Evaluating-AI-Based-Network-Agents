"""Capture real code/image provenance for a model run without credential values."""
import hashlib,json,subprocess
from pathlib import Path
from contextlib import closing
from .paths import ROOT,KATH_BASE,SADE_REPO
from .lab import _lab_filters

def snapshot_runtime(topology,scenario_path):
    import docker
    commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True)
    source=KATH_BASE/topology
    files={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and p.suffix!='.md' and '__pycache__' not in p.parts and 'shared' not in p.parts} if source.exists() else {}
    package=Path(__file__).parent
    harness={str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file() and p.suffix in ('.py','.json')}
    dependency_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=SADE_REPO,capture_output=True,text=True)
    nika_source=SADE_REPO/'src/nika'
    reference={str(p.relative_to(nika_source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in nika_source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    with closing(docker.from_env()) as client:
        containers=client.containers.list(filters=_lab_filters(topology))
        if not containers:raise RuntimeError('Cannot record runtime provenance: no named lab containers')
        images=sorted({container.image.id for container in containers})
        shared={}
        for container in containers:
            for mount in container.attrs.get('Mounts',[]):
                if mount.get('Destination')!='/usr' or mount.get('RW',True):continue
                receipt=Path(mount['Source']).parent/'manifest.json'
                if not receipt.is_file():raise RuntimeError('Shared program mount has no provenance receipt')
                data=json.loads(receipt.read_text())
                if data['device_image_id']!=container.image.id:raise RuntimeError('Shared program receipt does not match running image')
                shared[mount['Source']]={k:data[k] for k in ('source','source_id','device_image','device_image_id','usr_sha256')}
        return dict(git_commit=commit.stdout.strip() if commit.returncode==0 else None,sade_commit=dependency_commit.stdout.strip() if dependency_commit.returncode==0 else None,nika_source_sha256=reference,scenario_sha256=hashlib.sha256(scenario_path.read_bytes()).hexdigest(),topology_configuration_sha256=files,harness_sha256=harness,running_image_ids=images,shared_program_receipts=shared,running_devices=len(containers),docker_version=client.version()['Version'],storage_driver=client.info()['Driver'])
