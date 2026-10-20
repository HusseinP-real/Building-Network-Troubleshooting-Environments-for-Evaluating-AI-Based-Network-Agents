"""Fast device execution, scoped to containers from one Kathara lab and user.

Kathara still creates and cleans the lab. Use its parser to obtain the real lab
identity rather than guessing container names or selecting all Kathara devices.
"""
import json
from pathlib import Path
import shlex
import subprocess


def select_containers(records, lab_hash, user, expected):
    mapping = {}
    for record in records:
        labels = record['Config']['Labels']
        name = labels.get('name')
        if labels.get('app') != 'kathara' or labels.get('lab_hash') != lab_hash or labels.get('user') != user:
            raise RuntimeError('Docker returned a container outside the isolated lab')
        if name not in expected or name in mapping or not record['State']['Running']:
            raise RuntimeError(f'Unexpected, duplicate or stopped lab device: {name}')
        mapping[name] = record['Id']
    if set(mapping) != set(expected):
        raise RuntimeError('Docker device inventory does not match the lab specification')
    return mapping


class DockerLab:
    def __init__(self, path, nodes):
        from Kathara.parser.netkit.LabParser import LabParser
        from Kathara.utils import get_current_user_name
        self.path = Path(path)
        self.hash = LabParser.parse(str(self.path.resolve())).hash
        self.user = get_current_user_name()
        proc = subprocess.run(['docker', 'ps', '-q', '--filter', 'label=app=kathara',
                               '--filter', f'label=lab_hash={self.hash}', '--filter', f'label=user={self.user}'],
                              capture_output=True, text=True, timeout=30, check=True)
        identifiers = proc.stdout.split()
        if not identifiers:
            raise RuntimeError('No containers found for the new isolated lab')
        proc = subprocess.run(['docker', 'inspect', *identifiers], capture_output=True, text=True, timeout=30, check=True)
        self.containers = select_containers(json.loads(proc.stdout), self.hash, self.user, nodes)

    def exec(self, node, command):
        # Wait for Kathara's end-of-startup marker before any probe or mutation.
        wrapped = ('_p20_wait=0; while ! test -f /tmp/EOS; do '
                   '_p20_wait=$((_p20_wait+1)); '
                   'if test "$_p20_wait" -ge 30; then echo "startup timeout"; exit 124; fi; '
                   'sleep 1; done; exec sh -c ' + shlex.quote(command))
        proc = subprocess.run(['docker', 'exec', self.containers[node], 'sh', '-c', wrapped],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)
        return proc.returncode, proc.stdout.strip()
