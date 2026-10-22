#!/usr/bin/env python3
"""Prepare shared read-only /usr trees for Docker's copy-heavy vfs driver.

All bytes come from the already-built, verified local lab images. Importing
only the remaining root filesystem keeps each device's /etc,/var,/run writable
and independent. No host directory other than the explicit runtime cache is
mounted. Use normal full images on overlay2 machines.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone

_cache = Path('/workspace/.cache') if Path('/workspace').is_dir() else Path(os.environ.get('XDG_CACHE_HOME', str(Path.home()/'.cache')))
RUNTIME = Path(os.environ.get('FAULTBENCH_RUNTIME_DIR', str(_cache/'soft3888-runtime')))

def tree_hash(directory):
    digest=hashlib.sha256()
    for p in sorted(directory.rglob('*')):
        rel=str(p.relative_to(directory)).encode()
        if p.is_symlink(): value=b'link:'+os.readlink(p).encode()
        elif p.is_file(): value=hashlib.sha256(p.read_bytes()).digest()
        else: continue
        digest.update(rel+b'\0'+value+b'\0')
    return digest.hexdigest()

def prepare_image(client,source,target,root):
    image=client.images.get(source)
    stamp=root/'manifest.json'
    if stamp.exists():
        data=json.loads(stamp.read_text())
        if data['source_id']!=image.id or data['usr_sha256']!=tree_hash(root/'usr'):
            raise RuntimeError(f'Runtime provenance changed; preserve/remove {root} explicitly before rebuilding')
        if client.images.get(target).id != data['device_image_id']:
            raise RuntimeError('Shared device image ID changed; preserve and review cache before rebuilding')
        print(f'Verified existing shared {source} runtime',flush=True)
        return data
    if root.exists():raise RuntimeError(f'Refusing to overwrite incomplete runtime {root}')
    root.mkdir()
    container=client.containers.create(source,command=['bash'],network_mode='none')
    try:
        # Docker performs its own archive extraction semantics for symlinks.
        subprocess.run(['docker','cp',f'{container.id}:/usr',str(root/'usr')],check=True)
        with tempfile.TemporaryDirectory(prefix='soft3888-rootfs-') as tmp:
            full=Path(tmp)/'full.tar';small=Path(tmp)/'device.tar'
            with full.open('wb') as f:
                for chunk in container.export():f.write(chunk)
            with tarfile.open(full,'r:') as src,tarfile.open(small,'w:') as dst:
                for member in src:
                    name=member.name.removeprefix('./')
                    if name=='usr' or name.startswith('usr/'):continue
                    dst.addfile(member,src.extractfile(member) if member.isfile() else None)
            subprocess.run(['docker','import','--change','CMD ["bash"]',str(small),target],check=True)
        data=dict(source=source,source_id=image.id,device_image=target,
                  device_image_id=client.images.get(target).id,
                  usr_sha256=tree_hash(root/'usr'),created_at=datetime.now(timezone.utc).isoformat())
        stamp.write_text(json.dumps(data,indent=2)+'\n')
        print(f'Prepared shared {source} runtime',flush=True)
    finally:container.remove(force=True)
    return data

def main():
    import argparse
    import docker
    from contextlib import closing
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image',action='append',default=[],help='Additional existing source image to share, preserving its programs')
    args=ap.parse_args()
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with closing(docker.from_env(timeout=180)) as client:
        manifest={}
        for role,source,target in [('host','soft3888/host:bookworm-v1','soft3888/host:shared-v1'),('router','soft3888/frr:10.5.3-v1','soft3888/frr:shared-v1')]:
            manifest[role]=prepare_image(client,source,target,RUNTIME/role)
        (RUNTIME/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        extras_path=RUNTIME/'extra-images.json'
        extras=json.loads(extras_path.read_text()) if extras_path.exists() else {}
        for source in args.image:
            label='source-'+hashlib.sha256(source.encode()).hexdigest()[:12]
            data=prepare_image(client,source,'soft3888/'+label+':shared-v1',RUNTIME/label)
            data['runtime_dir']=str(RUNTIME/label)
            extras[source]=data
            # Kathara's defaults omit :latest; both names identify the same image.
            if source.endswith(':latest'):extras[source[:-7]]=data
        if args.image:extras_path.write_text(json.dumps(extras,indent=2)+'\n')
    print(f'Runtime provenance: {RUNTIME / "manifest.json"}')

if __name__=='__main__':main()
