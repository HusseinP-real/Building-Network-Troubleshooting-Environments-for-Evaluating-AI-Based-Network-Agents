# Campus80: Complete Topology and OSPF Fault Injection

This package retains the 80-node topology and startup configurations from `campus80_fixed.zip`, while adding a reproducible "healthy → fault → recovery" workflow. It can be executed using the Python 3 standard library. The host machine must have Docker and Kathará installed, and the container images must include FRR, `ip`, `ping`, `pgrep`, and `pkill`.

## Can the same type of fault be applied to both topologies?

Yes. We use the same `routing_daemon_down` fault as in `Enterprise80_Final_v2`: first, `watchfrr` is stopped to prevent automatic restarts, followed by stopping `ospfd` on the gateway. Network interfaces, IP addresses, the `zebra` daemon, and the containers themselves remain active.

| Item | Enterprise80 v2 | Campus80 |
|---|---|---|
| Faulty Device | sydr1 | r01 |
| Faulty Component | ospfd | ospfd |
| Affected LAN | 10.10.10.0/24 | 10.10.1.1/24 |
| Affected Endpoints | sydpc1–sydpc9 | pc01–pc05 |
| Local Gateway | 10.10.10.1 | 10.10.1.1 |
| Remote Probe | web1 | srv01 (10.10.3.100) |

This represents "one fault type applied as two distinct instances across two topologies." Because the device and IP parameters differ, the hard-coded scripts from the Enterprise topology cannot be used directly. While using the same fault type facilitates a comparison of diagnostic performance across topologies, it does not imply that a wide range of fault types is covered, nor does it suggest that both topologies present the same level of difficulty. Since `r01` also handles packet forwarding, its withdrawal from OSPF triggers a network-wide re-convergence.

## Is the network complete?

The files include 12 routers, 60 PCs, 8 servers, 20 `/30` links, 12 `/24` LANs, default routes for the hosts, and an OSPF Area 0 configuration. Static consistency checks have passed. Please refer to the output of the local `verify_healthy.sh` script to determine whether the network baseline is functioning correctly. HTTP is an optional service; the current acceptance criteria cover IPv4/ICMP and OSPF, but not HTTP applications. Additional services such as external network access, DNS, and DHCP are not implemented.

## Using an Existing Campus80 Instance

After extracting the files, navigate to the directory containing this document. If an instance of Campus80 is already running, there is no need to restart it; simply execute the following:

```bash
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
# Perform diagnostics and record results while in the faulted state; then, restore the system:
bash scripts/recover.sh
```

The injection script first performs a full health check; if this fails, no fault will be injected. Once a fault is injected, the system will remain in that state until the recovery script is run. If an error occurs during injection—which may result in some processes being terminated—please run the recovery script. Do not attempt to "recover" the system by performing another injection.

## Starting from a New Directory

Use this procedure only when no Campus80 instance is currently running:

```bash
kathara lstart -d . --noterminals
# Wait for the startup scripts to complete and for OSPF to converge; this may take longer on heavily loaded machines.
sleep 90
bash scripts/verify_healthy.sh
bash scripts/inject_fault.sh
bash scripts/verify_fault.sh
bash scripts/recover.sh
```

If an instance of Campus80 from a different directory is already running, either continue using that instance or stop it from its original directory before starting a new one. Do not mix instances from different directories. This setup can run concurrently with "Enterprise" or other experiments, as the scripts only target the relevant Campus containers.

## Automated Experiment Execution (Requires the experiment to be already running)

```bash
bash scripts/run_demo.sh
```

This command verifies the health baseline, injects and validates a fault, restores the system, and then re-verifies the baseline. The script includes a `finally` block to ensure recovery is attempted after the injection phase, even if the fault validation fails. Note that in cases such as a host machine crash or the forced termination of processes, manual recovery will still be required. This command does not initiate or clean up any experiments. ## Container Selection and Logging

The script requires exactly one running Kathará `r01` container, identified by its full prefix and experiment suffix, to match all 80 devices; it will not select a container based on a partial or ambiguous match. Before execution, the script verifies that the `r01` address aligns with the manifest.

When multiple "Campus" environments are running simultaneously, first identify the correct container name using `docker ps --format '{{.Names}}'`, then set the variable accordingly:

```bash
export CAMPUS_ANCHOR='[Insert the full r01 container name for the target experiment]'
bash scripts/verify_healthy.sh
```

All executed commands, their outputs, exit codes, and UTC timestamps are logged in the `logs/` directory. Errors are not interpreted as "successful fault injection"—for instance, `ping` results are parsed based on the number of packets received; Docker failures, missing commands, or an inability to parse command output are all treated as errors.

## Validation Criteria

- **Healthy State:** All 80 devices have the correct interfaces and IP addresses; the 12 routers have `ospfd`/`zebra` and forwarding enabled; all expected OSPF adjacencies reach the `FULL` state; and cross-LAN probes from 68 end-hosts are successful.
- **Fault State:** On `r01`, all interfaces and IP addresses remain, `ospfd`/`watchfrr` are stopped, but `zebra` continues to run. For other routers, expected OSPF adjacencies are lost, and routes to `LAN01` are withdrawn. The 5 affected PCs can reach their gateway but cannot access `srv01`; intra-LAN communication remains functional; reverse probes fail; and PCs in the other 11 LANs retain access to `srv01`.
- **Recovery State:** `FRR` services on `r01` are restarted, configurations are reloaded from the persistent `frr.conf`, all health checks pass, and `watchfrr` is restored.

During the fault and recovery phases, the script continuously monitors the actual system state—waiting for up to ~180 seconds (plus the duration of a single check cycle) rather than relying on a fixed-duration sleep timer to declare success. End-host probing does not constitute an exhaustive, all-pairs connectivity test across the entire network.

## Files

- `fault.py`: The complete implementation; can be used for offline verification via `python3 fault.py static`.
- `scripts/*.sh`: Command entry points, similar to those used in the "Enterprise" scenario. - `lab.conf`, `*.startup`, `rXX/etc/frr/frr.conf`: Complete network configuration.
- `ground_truth.json`: Correct answers and expected behaviors.
- `dataset/campus80_Q/base/`: Scenario description.
- `VALIDATION.md`: Scope and results of tests conducted at the time of delivery.

When evaluating a diagnostic agent, provide only the scenario prompt and observation access; do not disclose the ground truth, the injected source code, or the fix/solution. This package does not include an automated integration for NIKA, SADE, or FaulT-Bench runners.
