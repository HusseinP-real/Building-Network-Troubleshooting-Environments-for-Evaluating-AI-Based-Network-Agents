from pathlib import Path

root = Path("Sarah_Enterprise_75")
lab_path = root / "lab.conf"

# Preserve the existing validated six-device topology.
lines = (root / "lab.conf.backup").read_text().splitlines()

# Additional routers: r3-r10 (8)
# Additional switches: s1-s15 (15)
# Additional PCs: pc4-pc45 (42)
# Additional servers: server2-server5 (4)
# Total = 6 + 8 + 15 + 42 + 4 = 75

def startup(name, commands):
    path = root / f"{name}.startup"
    path.write_text("#!/bin/sh\n" + "\n".join(commands) + "\n")
    path.chmod(0o755)

# Connect additional routers to the existing HR/Finance network.
for i in range(3, 11):
    name = f"r{i}"
    segment = f"ROUTER_{i}"
    lines.append(f"{name}[0]={segment}")
    lines.append(f"{name}[1]=HR")
    startup(name, [
        f"ip addr add 10.30.{i}.1/24 dev eth0",
        f"ip addr add 10.10.1.{i + 10}/24 dev eth1",
        "ip link set eth0 up",
        "ip link set eth1 up",
        "sysctl -w net.ipv4.ip_forward=1",
        "ip route replace default via 10.10.1.1",
    ])

# Add Linux bridge switches.
for i in range(1, 16):
    name = f"s{i}"
    segment = f"SWITCH_{i}"
    lines.append(f"{name}[0]={segment}")
    lines.append(f"{name}[1]=HR")
    startup(name, [
        "ip link set eth0 up",
        "ip link set eth1 up",
        "ip link add br0 type bridge",
        "ip link set eth0 master br0",
        "ip link set eth1 master br0",
        "ip link set br0 up",
    ])

# Add 42 PCs, distributed across switch segments.
for i in range(4, 46):
    name = f"pc{i}"
    switch_id = ((i - 4) % 15) + 1
    lines.append(f"{name}[0]=SWITCH_{switch_id}")
    startup(name, [
        f"ip addr add 10.10.1.{i + 30}/24 dev eth0",
        "ip link set eth0 up",
        "ip route replace default via 10.10.1.1",
    ])

# Add four additional servers.
for i in range(2, 6):
    name = f"server{i}"
    lines.append(f"{name}[0]=SERVER")
    startup(name, [
        f"ip addr add 10.10.3.{i + 10}/24 dev eth0",
        "ip link set eth0 up",
        "ip route replace default via 10.10.3.1",
    ])

lab_path.write_text("\n".join(lines) + "\n")
print("Generated Sarah_Enterprise_75")
print("Expected device count: 75")
