#!/usr/bin/env python3
"""Read-only MCP diagnostics for the standalone enterprise Kathara lab."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import lab  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

NODES = json.loads((ROOT / "inventory.json").read_text())["nodes"]
KIND = os.environ.get("SADE_MCP_KIND", "base")
mcp = FastMCP("helper_server" if KIND == "helper" else "kathara_base_mcp_server")


def _query(node: str, command: str) -> dict:
    if node not in NODES:
        return {"node": node, "ok": False, "output": "unknown device"}
    ok, output = lab.execute(node, command, timeout=20)
    return {"node": node, "ok": ok, "output": output[:5000]}


def _safe_command(command: str) -> str | None:
    """Accept one read-only diagnostic command, without shell operators."""
    try:
        args = shlex.split(command)
    except ValueError:
        return None
    if not args or any(c in command for c in ";|&`$<>\n\r"):
        return None
    head = args[0]
    if head == "vtysh":
        if len(args) < 3 or len(args) % 2 != 1 or not all(
            args[i] == "-c" and args[i + 1].lower().startswith("show ")
            for i in range(1, len(args), 2)
        ):
            return None
    elif head == "ip":
        tail = [a for a in args[1:] if a not in ("-4", "-6", "-j", "-br", "-o", "-s")]
        if len(tail) < 2 or tail[0] not in ("link", "addr", "route", "neigh") or tail[1] not in ("show", "get", "list"):
            return None
    elif head == "iptables":
        if len(args) not in (2, 3) or args[1] not in ("-S", "-L") or (len(args) == 3 and args[2].startswith("-")):
            return None
    elif head == "bridge":
        if len(args) < 3 or args[1] not in ("link", "vlan", "fdb", "mdb") or args[2] != "show":
            return None
    elif head == "cat":
        if len(args) != 2 or not args[1].startswith(
            ("/proc/", "/sys/", "/etc/frr/", "/etc/keepalived/", "/var/log/")
        ):
            return None
    elif head == "curl":
        if len(args) != 2 or not args[1].startswith(("http://10.", "http://app.enterprise.test", "http://dmz.enterprise.test", "http://database.enterprise.test")):
            return None
    elif head == "ping":
        if len(args) != 4 or args[1] != "-c" or not args[2].isdigit() or not 1 <= int(args[2]) <= 4:
            return None
    elif head == "ss":
        if any(a in ("-K", "--kill") for a in args[1:]):
            return None
    elif head == "hostname":
        if len(args) != 1:
            return None
    elif head not in {"dig", "ps", "pgrep"}:
        return None
    return shlex.join(args)


def _reachability() -> dict:
    # These are known-allowed flows. Guest-to-internal and direct office-to-DB
    # are policy-denied even in a healthy lab, so they are not anomaly probes.
    probes = [
        ("staff", "application HTTP", "curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://10.30.10.10/"),
        ("office", "application HTTP", "curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://10.30.10.10/"),
        ("guest", "DMZ HTTP", "curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://10.40.10.10/"),
        ("ops", "database HTTP", "curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://10.30.20.10:8080/"),
        ("app", "database HTTP", "curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://10.30.20.10:8080/"),
    ]
    rows = []
    for node, target, command in probes:
        result = _query(node, command)
        rows.append({"src": node, "target": target, "expected_http": 200,
                     "observed": result["output"], "ok": result["ok"] and result["output"].strip() == "200"})
    return {"checks": rows, "all_expected": all(row["ok"] for row in rows)}


def _snapshot(nodes: list[str], command: str) -> list[dict]:
    return [_query(node, command) for node in nodes]


def _helper(name: str) -> dict:
    routers = [node for node, meta in NODES.items() if meta["role"] == "router"]
    if name in ("baseline_behavior", "safe_reachability"):
        return {"policy": "Guest internal traffic and office direct database traffic are denied by design.",
                "reachability": _reachability()}
    if name == "network_inventory":
        return {"roles": {role: [n for n, meta in NODES.items() if meta["role"] == role]
                          for role in ("router", "switch", "host")}}
    if name in ("ospf_snapshot", "infra_sweep"):
        result = {"router_links": _snapshot(routers, "ip -br link show"),
                  "ospf_neighbors": _snapshot(routers, "vtysh -c 'show ip ospf neighbor'"),
                  "vrrp_processes": _snapshot(["r3", "r4", "r5", "r6", "r7", "r8", "r9", "r10"], "pgrep -a keepalived")}
        if name == "infra_sweep":
            result["app_output_policy"] = _query("app", "iptables -S OUTPUT")
        return result
    if name in ("service_snapshot", "http_client_snapshot"):
        return {"reachability": _reachability(), "app_policy": _query("app", "iptables -S OUTPUT"),
                "app_process": _query("app", "ps -ef"), "database_process": _query("database", "ps -ef")}
    if name == "l2_snapshot":
        return {"bridges": _snapshot([n for n, meta in NODES.items() if meta["role"] == "switch"],
                                     "bridge link show")}
    return {"error": f"helper {name!r} is not available for this lab",
            "available": ["baseline_behavior", "safe_reachability", "network_inventory",
                          "ospf_snapshot", "infra_sweep", "service_snapshot",
                          "http_client_snapshot", "l2_snapshot"]}


if KIND == "helper":
    @mcp.tool()
    def list_helpers() -> str:
        return json.dumps(_helper("unsupported")["available"])

    @mcp.tool()
    def run_helper(script_name: str, args: list[str] | None = None) -> str:
        """Run a read-only network diagnostic sweep against the active lab."""
        if args:
            return json.dumps({"error": "this lab's helpers do not accept arguments"})
        return json.dumps(_helper(script_name))
else:
    @mcp.tool()
    def get_reachability() -> str:
        """Probe expected HTTP paths; policy-denied paths are omitted."""
        return json.dumps(_reachability())

    @mcp.tool()
    def list_devices() -> str:
        """List network device names and roles."""
        return json.dumps({name: meta["role"] for name, meta in NODES.items()})

    @mcp.tool()
    def exec_shell(host_name: str, command: str) -> str:
        """Run one read-only diagnostic command in a named device container."""
        safe = _safe_command(command)
        if safe is None:
            return json.dumps({"error": "Only one read-only diagnostic command is allowed."})
        return json.dumps(_query(host_name, safe))


if __name__ == "__main__":
    mcp.run(transport="stdio")
