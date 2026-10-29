"""Compile operator-owned generic targets from pinned Git source; execute no lab scripts."""

import argparse
import hashlib
import io
import ipaddress
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def build(ref=None):
    saved_path = ROOT / "tools/generic_fault_targets.json"
    saved = json.loads(saved_path.read_text()) if saved_path.is_file() else {}
    native_ref = ref or saved.get("enterprise-75", {}).get(
        "source_commit", "origin/main"
    )
    catalog = json.loads((ROOT / "dashboard/topologies/catalog.json").read_text())
    specs = [
        ("enterprise-75", "EnterpriseTopology", ".", native_ref),
        ("enterprise-75-standalone", "EnterpriseTopology75", ".", native_ref),
    ]
    for row in catalog:
        snapshot = json.loads(
            (ROOT / "dashboard/topologies" / row["inventory"]).read_text()
        )
        sub = (
            "lab"
            if row["id"] in ("multi-as-isp", "jennie-enterprise-75")
            else "topology_kathara/Enterprise80"
            if row["id"] == "enterprise80-eason"
            else "."
        )
        specs.append(
            (row["id"], snapshot["source_path"], sub, snapshot["source_commit"])
        )
    archives = {}
    result = {}
    for key, base, sub, source_ref in specs:
        commit = subprocess.check_output(
            ["git", "rev-parse", source_ref], cwd=REPO, text=True
        ).strip()
        if commit not in archives:
            data = subprocess.check_output(["git", "archive", commit], cwd=REPO)
            with tarfile.open(fileobj=io.BytesIO(data)) as archive:
                archives[commit] = {
                    m.name: archive.extractfile(m).read()
                    for m in archive.getmembers()
                    if m.isfile()
                }
        files = archives[commit]
        folder = Path(base) / sub
        hosts = []
        for path, data in sorted(files.items()):
            if Path(path).parent != folder or not path.endswith(".startup"):
                continue
            text = data.decode()
            address = re.search(
                r"ip (?:-4 )?addr(?:ess)? (?:add|replace) ([\d./]+) dev (\w+)", text
            )
            gateway = re.search(r"ip route (?:add|replace) default via ([\d.]+)", text)
            if (
                not address
                or not gateway
                or re.search(r"ip_forward\s*=\s*1|type bridge|brctl|vtysh", text)
            ):
                continue
            hosts.append(
                {
                    "node": Path(path).stem,
                    "address": address[1],
                    "interface": address[2],
                    "gateway": gateway[1],
                }
            )
        # Prefer simple clients; retain deterministic source ordering and distinct subnets.
        hosts.sort(
            key=lambda h: (
                not bool(re.search(r"pc|client|_h\d|^a\d|^as.*h\d", h["node"])),
                h["node"],
            )
        )
        source = hosts[0]
        network = ipaddress.ip_interface(source["address"]).network
        remote = next(
            h for h in hosts if ipaddress.ip_interface(h["address"]).ip not in network
        )
        control = next(
            h for h in hosts if h["node"] not in (source["node"], remote["node"])
        )
        conf = files[str(folder / "lab.conf")]
        real_nodes = sorted(set(re.findall(rb"^([\w-]+)\[\d+\]", conf, re.MULTILINE)))
        result[key] = {
            "source_commit": commit,
            "lab_path": str(folder),
            "lab_conf_sha256": hashlib.sha256(conf).hexdigest(),
            "nodes": [n.decode() for n in real_nodes],
            "source": source,
            "remote": remote,
            "control": control,
            "wrong_gateway": "192.0.2.254",
            "startup_sha256": {
                h["node"]: hashlib.sha256(
                    files[str(folder / (h["node"] + ".startup"))]
                ).hexdigest()
                for h in (source, remote, control)
            },
        }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="Refresh native topology source revision")
    args = parser.parse_args()
    target = ROOT / "tools/generic_fault_targets.json"
    target.write_text(json.dumps(build(args.ref), indent=2) + "\n")
    print(f"Compiled {len(json.loads(target.read_text()))} topology mappings")
