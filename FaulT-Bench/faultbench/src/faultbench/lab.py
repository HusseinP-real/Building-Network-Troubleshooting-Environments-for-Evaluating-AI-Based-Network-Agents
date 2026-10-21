"""Kathara lab lifecycle wrappers.

Uses the Kathara Python API (NOT the CLI `kathara lstart`) so we can
explicitly set `lab.name = <topology>`. NIKA's MCP servers find the lab
via `Kathara.get_instance().get_lab_from_api(lab_name=...)` — that only
works for labs registered with a known name; CLI-started labs get an
auto-generated name the MCP servers cannot discover.
"""
from __future__ import annotations

import os
import shutil
import re
from contextlib import closing
from pathlib import Path

from func_timeout import FunctionTimedOut, func_timeout
from Kathara.manager.Kathara import Kathara
from Kathara.parser.netkit.LabParser import LabParser

from .paths import KATH_BASE, SADE_REPO


def lab_dir(topology: str) -> Path:
    """Map 'Kath3' -> the lab directory path."""
    return KATH_BASE / topology


def _is_nika_topology(topology: str) -> bool:
    """True if `topology` is a programmatic NIKA net_env (not a Kath* dir lab).

    NIKA labs are built in Python (nika.net_env) rather than parsed from a
    lab.conf dir, so they take a different deploy path. Imported lazily so the
    pipeline still runs Kath-only without nika installed.
    """
    os.environ.setdefault("BASE_DIR", str(SADE_REPO))
    try:
        from nika.net_env.net_env_pool import list_all_net_envs
        return topology in list_all_net_envs()
    except Exception:
        return False


def _kathara() -> Kathara:
    return Kathara.get_instance()


def check_storage_budget(lab):
    import docker
    with closing(docker.from_env()) as client:
        size=sum(client.images.get(m.get_image()).attrs['Size'] for m in lab.machines.values())
        free=shutil.disk_usage(KATH_BASE).free
        if client.info()['Driver']=='vfs' and size*3>free:
            raise RuntimeError(f'Insufficient vfs disk budget: device image sum {size} bytes, free {free}. Prepare verified shared source images with tools/prepare_soft3888_runtime.py --image IMAGE, or use an overlay-backed host.')


def lstart(topology: str) -> int:
    """Boot a Kathara lab via Python API with `lab.name = topology`.

    Always lclean first to clear any stale Docker state from a previous
    crashed run (avoids MachineAlreadyExistsError). Returns the lab's device
    count (= the expected running-container count) so the caller can confirm
    the deployment is complete.
    """
    if _is_nika_topology(topology):
        return _lstart_nika(topology)
    cwd = lab_dir(topology)
    if not cwd.exists():
        raise FileNotFoundError(f"Topology {topology} not found at {cwd}")
    from Kathara.setting.Setting import Setting
    Setting.get_instance().open_terminals = False
    lab = LabParser().parse(str(cwd))
    lab.name = topology
    lab.general_options.update({"open_terminals": False, "hosthome_mount": False, "shared_mount": False})
    from .runtime import prepare_lab_runtime
    prepare_lab_runtime(lab)
    check_storage_budget(lab)
    lclean(topology)
    old_umask = os.umask(0o022)
    try:
        _kathara().deploy_lab(lab)
    finally:
        os.umask(old_umask)
    return len(lab.machines)


def prepare_nika_startup_runtime(lab):
    """Adapt service startup in the generated in-memory Lab; preserve reference files."""
    overrides=[]
    for path in lab.fs.walk.files('/'):
        if not path.endswith('.startup'):continue
        text=lab.fs.readtext(path)
        updated=re.sub(r'(?m)^([ \t]*)systemctl\s+start\s+frr[ \t]*$',r'\1/etc/init.d/frr start\n\1vtysh -b',text)
        updated=re.sub(r'(?m)^([ \t]*)systemctl\s+start\s+named[ \t]*$',r'\1/etc/init.d/named start',updated)
        if updated!=text:
            lab.fs.writetext(path,updated)
            overrides.append(dict(path=path,change='Use init.d for declared FRR/named startup; replay FRR configuration with vtysh -b',protocol_configuration_changed=False))
    return overrides


def _lstart_nika(topology: str) -> int:
    """Deploy a programmatic NIKA net_env under Kathara, named `topology`.

    The NIKA env builds its own Lab (already named LAB_NAME == topology), so we
    lclean stale state and deploy it. Everything downstream (exec, checks,
    agents, teardown) then works by lab_name exactly like a Kath lab.
    """
    from nika.net_env.net_env_pool import get_net_env_instance
    env = get_net_env_instance(topology)
    prepare_nika_startup_runtime(env.lab)
    env.lab.general_options.update(open_terminals=False,hosthome_mount=False,shared_mount=False)
    from Kathara.setting.Setting import Setting
    settings=Setting.get_instance()
    settings.open_terminals=False
    settings.hosthome_mount=False
    settings.shared_mount=False
    from .runtime import prepare_lab_runtime
    prepare_lab_runtime(env.lab)
    check_storage_budget(env.lab)
    lclean(topology)
    previous_umask=os.umask(0o022)
    try:
        _kathara().deploy_lab(lab=env.lab)
    finally:
        os.umask(previous_umask)
    return len(env.lab.machines)


def _lab_filters(topology: str) -> dict:
    from Kathara import utils
    return {"label": ["app=kathara", "lab_hash=" + utils.generate_urlsafe_hash(topology),
                      "user=" + utils.get_current_user_name()]}


def kathara_container_count(topology: str) -> int:
    """Count only running containers in the named lab, never other experiments."""
    import docker
    with closing(docker.from_env()) as client:
        return len(client.containers.list(filters=_lab_filters(topology)))


def lclean(topology: str, timeout: int = 300) -> None:
    """Undeploy only this lab, including leftovers from a partial deployment."""
    import docker
    filters = _lab_filters(topology)
    with closing(docker.from_env(timeout=timeout)) as client:
        containers = client.containers.list(all=True, filters=filters)
        networks = client.networks.list(filters=filters)
        if not containers and not networks:
            return
        try:
            _kathara().undeploy_lab(lab_name=topology)
        except Exception:
            # Only resources with the exact lab hash and user are eligible.
            for container in client.containers.list(all=True, filters=filters):
                container.remove(force=True)
        for network in client.networks.list(filters=filters):
            network.reload()
            if network.attrs.get("Containers"):
                raise RuntimeError(f"Refusing to remove occupied lab network {network.id}")
            network.remove()
        if client.containers.list(all=True, filters=filters) or client.networks.list(filters=filters):
            raise RuntimeError(f"Lab cleanup incomplete: {topology}")


def kathara_exec(topology: str, device: str, command: str,
                 timeout: int = 30) -> tuple[int, str]:
    """Use Kathara's non-streaming (stdout, stderr, exit_code) API contract.

    Never retry a potentially mutating command after an ambiguous API failure.
    """
    def collect() -> tuple[int, str]:
        stdout, stderr, rc = _kathara().exec(
            machine_name=device, command=["/bin/sh", "-c", command],
            lab_name=topology, stream=False,
        )
        def decode(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
        return int(rc), (decode(stdout) + decode(stderr)).strip()
    try:
        return func_timeout(timeout, collect)
    except FunctionTimedOut:
        return 124, f"[TIMEOUT] command exceeded {timeout}s on {device}"
    except Exception as exc:
        return 125, f"[exec error] {type(exc).__name__}: {exc}"
