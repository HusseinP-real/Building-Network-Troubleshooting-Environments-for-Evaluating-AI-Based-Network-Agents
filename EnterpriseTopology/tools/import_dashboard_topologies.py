"""Export teammate topology inventories from a Git ref without changing checkout."""

import argparse
import ast
import collections
import io
import json
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "EnterpriseTopology/dashboard/topologies"
# Jennie's candidate is not merged into main; retain an immutable source revision.
JENNIE_REF = "2acf8e01660a8c5721126c022af0ce97a57feb07"
SPECS = [
    (
        "p20-enterprise",
        "P20 Enterprise · 75 devices",
        "FaulT-Bench/topology_kathara/P20Enterprise",
        ".",
        [],
        "OSPF",
    ),
    (
        "sarah-enterprise-75",
        "Sarah Enterprise · 75 devices",
        "Sarah_Enterprise_75",
        ".",
        [],
        "Static routing",
    ),
    (
        "sarah-service-75",
        "Sarah Service · 75 devices",
        "Sarah_Service_75",
        ".",
        [],
        "Static routing · DNS · DHCP",
    ),
    (
        "jennie-enterprise-75",
        "Jennie Enterprise · 75 devices (candidate)",
        "Enterprise-SADE-W11-75",
        "lab",
        [],
        "OSPF · eBGP",
    ),
    (
        "datacenter-fabric",
        "Data Centre Fabric · 39 devices",
        "DatacenterFabric",
        ".",
        [
            "healthy",
            "uplink",
            "wrong-gateway",
            "backend-link",
            "withdrawal",
            "compound",
        ],
        "eBGP · ECMP",
    ),
    (
        "multi-as-isp",
        "Multi-AS ISP Backbone · 75 devices",
        "Multi-AS-ISP-Backbone-W11-75",
        "lab",
        [f"S{i:02}" for i in range(1, 9)],
        "IS-IS · OSPF · iBGP · eBGP",
    ),
    (
        "multisite",
        "Multi-Site Enterprise · 80 devices",
        "MultiSite_BGP_OSPF_Benchmark",
        ".",
        ["F01", "F02", "F03"],
        "OSPF · eBGP",
    ),
    (
        "jiayuan-75",
        "Jiayuan Enterprise · 75 devices",
        "FaulT-Bench/topology_kathara/Kath5_Jiayuan_75Devices",
        ".",
        [],
        "OSPF · EIGRP · DNS · HTTP",
    ),
    (
        "nika-92",
        "NIKA Clos · 92 devices",
        "FaulT-Bench/topology_kathara/NIKA_Clos_Jiayuan_92Devices",
        ".",
        [],
        "BGP · DHCP · DNS · HAProxy",
    ),
    (
        "missing-return-route",
        "Missing Return Route · micro lab",
        "kathara_scenario/missing_return_route",
        ".",
        ["missing-return-route"],
        "Static routing",
    ),
    (
        "abilene",
        "Abilene · IS-IS backbone",
        "SOFT3888_Abilene_YUMAng_Deliverable",
        ".",
        ["link-failure"],
        "IS-IS",
    ),
    (
        "kairos-enterprise",
        "Kairos Enterprise · 75 devices",
        "EnterpriseTopology_Kairos",
        ".",
        [],
        "OSPF · VRRP · VLAN · DNS",
    ),
    ("campus80-eason", "Eason Campus · 80 devices", "Campus80_Eason", ".", [], "OSPF"),
    (
        "enterprise80-eason",
        "Eason Enterprise · 80 devices",
        "Enterprise80_Eason",
        "topology_kathara/Enterprise80",
        [],
        "OSPF",
    ),
    (
        "kairos-kath3",
        "Kairos Kath3 · 32 devices",
        "FaulT-Bench/topology_kathara/Kath3_Kairos",
        ".",
        ["kairos_wrong_default_gateway"],
        "OSPF · VLAN · Static routing",
    ),
    (
        "sarah-enterprise",
        "Sarah Enterprise · 6 devices",
        "Sarah_Enterprise_Network",
        ".",
        ["SARAH-ENT-001"],
        "Static routing",
    ),
    (
        "sarah-service",
        "Sarah Service · 7 devices",
        "Sarah_Service_Network",
        ".",
        ["SARAH-SVC-001", "SARAH-SVC-002"],
        "Static routing · DNS · DHCP",
    ),
]


def fault_catalog(key, base, read):
    """Normalize operator metadata from the same archived revision as the map.

    No contributed Python or shell script is executed while importing a catalog.
    """
    rows = []
    if key == "kairos-enterprise":
        cases = json.loads(read(Path("EnterpriseTopology/tools/sade_cases.json")))
        tree = ast.parse(read(base / "lab.py"))
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "FAULTS"
                for target in statement.targets
            ):
                for name, (node, _, _) in ast.literal_eval(statement.value).items():
                    case = cases[name]
                    rows.append(
                        {
                            "id": name,
                            "kind": "fault",
                            "components": [],
                            "description": case["ground_truth"]["root_cause"],
                            "targets": [node],
                            "expected_impact": case["ticket"],
                            "case_ids": [],
                            "source_path": str(base / "lab.py"),
                        }
                    )
        path = base / "scenarios/kairos_dns_record/ground_truth.json"
        item = json.loads(read(path))
        rows.append(
            {
                "id": item["scenario_id"],
                "kind": "fault",
                "components": [],
                "description": item["root_cause"],
                "targets": [item["affected_device"]],
                "expected_impact": item["expected_diagnosis"],
                "case_ids": [],
                "source_path": str(path),
            }
        )
    elif key in ("campus80-eason", "enterprise80-eason"):
        path = base / "ground_truth.json"
        item = json.loads(read(path))
        fault = item["fault"]
        rows.append(
            {
                "id": item["scenario_id"],
                "kind": "fault",
                "components": [],
                "description": f"{fault['component']} stopped on {fault['device']} ({fault['type']}).",
                "targets": [fault["device"]],
                "expected_impact": "; ".join(
                    item.get("expected_symptoms", item.get("symptoms", []))
                ),
                "case_ids": [],
                "source_path": str(path),
            }
        )
    return rows


def export(ref):
    commit = subprocess.check_output(
        ["git", "rev-parse", ref], cwd=REPO, text=True
    ).strip()
    archive = subprocess.check_output(["git", "archive", commit], cwd=REPO)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        files = {
            m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()
        }

    main_files = files
    main_commit = commit
    candidate_archive = subprocess.check_output(
        ["git", "archive", JENNIE_REF], cwd=REPO
    )
    with tarfile.open(fileobj=io.BytesIO(candidate_archive)) as tar:
        candidate_files = {
            m.name: tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()
        }

    def read(path):
        return files.get(str(path), b"").decode("utf-8", errors="replace")

    catalog = []
    excluded = []
    outputs = {}
    for key, name, source, labpath, cases, protocols in SPECS:
        files = candidate_files if key == "jennie-enterprise-75" else main_files
        commit = JENNIE_REF if key == "jennie-enterprise-75" else main_commit
        base = Path(source)
        labbase = base if labpath == "." else base / labpath
        nodes = {}
        domains = collections.defaultdict(list)
        links = []
        roles = json.loads(read(base / "roles.json") or "{}")
        for node, port, domain in re.findall(
            r'^([\w-]+)\[(\d+)\]\s*=\s*["\x27]?([\w.-]+)',
            read(labbase / "lab.conf"),
            re.MULTILINE,
        ):
            startup = read(labbase / (node + ".startup"))
            config = read(labbase / node / "etc/frr/frr.conf")
            role = (
                "router"
                if node in roles.get("routers", [])
                or "router " in config
                or "vtysh" in startup
                or "ip_forward=1" in startup
                or "ip_forward = 1" in startup
                else "switch"
                if "brctl" in startup or "type bridge" in startup
                else "host"
            )
            nodes.setdefault(node, {"role": role, "ports": []})
            domains[domain].append({"node": node, "interface": "eth" + port})
        if key == "datacenter-fabric":
            original = json.loads(read(base / "inventory.json"))
            nodes = original["nodes"]
            links = original["links"]
            for n in nodes.values():
                n["source_role"] = n["role"]
                n["role"] = {
                    "spine": "router",
                    "leaf": "router",
                    "server": "host",
                    "client": "host",
                }.get(n["role"], n["role"])
        elif key == "abilene":
            root = ET.fromstring(files[str(base / "topology/network.xml")])
            ns = {"n": "http://sndlib.zib.de/network"}
            nodes = {
                n.attrib["id"]: {"role": "router", "ports": []}
                for n in root.findall(".//n:networkStructure/n:nodes/n:node", ns)
            }
            for link in root.findall(".//n:networkStructure/n:links/n:link", ns):
                a = link.find("n:source", ns).text
                b = link.find("n:target", ns).text
                links.append(
                    {
                        "name": link.attrib["id"],
                        "kind": "routed",
                        "endpoints": [
                            {"node": a, "interface": link.attrib["id"]},
                            {"node": b, "interface": link.attrib["id"]},
                        ],
                    }
                )
        else:
            for domain, endpoints in domains.items():
                # A shared collision domain is a LAN, not a fabricated mesh of direct wires.
                if len(endpoints) > 2:
                    hub = "lan:" + domain
                    nodes[hub] = {
                        "role": "switch",
                        "source_role": "shared LAN",
                        "virtual": True,
                        "ports": [],
                    }
                    for i, endpoint in enumerate(endpoints):
                        links.append(
                            {
                                "name": domain + ":" + str(i),
                                "kind": "lan",
                                "endpoints": [
                                    endpoint,
                                    {"node": hub, "interface": "port" + str(i)},
                                ],
                            }
                        )
                elif len(endpoints) == 2:
                    links.append(
                        {"name": domain, "kind": "routed", "endpoints": endpoints}
                    )
        device_count = sum(not n.get("virtual") for n in nodes.values())
        if device_count < 75:
            excluded.append(
                {
                    "id": key,
                    "name": name,
                    "source_path": source,
                    "source_commit": commit,
                    "device_count": device_count,
                    "reason": "Below the dashboard minimum of 75 real devices.",
                }
            )
            print(key, "excluded:", device_count, "devices (minimum 75)")
            continue
        saved_ports = {
            name: {p["interface"]: p for p in n.get("ports", [])}
            for name, n in nodes.items()
        }
        for n in nodes.values():
            n["ports"] = []
        for link in links:
            a, b = link["endpoints"]
            for own, peer in [(a, b), (b, a)]:
                port = {
                    **saved_ports.get(own["node"], {}).get(own["interface"], {}),
                    "interface": own["interface"],
                    "peer": peer["node"],
                    "kind": link["kind"],
                    "link": link["name"],
                }
                startup = read(labbase / (own["node"] + ".startup"))
                addresses = re.findall(
                    r"ip (?:-4 )?addr(?:ess)? (?:add|replace) ([\d./]+) dev "
                    + re.escape(own["interface"])
                    + r"\b",
                    startup,
                )
                if addresses:
                    port["address"] = addresses[0]
                nodes[own["node"]]["ports"].append(port)
        if key in ("jiayuan-75", "nika-92"):
            folder = "jiayuan75_Q" if key == "jiayuan-75" else "nika92_Q"
            cases = [
                Path(p).stem
                for p in files
                if p.startswith("FaulT-Bench/dataset/" + folder + "/custom/")
                and p.endswith(".txt")
            ]
        faults = fault_catalog(key, base, read)
        if faults:
            cases = [row["id"] for row in faults]
        data = {
            "nodes": nodes,
            "links": links,
            "layout": "generic",
            "protocols": protocols,
            "source_path": source,
            "source_commit": commit,
            "scenarios": cases,
            "scenario_count": len(cases),
            "fault_catalog": faults,
            "evaluation_enabled": False,
            "note": "Imported topology and operator fault catalog · runtime and automatic evaluation adapters pending",
            "health": None,
        }
        assert nodes and links, source
        outputs[key + ".json"] = data
        catalog.append(
            {
                "id": key,
                "name": name,
                "inventory": key + ".json",
                "scenario_count": len(cases),
                "evaluation_enabled": False,
            }
        )
        print(
            key,
            sum(not n.get("virtual") for n in nodes.values()),
            "devices",
            len(links),
            "drawn edges",
        )
    # Finish parsing before touching saved snapshots, so a bad source cannot leave a
    # partially refreshed catalog. Never delete unrelated or standalone inventories.
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, data in outputs.items():
        (OUT / filename).write_text(json.dumps(data, indent=2) + "\n")
    for row in excluded:
        (OUT / (row["id"] + ".json")).unlink(missing_ok=True)
    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    (OUT / "excluded.json").write_text(json.dumps(excluded, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ref", default="origin/main")
    export(parser.parse_args().ref)
