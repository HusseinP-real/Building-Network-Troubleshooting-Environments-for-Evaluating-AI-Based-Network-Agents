#!/usr/bin/env python3
"""Record versions and inspect live mount/port isolation for this named lab."""
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import sys
import docker

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lab


def record():
    client=docker.from_env()
    image=client.images.get(lab.inventory()['image'])
    machines=lab.manager().get_machines_api_objects(lab_name=lab.NAME)
    expected=len(lab.inventory()['nodes'])
    assert len(machines)==expected, f'Expected {expected} devices, got {len(machines)}'
    for machine in machines:
        machine.reload()
    ok,frr=lab.execute('leaf1', "vtysh -c 'show version'")
    assert ok, frr
    mounts=[dict(device=c.labels.get('name',c.name),type=m['Type'],destination=m['Destination']) for c in machines for m in c.attrs.get('Mounts',[])]
    # The base image declares anonymous volumes at /hosthome and /shared.
    # A volume at that destination is not a bind mount of the user's home.
    home=any(m['type']=='bind' and m['destination']=='/hosthome' for m in mounts)
    shared=any(m['type']=='bind' and m['destination']=='/shared' for m in mounts)
    published=any(any(v for v in c.attrs.get('NetworkSettings',{}).get('Ports',{}).values()) for c in machines)
    report=dict(validated_at=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),kathara=importlib.metadata.version('Kathara'),docker=client.version()['Version'],docker_memory_bytes=client.info()['MemTotal'],docker_cpus=client.info()['NCPU'],image_id=image.id,image_repo_digests=image.attrs.get('RepoDigests'),running_devices=len(machines),frr_version=frr,inventory_sha256=hashlib.sha256((lab.ROOT/'inventory.json').read_bytes()).hexdigest(),host_home_mounted=home,shared_mounted=shared,published_ports=published,mounts=mounts)
    (lab.ROOT/'results/environment.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not home and not shared and not published, 'Unexpected host bind mount or published port'
    print(f'Environment recorded: {expected} devices, no host-home/shared bind mounts or published ports')


if __name__=='__main__':
    record()
