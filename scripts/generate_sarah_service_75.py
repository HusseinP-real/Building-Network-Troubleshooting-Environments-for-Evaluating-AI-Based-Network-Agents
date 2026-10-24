from pathlib import Path
import re

root = Path("Sarah_Service_75")
base = (root / "lab.conf.backup").read_text().rstrip()
lines = [base, ""]

def startup(name, commands):
    path = root / f"{name}.startup"
    path.write_text("#!/bin/sh\nset -e\n" + "\n".join(commands) + "\n")
    path.chmod(0o755)

# 8 additional routers.
# Each router connects a new client subnet to the existing CLIENT_LAN.
for i in range(3, 11):
    name = f"r{i}"
    lines.extend([
        f"{name}[0]=CLIENT_LAN",
        f"{name}[1]=SERVICE_SUBNET_{i}",
        "",
    ])
    startup(name, [
        f"ip addr show dev eth0 | grep -q '10.20.1.{i + 10}/24' || ip addr add 10.20.1.{i + 10}/24 dev eth0",
        f"ip addr show dev eth1 | grep -q '10.21.{i}.1/24' || ip addr add 10.21.{i}.1/24 dev eth1",
        "ip link set eth0 up",
        "ip link set eth1 up",
        "sysctl -w net.ipv4.ip_forward=1 || true",
        "ip route replace default via 10.20.1.1",
    ])

# 15 switches: each bridges a group of PCs to one router subnet.
# Each switch has one uplink and three client-facing interfaces.
for i in range(1, 16):
    name = f"s{i}"
    router_id = 3 + (i - 1) % 8
    lines.append(f"{name}[0]=SERVICE_SUBNET_{router_id}")

    for port in range(1, 4):
        lines.append(f"{name}[{port}]=SWITCH_{i}_{port}")

    lines.append("")

    commands = [
        "ip link add br0 type bridge",
        "ip link set br0 up",
    ]

    for port in range(4):
        commands.extend([
            f"ip link set eth{port} up",
            f"ip link set eth{port} master br0",
        ])

    startup(name, commands)

# 40 additional PCs.
for i in range(3, 43):
    name = f"pc{i}"
    switch_id = ((i - 3) % 15) + 1
    port = ((i - 3) // 15) + 1
    router_id = 3 + (switch_id - 1) % 8

    lines.append(f"{name}[0]=SWITCH_{switch_id}_{port}")

    startup(name, [
        f"ip addr add 10.21.{router_id}.{i + 20}/24 dev eth0",
        "ip link set eth0 up",
        f"ip route replace default via 10.21.{router_id}.1",
    ])

# 5 additional application servers.
for i in range(2, 7):
    name = f"app{i}"
    lines.append(f"{name}[0]=SERVICE_LAN")

    startup(name, [
        f"ip addr add 10.20.3.{i + 20}/24 dev eth0",
        "ip link set eth0 up",
        "ip route replace default via 10.20.3.1",
    ])

# Existing r1 must know routes to the new subnets.
r1_path = root / "r1.startup"
r1_original = Path("Sarah_Service_Network/r1.startup").read_text()

for i in range(3, 11):
    r1_original += (
        f"\nip route replace 10.21.{i}.0/24 "
        f"via 10.20.1.{i + 10}"
    )

r1_path.write_text(r1_original + "\n")
r1_path.chmod(0o755)

# Existing r2 must also know routes to the new subnets.
r2_path = root / "r2.startup"
r2_original = Path("Sarah_Service_Network/r2.startup").read_text()

for i in range(3, 11):
    r2_original += (
        f"\nip route replace 10.21.{i}.0/24 "
        "via 10.20.12.1"
    )

r2_path.write_text(r2_original + "\n")
r2_path.chmod(0o755)

(root / "lab.conf").write_text("\n".join(lines) + "\n")

interfaces = re.findall(
    r"^([A-Za-z0-9_-]+)\[(\d+)\]=",
    (root / "lab.conf").read_text(),
    re.M,
)

devices = {name for name, _ in interfaces}

print("Generated Sarah_Service_75")
print("Devices:", len(devices))
print("Interfaces:", len(interfaces))
print("Duplicate interfaces:", len(interfaces) - len(set(interfaces)))
