"""Optional read-only program sharing for vfs-backed custom labs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from contextlib import closing

_cache = Path('/workspace/.cache') if Path('/workspace').is_dir() else Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache')))
RUNTIME = Path(os.environ.get('FAULTBENCH_RUNTIME_DIR', str(_cache/'soft3888-runtime')))
_verified = set()


def tree_hash(directory):
    digest = hashlib.sha256()
    for p in sorted(directory.rglob('*')):
        rel = str(p.relative_to(directory)).encode()
        if p.is_symlink(): value = b'link:' + os.readlink(p).encode()
        elif p.is_file(): value = hashlib.sha256(p.read_bytes()).digest()
        else: continue
        digest.update(rel + b'\0' + value + b'\0')
    return digest.hexdigest()


def prepare_lab_runtime(lab):
    """Return image/mount provenance; never alter baseline protocol config."""
    extras_path=RUNTIME/'extra-images.json'
    extras=json.loads(extras_path.read_text()) if extras_path.exists() else {}
    candidates = [m for m in lab.machines.values() if m.get_image() in extras or m.get_image() in ('soft3888/host:bookworm-v1','soft3888/frr:10.5.3-v1')]
    if not candidates:
        return {}
    import docker
    mode = os.environ.get('FAULTBENCH_STORAGE_MODE', 'auto')
    if mode not in ('auto', 'shared', 'full'):
        raise ValueError('FAULTBENCH_STORAGE_MODE must be auto, shared or full')
    with closing(docker.from_env()) as client:
        shared = mode == 'shared' or (mode == 'auto' and client.info()['Driver'] == 'vfs')
        if not shared:
            return {'mode': 'full'}
        provenance = {}
        for machine in candidates:
            source=machine.get_image()
            role = source if source in extras else 'router' if source.startswith('soft3888/frr:') else 'host'
            root = Path(extras[source]['runtime_dir']) if source in extras else RUNTIME / role
            if not (root / 'manifest.json').is_file():
                raise RuntimeError('Run python tools/prepare_soft3888_runtime.py before a vfs deployment')
            data = json.loads((root / 'manifest.json').read_text())
            original = client.images.get(data['source'])
            device = client.images.get(data['device_image'])
            key = (role, data['source_id'], data['device_image_id'], data['usr_sha256'])
            if original.id != data['source_id'] or device.id != data['device_image_id']:
                raise RuntimeError('Shared runtime image ID mismatch')
            if key not in _verified:
                if tree_hash(root / 'usr') != data['usr_sha256']:
                    raise RuntimeError('Shared /usr integrity mismatch')
                _verified.add(key)
            machine.add_meta('image', data['device_image'])
            machine.add_meta('volume', f'{root / "usr"}|/usr|ro')
            provenance[role] = data
        return {'mode': 'shared-readonly-usr', 'roles': provenance}
