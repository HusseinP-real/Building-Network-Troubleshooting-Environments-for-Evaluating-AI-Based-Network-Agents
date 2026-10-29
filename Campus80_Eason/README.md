# Campus80: complete topology and OSPF fault injection

This package preserves the 80-node topology and startup configuration from campus80_fixed.zip and adds a reproducible healthy → fault → recovery workflow. The scripts use the Python 3 standard library. The host requires Docker and Kathara; container images require FRR, ip, ping, pgrep, and pkill.

## Sharing a fault family across two topologies

Campus80 uses the same `routing_daemon_down` family as Enterprise80_Final_v2: stop watchfrr to prevent automatic restart, then stop the gateway's ospfd. Interfaces, addresses, zebra, and containers remain running.

| Item | Enterprise80 v2 | Campus80 |
|---|---|---|
| Fault device | sydr1 | r01 |
| Fault component | ospfd | ospfd |
| Affected LAN | 10.10.10.0/24 | 10.10.1.0/24 |
| Affected endpoints | sydpc1–sydpc9 | pc01–pc05 |
| Local gateway | 10.10.10.1 | 10.10.1.1 |
| Remote probe | web1 | srv01, 10.10.3.100 |

These are two instances of one fault family on different topologies. Device and IP parameters differ, so Enterprise's hardcoded scripts cannot be reused unchanged. The shared family supports cross-topology diagnosis comparisons but does not establish multiple fault families or equal difficulty. Other paths reconverge when r01, which also forwards traffic, stops participating in OSPF.

## Network completeness and scope

The package includes 12 routers, 60 PCs, 8 servers, 20 /30 links, 12 /24 LANs, host default routes, and OSPF area 0 configuration. Static consistency checks passed. Use the local `verify_healthy.sh` result to determine whether the running baseline works. HTTP is an optional startup service; acceptance covers IPv4/ICMP and OSPF rather than HTTP. External connectivity, DNS, and DHCP are not implemented.

## Use an existing Campus80 deployment

Enter this directory after extraction. If the same Campus80 deployment is already running, run:

```bash
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
# Diagnose and record results while the fault is active, then recover:
bash scripts/recover.sh
```

Injection first verifies the complete healthy baseline and stops if it fails. A successful injection remains active until recovery. If injection fails partway through, some processes may already have stopped; run recovery. Repeating injection is not a recovery method.

## Start from a new directory

Only when Campus80 is not already running:

```bash
kathara lstart -d . --noterminals
# Wait for startup and OSPF convergence; busy hosts may need longer.
sleep 90
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
bash scripts/recover.sh
```

If Campus80 is running from an older directory, keep using that deployment or stop it from its original directory before starting the new one. Do not mix deployments. Enterprise and other labs can run concurrently; these scripts match only the selected Campus containers.

## Run a complete experiment on an existing deployment

```bash
bash scripts/run_demo.sh
```

This checks the healthy baseline, injects and verifies the fault, recovers, and checks the baseline again. Once injection begins, a finally block attempts recovery even if fault verification fails. Host crashes or forced termination can still require manual recovery. The command does not start or clean labs.

## Container selection and logs

The scripts require exactly one running Kathara `r01` and use its complete prefix and lab suffix to identify all 80 devices. They do not select the first fuzzy match. Before execution, the r01 addresses must match the manifest.

When multiple Campus deployments are running, inspect `docker ps --format '{{.Names}}'` and set the exact container name:

```bash
export CAMPUS_ANCHOR='FULL_R01_CONTAINER_NAME_OF_TARGET_LAB'
bash scripts/verify_healthy.sh
```

Commands, output, exit codes, and UTC timestamps are saved under `logs/`. Errors are not treated as successful injection: ping results must include a parseable received-packet count. Docker failures, missing commands, and unparseable output are errors.

## Acceptance checks

- Healthy: interfaces and IP addresses on all 80 devices; ospfd, zebra, and forwarding on 12 routers; all expected FULL adjacencies; cross-LAN probes from 68 endpoints.
- Fault: r01 retains every interface and address; ospfd/watchfrr are stopped and zebra remains active; expected neighbors and the LAN01 route are withdrawn on other routers; five affected PCs can reach their gateway but not srv01; same-LAN connectivity works; reverse probes fail; representative PCs in the other 11 LANs can reach srv01.
- Recovery: restart r01 FRR, reload persistent frr.conf, pass every healthy check, and restore watchfrr.

Fault and recovery checks poll actual state for up to approximately 180 seconds plus one checking round. A fixed delay alone is not considered success. Endpoint probes are not an exhaustive all-pairs test.

## Files

- `fault.py`: implementation; `python3 fault.py static` performs offline checks.
- `scripts/*.sh`: command entry points similar to Enterprise.
- `lab.conf`, `*.startup`, `rXX/etc/frr/frr.conf`: complete network configuration.
- `ground_truth.json`: reference answers and expected observations.
- `dataset/campus80_Q/base/`: scenario descriptions.
- `VALIDATION.md`: validation scope and results at delivery.

For diagnosis-agent evaluation, provide only the scenario PROMPT and observation access. Do not expose ground truth, injection source, or repair answers to the agent. This package does not automatically integrate with the NIKA/SADE/FaulT-Bench runner.
