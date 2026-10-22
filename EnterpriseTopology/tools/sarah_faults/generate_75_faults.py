import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent / "fault_cases.json"

inventory = json.loads((ROOT / "inventory.json").read_text())

faults = []

for device, info in inventory["nodes"].items():

    if info["role"] != "router":
        continue

    for port in info["ports"]:

        if port["kind"] != "routed":
            continue

        interface = port["interface"]

        fault_id = f"sarah-fault-{len(faults) + 1:03}"

        faults.append({
            "id": fault_id,
            "device": device,
            "fault_type": "interface_down",
            "interface": interface,
            "inject": f"ip link set {interface} down",
            "repair": f"ip link set {interface} up",
            "ground_truth": {
                "device": device,
                "interface": interface,
                "root_cause": (
                    f"The routed interface {interface} "
                    f"on {device} is administratively down."
                )
            }
        })
# Generate 33 additional switch interface-down fault candidates

switch_faults_added = 0

for device, info in inventory["nodes"].items():

    if info["role"] != "switch":
        continue

    for port in info["ports"]:

        if switch_faults_added >= 33:
            break

        interface = port["interface"]

        fault_id = f"sarah-fault-{len(faults) + 1:03}"

        faults.append({
            "id": fault_id,
            "device": device,
            "fault_type": "switch_interface_down",
            "interface": interface,
            "inject": f"ip link set {interface} down",
            "repair": f"ip link set {interface} up",
            "ground_truth": {
                "device": device,
                "interface": interface,
                "root_cause": (
                    f"The switch interface {interface} on "
                    f"{device} is administratively down."
                )
            }
        })

        switch_faults_added += 1

    if switch_faults_added >= 33:
        break
    
OUTPUT.write_text(json.dumps(faults, indent=2))

print(f"Generated {len(faults)} candidate fault scenarios.")
print(f"Saved to {OUTPUT}")