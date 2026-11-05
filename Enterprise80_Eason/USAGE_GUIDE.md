# Enterprise80 v2 — Usage Guide

## Important notes

This version includes explicit provisioning scripts. It does not rely on Kathara automatically executing `.startup` files: it enters each Docker container in the same lab, applies its configuration, and checks for errors. Static checks have been performed, but this version has not been run in your Mac / Docker / Kathara environment; compatibility must be verified locally.

Run from the `Enterprise80_Eason` root directory, not an older release directory:

```bash
chmod +x scripts/*.sh
kathara lclean -d topology_kathara/Enterprise80
kathara lstart --noterminals -d topology_kathara/Enterprise80
./scripts/provision.sh
sleep 35
./scripts/verify_healthy.sh
```

`lclean` cleans only Enterprise80, not other labs. `--noterminals` avoids opening 80 terminal windows. After verification reports PASS, run:

```bash
./scripts/inject_fault.sh
./scripts/verify_fault.sh
./scripts/recover.sh
```

When finished:

```bash
kathara lclean -d topology_kathara/Enterprise80
```

To inspect a device:

```bash
./scripts/device.sh sydr1 ip -br addr
./scripts/device.sh sydr1 vtysh -c 'show ip ospf neighbor'
```

If `kathara connect sydr1` encounters a lab-name conflict, use `scripts/device.sh`. Provisioning stops at the device that fails. Inspect the first ERROR and its surrounding logs before continuing; do not inject a fault after a provisioning failure.
