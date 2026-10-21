"""Explicit device roles for custom labs; preserve upstream SADE source files.

Metadata includes roles/names only, never fault labels or reference answers.
Legacy labs keep upstream inference and reachability sampling unchanged.
"""
from __future__ import annotations
import json
import asyncio
from collections import defaultdict
import os
import re
from pathlib import Path
from .paths import KATH_BASE


def role_path(api, topology=None):
    name=topology or os.environ.get("FAULTBENCH_INVENTORY_TOPOLOGY") or api.lab.name
    local=KATH_BASE/name/'roles.json'
    return local if local.exists() else Path(__file__).parent/'inventories'/(name+'.json')


def apply_roles(api, topology=None):
    path = role_path(api, topology)
    if not path.exists():
        return False
    roles = json.loads(path.read_text())
    declared = roles.get('routers', []) + roles.get('hosts', []) + roles.get('switches', [])
    declared += [d for group in roles.get('servers', {}).values() for d in group]
    if len(declared) != len(set(declared)) or set(declared) != set(api.lab.machines):
        raise ValueError(f'{path}: roles must classify each lab device exactly once')
    api.routers = sorted(roles.get('routers', []))
    api.hosts = sorted(roles.get('hosts', []))
    api.switches = sorted(roles.get('switches', []))
    api.servers = defaultdict(list, {key: sorted(value) for key, value in roles.get('servers', {}).items()})
    api.bmv2_switches, api.ovs_switches, api.sdn_controllers = [], [], []
    return True


def install_inventory_adapter():
    from nika.service.kathara.base_api import KatharaBaseAPI
    if getattr(KatharaBaseAPI.load_machines, '_faultbench_roles', False):
        return
    original = KatharaBaseAPI.load_machines
    original_reachability = KatharaBaseAPI._get_reachability_async
    original_hosts, original_base_hosts = KatharaBaseAPI.get_hosts, KatharaBaseAPI.get_base_hosts
    def load(self):
        if not apply_roles(self):
            original(self)
    load._faultbench_roles = True
    KatharaBaseAPI.load_machines = load
    async def reachability(self):
        if not role_path(self).exists():
            return await original_reachability(self)
        return await sampled_reachability(self)
    KatharaBaseAPI._get_reachability_async = reachability
    def hosts(self):
        return list(self.hosts) if apply_roles(self) else original_hosts(self)
    def base_hosts(self):
        if not apply_roles(self):
            return original_base_hosts(self)
        return sorted(self.hosts + [n for group in self.servers.values() for n in group])
    KatharaBaseAPI.get_hosts = hosts
    KatharaBaseAPI.get_base_hosts = base_hosts


def parse_ping_error_statistics(output):
    """Handle real iputils summaries, including +N errors; never infer loss from command failure."""
    match = re.search(
        r"^(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received,\s+"
        r"(?:\+\d+\s+errors?,\s+)?(\d+(?:\.\d+)?)%\s+packet loss"
        r"(?:,\s*time\s*(\d+)ms)?\s*$", output, re.MULTILINE)
    if not match:
        return None
    tx, rx = int(match[1]), int(match[2])
    loss = float(match[3])
    if tx <= 0 or not 0 <= rx <= tx or not 0 <= loss <= 100:
        return None
    if abs(loss - (tx-rx)*100/tx) > 1:
        return None
    return dict(tx=tx, rx=rx, loss_percent=loss,
                time_ms=float(match[4]) if match[4] else None,
                status='down' if rx == 0 else 'ok' if loss == 0 else 'unstable')


async def sampled_reachability(api):
    """Deterministic custom-lab probes with at most four concurrent execs.

    Preserve upstream results/status schema and its real ping evaluator, with
    a bounded fallback for actual iputils error-statistic summaries. This
    prevents unbounded probe fanout from starving routing timers on small hosts.
    """
    api.load_machines()
    roles = json.loads(role_path(api).read_text())
    names = sorted(set(api.hosts + [n for group in api.servers.values() for n in group]))
    destinations = roles.get('reachability_destinations', names[:2])
    if len(destinations) != len(set(destinations)) or not set(destinations) <= set(names):
        raise ValueError('Invalid reachability destinations in role metadata')
    semaphore = asyncio.Semaphore(4)
    async def address(name):
        async with semaphore:
            return name, await asyncio.to_thread(api.get_host_ip, name)
    addresses = dict(await asyncio.gather(*(address(n) for n in names)))
    async def probe(src, dst):
        async with semaphore:
            stats = await api._check_ping_success_async(src, addresses[dst])
            if isinstance(stats, dict) and stats.get('status') == 'unknown':
                # The pinned evaluator cannot parse "+N errors" before loss.
                # Reprobe with a deadline and parse real counts, retaining
                # unknown for timeouts, missing summaries or command errors.
                output = await api.exec_cmd_async(src, f'ping -n -q -c2 -W1 {addresses[dst]}')
                parsed = parse_ping_error_statistics(output)
                if parsed is not None:
                    stats = parsed
        stats = stats if isinstance(stats, dict) else {}
        return dict(src=src, dst=dst, dst_ip=addresses[dst],
            **{key: stats.get(key) for key in ('tx','rx','loss_percent','time_ms',
                'rtt_avg_ms','rtt_min_ms','rtt_max_ms','rtt_mdev_ms')},
            status=stats.get('status','unknown'))
    results = await asyncio.gather(*(probe(src,dst) for src in names for dst in destinations if src != dst))
    return json.dumps(dict(hosts=addresses, results=results,
                          sampling=dict(destinations=destinations, concurrency=4)), separators=(',',':'))
