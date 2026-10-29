"""Scoped, reversible endpoint faults shared by thirteen Kathara topologies.

Operator-only module. Diagnostic MCP receives only the public inventory and scope.
No contributed injection script or browser-supplied command is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

from environment_guard import Lease, inherited

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parent
TARGETS = json.loads((PROJECT / "tools/generic_fault_targets.json").read_text())
FAMILIES = {
    "link_down": "Link / interface down",
    "wrong_gateway": "Incorrect default gateway",
    "route_blackhole": "Destination route blackhole",
    "traffic_filter": "ICMP traffic blocked",
    "healthy_control": "Healthy network",
}
VERSION = "generic-endpoint-v1"


def mapping(topology):
    if topology not in TARGETS:
        raise ValueError("Unknown topology")
    return TARGETS[topology]


def root(topology):
    return REPO / mapping(topology)["lab_path"]


def fingerprint(topology):
    digest = hashlib.sha256(json.dumps(mapping(topology), sort_keys=True).encode())
    digest.update(Path(__file__).read_bytes())
    return digest.hexdigest()


def support(topology):
    target = mapping(topology)
    folder = root(topology)
    checks = {
        "lab.conf": target["lab_conf_sha256"],
        **{
            node + ".startup": value for node, value in target["startup_sha256"].items()
        },
    }
    for name, expected in checks.items():
        file = folder / name
        if not file.is_file():
            return (
                False,
                f"Lab source unavailable: {target['lab_path']}/{name}. Restore the pinned source and deploy this lab first.",
            )
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            return (
                False,
                f"Lab source changed: {name}. Rebuild and validate the target mapping.",
            )
    return (
        True,
        "Generic adapter mapped. Validate the selected fault on the deployed lab before benchmarking.",
    )


def evidence_file(topology, family):
    if family not in FAMILIES:
        raise ValueError("Unknown generic fault")
    return root(topology) / "results/control" / f"generic-validation-{family}.json"


def validated(topology, family):
    try:
        evidence = json.loads(evidence_file(topology, family).read_text())
        return (
            support(topology)[0]
            and evidence.get("passed") is True
            and evidence.get("fingerprint") == fingerprint(topology)
        )
    except (OSError, ValueError):
        return False


def catalog(topology):
    target = mapping(topology)
    available, reason = support(topology)
    return [
        {
            "id": family,
            "family_id": family,
            "title": title,
            "generic": True,
            "kind": "healthy" if family == "healthy_control" else "fault",
            "components": [] if family == "healthy_control" else [family],
            "targets": []
            if family == "healthy_control"
            else [target["source"]["node"]],
            "description": title
            + (
                "; no network mutation."
                if family == "healthy_control"
                else f" on {target['source']['node']} ({target['source']['interface']})."
            ),
            "expected_impact": "Source-to-remote ICMP fails; independent control-to-remote ICMP stays healthy."
            if family != "healthy_control"
            else "Both source and control reach the remote endpoint.",
            "case_ids": [family],
            "execution_enabled": available,
            "evaluation_enabled": available and validated(topology, family),
            "validation_status": "validated"
            if validated(topology, family)
            else "pending",
            "support_reason": reason,
        }
        for family, title in FAMILIES.items()
    ]


class Adapter:
    def __init__(self, topology):
        self.trace = []
        self.topology = topology
        self.target = mapping(topology)
        self.ROOT = root(topology)
        self.source = self.target["source"]["node"]
        self.interface = self.target["source"]["interface"]
        self.destination = str(
            ipaddress.ip_interface(self.target["remote"]["address"]).ip
        )
        self.gateway = self.target["source"]["gateway"]
        self.wrong_gateway = self.target["wrong_gateway"]
        self.rule = f"-d {self.destination}/32 -p icmp -m comment --comment generic-benchmark-v1 -j DROP"
        self.FAULTS = {
            key: (self.source, "@inject:" + key, "@repair:" + key)
            for key in FAMILIES
            if key != "healthy_control"
        }

    def execute(self, node, command, timeout=35):
        if node not in self.target["nodes"]:
            return False, "Unknown device for selected topology"
        if command.startswith("@"):
            action, family = command[1:].split(":", 1)
            try:
                self.action(action, family)
                return True, f"{action} verified"
            except (RuntimeError, ValueError, OSError) as exc:
                return False, str(exc)
        marker = "__GENERIC_REMOTE_SUCCESS__"
        wrapped = f'( {command} ) && printf "\\n{marker}\\n"'
        try:
            result = subprocess.run(
                [
                    "kathara",
                    "exec",
                    "-d",
                    str(self.ROOT),
                    node,
                    "--",
                    "sh",
                    "-c",
                    wrapped,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            output = result.stdout + result.stderr
            ok = result.returncode == 0 and marker in output
            cleaned = output.replace(marker, "").strip()
            self.trace.append(
                {
                    "node": node,
                    "command": command,
                    "passed": ok,
                    "output": cleaned[:5000],
                }
            )
            return ok, cleaned
        except subprocess.TimeoutExpired:
            return False, f"Scoped command timed out after {timeout}s"

    def require(self, node, command):
        ok, output = self.execute(node, command)
        if not ok:
            raise RuntimeError(f"{node}: {command}: {output}")
        return output

    def ping(self, node, destination, succeeds=True):
        # ping returns 2 for a kernel route error. Accept only those explicit
        # network errors, after checking the actual injected state in action().
        command = f"output=$(ping -n -c 2 -W 2 {destination} 2>&1); rc=$?; "
        if succeeds:
            command += 'printf "%s\\n" "$output"; test "$rc" -eq 0'
        else:
            command += (
                'printf "%s\\n" "$output"; test "$rc" -eq 1 || '
                '{ test "$rc" -eq 2 && case "$output" in '
                '*"Network is unreachable"*|*"Network unreachable"*|*"No route to host"*|*"connect: Invalid argument"*) true ;; *) false ;; esac; }'
            )
        self.require(node, command)

    def baseline(self):
        available, reason = support(self.topology)
        if not available:
            raise RuntimeError(reason)
        actual = json.loads(
            self.require(self.source, f"ip -j -4 addr show dev {self.interface}")
        )
        address = str(ipaddress.ip_interface(self.target["source"]["address"]).ip)
        if not any(
            a["local"] == address for link in actual for a in link.get("addr_info", [])
        ):
            raise RuntimeError("Source address differs from pinned mapping")
        link = json.loads(
            self.require(self.source, f"ip -j link show dev {self.interface}")
        )[0]
        if "UP" not in link["flags"]:
            raise RuntimeError("Source interface is not administratively UP")
        route = self.require(self.source, "ip -4 route show default")
        # Only a single uncomplicated static endpoint default is supported. Never guess recovery.
        if not re.fullmatch(
            r"default via "
            + re.escape(self.gateway)
            + r" dev "
            + re.escape(self.interface)
            + r"(?: proto (?:static|boot))?(?: metric \d+)?",
            route,
        ):
            raise RuntimeError(
                f"Expected one simple endpoint default route; observed: {route}"
            )
        self.ping(self.source, self.gateway)
        self.ping(self.source, self.destination)
        self.ping(self.target["control"]["node"], self.destination)
        return route

    def check(self):
        try:
            self.baseline()
            return 0
        except (RuntimeError, ValueError, OSError) as exc:
            print(f"FAIL generic baseline: {exc}", flush=True)
            return 1

    def backup_path(self, family):
        if family not in self.FAULTS:
            raise ValueError("Unknown mutable fault")
        return self.ROOT / "results/control" / f"generic-original-{family}.json"

    def save(self, family):
        path = self.backup_path(family)
        if path.exists():
            raise RuntimeError(
                "An original-state backup exists; recover before reinjection"
            )
        original = self.baseline()
        if family == "route_blackhole":
            self.require(
                self.source,
                f'test -z "$(ip -4 route show exact {self.destination}/32)"',
            )
        if family == "traffic_filter":
            self.require(self.source, "iptables -S OUTPUT")
            # A pre-existing identical rule must never be deleted by our recovery.
            self.require(
                self.source,
                f'iptables -C OUTPUT {self.rule} >/dev/null 2>&1; rc=$?; test "$rc" -eq 1',
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(
                {"default_route": original, "fingerprint": fingerprint(self.topology)},
                stream,
            )
            stream.flush()
            os.fsync(stream.fileno())

    def repair_command(self, family):
        if family == "link_down":
            return f"ip link set dev {self.interface} up && ip route replace default via {self.gateway} dev {self.interface}"
        if family == "wrong_gateway":
            return f"ip route replace default via {self.gateway} dev {self.interface}"
        if family == "route_blackhole":
            return f"ip route del blackhole {self.destination}/32 metric 42760"
        return f"iptables -D OUTPUT {self.rule}"

    def action(self, action, family):
        if family not in self.FAULTS:
            raise ValueError("Unknown fault")
        if action == "inject":
            self.save(family)
            commands = {
                "link_down": f"ip link set dev {self.interface} down",
                "wrong_gateway": f"ip route replace default via {self.wrong_gateway} dev {self.interface} onlink",
                "route_blackhole": f"ip route add blackhole {self.destination}/32 metric 42760",
                "traffic_filter": f"iptables -I OUTPUT 1 {self.rule}",
            }
            self.require(self.source, commands[family])
        elif action == "repair":
            path = self.backup_path(family)
            if not path.exists():
                # Failure before saving never performed a mutation.
                self.baseline()
                return
            state = json.loads(path.read_text())
            if state["fingerprint"] != fingerprint(self.topology):
                raise RuntimeError(
                    "Recovery mapping changed; inspect original state before repair"
                )
            command = self.repair_command(family)
            if family in ("link_down", "wrong_gateway"):
                command = "ip route replace " + shlex.join(
                    shlex.split(state["default_route"])
                )
                if family == "link_down":
                    command = f"ip link set dev {self.interface} up && " + command
            if family == "route_blackhole":
                command = f'if ip -4 route show exact {self.destination}/32 | grep -q "^blackhole .*metric 42760"; then {command}; fi'
            if family == "traffic_filter":
                command = (
                    f"if iptables -C OUTPUT {self.rule} 2>/dev/null; then {command}; fi"
                )
            self.require(self.source, command)
        elif action in ("verify", "repaired"):
            repaired = action == "repaired"
            checks = {
                "link_down": f"ip -j link show dev {self.interface}",
                "wrong_gateway": "ip -4 route show default",
                "route_blackhole": f"ip -4 route show exact {self.destination}/32",
                "traffic_filter": "iptables -S OUTPUT",
            }
            output = self.require(self.source, checks[family])
            if family == "link_down":
                faulty = "UP" not in json.loads(output)[0]["flags"]
            elif family == "wrong_gateway":
                faulty = f"via {self.wrong_gateway} " in output
                if repaired and f"via {self.gateway} " not in output:
                    raise RuntimeError("Original gateway not restored")
            elif family == "route_blackhole":
                faulty = (
                    "blackhole " + self.destination in output
                    and "metric 42760" in output
                )
            else:
                faulty = "generic-benchmark-v1" in output
            if faulty == repaired:
                raise RuntimeError("Mutation state does not match expected phase")
            self.ping(self.source, self.destination, succeeds=repaired)
            self.ping(self.target["control"]["node"], self.destination)
            if repaired:
                self.baseline()
                self.backup_path(family).unlink(missing_ok=True)
            elif family != "link_down":
                self.ping(self.source, self.gateway)
        else:
            raise ValueError("Unknown action")

    def cases(self):
        rows = {}
        for family, title in FAMILIES.items():
            healthy = family == "healthy_control"
            resource = (
                f"interface/{self.source}/{self.interface}"
                if family == "link_down"
                else f"routing/{self.source}/default"
                if family == "wrong_gateway"
                else f"routing/{self.source}/blackhole"
                if family == "route_blackhole"
                else f"policy/{self.source}/output-icmp"
            )
            rows[family] = {
                "ticket": f"Please investigate a reported connectivity problem from {self.source} to {self.destination}. Verify the report independently and identify any actual fault; do not repair the environment.",
                "fault": None if healthy else family,
                "category": "healthy" if healthy else "accurate",
                "inject_check": [self.source, "@verify:" + family],
                "repair_check": [self.source, "@repaired:" + family],
                "ground_truth": {
                    "is_anomaly": not healthy,
                    "resource_id": "none" if healthy else resource,
                    "fault_type": "none" if healthy else family,
                    "device": "none" if healthy else self.source,
                    "root_cause": "No fault; both configured paths are healthy."
                    if healthy
                    else title
                    + f" on {self.source} causes the verified source-path failure while the control path remains healthy.",
                    "remediation": []
                    if healthy
                    else [
                        {"device": self.source, "command": self.repair_command(family)}
                    ],
                },
            }
        return rows


def validate(topology, family):
    adapter = Adapter(topology)
    lease = Lease(adapter.ROOT)
    owned = not inherited(adapter.ROOT)
    if owned:
        lease.acquire()
    report = {
        "fingerprint": fingerprint(topology),
        "topology_id": topology,
        "family_id": family,
        "passed": False,
        "timestamp": time.time(),
    }
    changed = False
    try:
        if family not in FAMILIES:
            raise ValueError("Unknown fault")
        if lease.read()["pending"]:
            raise RuntimeError("Recover existing pending faults first")
        adapter.baseline()
        if family != "healthy_control":
            lease.mark(family)
            changed = True
            adapter.action("inject", family)
            adapter.action("verify", family)
        report["fault_verified"] = True
    except (RuntimeError, ValueError, OSError) as exc:
        report["error"] = str(exc)
    finally:
        try:
            if changed:
                adapter.action("repair", family)
                adapter.action("repaired", family)
                lease.clear([family])
            adapter.baseline()
            report["recovery_verified"] = True
        except (RuntimeError, ValueError, OSError) as exc:
            report["recovery_error"] = str(exc)
        report["checks"] = adapter.trace
        report["passed"] = bool(
            report.get("fault_verified") and report.get("recovery_verified")
        )
        path = evidence_file(topology, family)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(report, indent=2) + "\n")
        temp.replace(path)
        if owned:
            lease.release()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topology", choices=TARGETS)
    parser.add_argument("family", choices=FAMILIES)
    args = parser.parse_args()
    result = validate(args.topology, args.family)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
