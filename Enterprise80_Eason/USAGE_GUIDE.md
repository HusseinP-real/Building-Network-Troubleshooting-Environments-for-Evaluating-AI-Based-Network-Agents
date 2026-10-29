# Enterprise80 v2 usage guide

## Provisioning and validation scope

This version includes explicit provisioning scripts. Instead of relying on Kathara to execute `.startup` files automatically, the scripts enter each Docker container in the same lab, configure it, and check for errors. Static checks have been performed, but this version has not been run in the target Mac / Docker / Kathara environment. Runtime compatibility remains to be verified.

Run from the `Enterprise80_Eason` root directory, rather than an older version's directory:

```bash
chmod +x scripts/*.sh
kathara lclean -d topology_kathara/Enterprise80
kathara lstart --noterminals -d topology_kathara/Enterprise80
./scripts/provision.sh
sleep 35
./scripts/verify_healthy.sh
```

`lclean` cleans only Enterprise80. `--noterminals` avoids opening 80 terminal windows. After healthy validation passes, run:

```bash
./scripts/inject_fault.sh
./scripts/verify_fault.sh
./scripts/recover.sh
```

To stop and clean the lab:

```bash
kathara lclean -d topology_kathara/Enterprise80
```

To inspect an individual device:

```bash
./scripts/device.sh sydr1 ip -br addr
./scripts/device.sh sydr1 vtysh -c 'show ip ospf neighbor'
```

If `kathara connect sydr1` encounters a lab-name conflict, use `scripts/device.sh`. Provisioning stops at the device where an error occurs. Inspect the first ERROR and its surrounding logs before proceeding with fault injection.
