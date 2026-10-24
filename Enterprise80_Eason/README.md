# Enterprise80 v2 — Enterprise Network Troubleshooting Lab

Enterprise80 v2 is an 80-device Kathará network lab for studying fault diagnosis in a multi-site enterprise network. It models Sydney, Melbourne, Brisbane, and a data centre connected through a four-router backbone. FRRouting (FRR) provides IPv4 OSPF routing, and a controlled routing-process failure provides a reproducible troubleshooting scenario.

The package includes topology definitions, device startup configurations, an addressing inventory, provisioning and verification scripts, and one annotated fault scenario. It supports a healthy → fault → recovery experiment and can serve as input for future network-troubleshooting agent evaluation.

**Validation status:** this README describes the supplied configuration and script behaviour. No live Kathará/Docker integration test was performed for this documentation update. Expected ground truth must be confirmed in a running lab before it is treated as an experimentally validated result. Integration with a FaulT-Bench, NIKA, or SADE runner is not included.

The Campus80 companion lab is maintained once at [../Campus80_Eason](../Campus80_Eason/README.md). The former nested copy was byte-identical and has been removed; its validation evidence remains in the canonical directory.

## 1. Package contents

```text
Enterprise80_Eason/
├── README.md
├── USAGE_GUIDE_CN.md
├── addressing.csv
├── ground_truth.json
├── topology_kathara/Enterprise80/
│   ├── lab.conf
│   └── <device>.startup              # 80 device configurations
├── dataset/enterprise80_Q/base/
│   └── enterprise80-sydr1-ospfd-down.txt
└── scripts/
    ├── device.sh
    ├── provision.sh
    ├── verify_healthy.sh
    ├── inject_fault.sh
    ├── verify_fault.sh
    ├── recover.sh
    └── run_demo.sh
```

- [lab.conf](topology_kathara/Enterprise80/lab.conf) defines device connections and router images.
- The `.startup` files configure interface addresses, host default routes, and router OSPF settings.
- [addressing.csv](addressing.csv) lists every configured device address and host gateway.
- [ground_truth.json](ground_truth.json) contains a compact scenario label, expected symptoms, and a nominal repair command.
- The [scenario file](dataset/enterprise80_Q/base/enterprise80-sydr1-ospfd-down.txt) contains the agent-facing ticket, injection description, ground truth, diagnostic example, scoring axes, and supplied taxonomy labels.
- [USAGE_GUIDE_CN.md](USAGE_GUIDE_CN.md) provides the original Chinese operating guide.

## 2. Network architecture

### Device inventory

| Group | Devices | Count | Function |
|---|---|---:|---|
| Backbone | `core1`–`core4` | 4 | Fully meshed OSPF core |
| Sydney routers | `sydr1`, `sydr2` | 2 | Sydney LAN gateways and backbone access |
| Melbourne routers | `melr1`, `melr2` | 2 | Melbourne LAN gateways and backbone access |
| Brisbane routers | `brisr1`, `brisr2` | 2 | Brisbane LAN gateways and backbone access |
| Data-centre routers | `dcr1`, `dcr2` | 2 | Web and database-subnet gateways |
| Sydney clients | `sydpc1`–`sydpc17` | 17 | End hosts across two LANs |
| Melbourne clients | `melpc1`–`melpc17` | 17 | End hosts across two LANs |
| Brisbane clients | `brispc1`–`brispc17` | 17 | End hosts across two LANs |
| Web hosts | `web1`–`web9` | 9 | Data-centre hosts with an optional Python HTTP service |
| Database-role hosts | `db1`–`db8` | 8 | Data-centre endpoints; no database service is configured |
| **Total** | **12 routers and 68 end hosts** | **80** | |

There are **18 routed /30 links**: six core-to-core links, eight site-to-core uplinks, and four links between the two routers at each site. The eight /24 LANs are shared Kathará network segments; no separate switch containers are counted among the 80 devices.

### Connectivity layout

The core is a complete four-router mesh: `core1` connects to `core2`, `core3`, and `core4`; `core2` also connects to `core3` and `core4`; and `core3` connects to `core4`.

The shared Dashboard provides an explorable map under **Eason Enterprise**. Its 80 real devices and 18 router transit links come from `lab.conf`; shared LANs are drawn with virtual junctions. The controlled fault targets `sydr1` while its physical connections remain configured.

Each site has two backbone attachments, but each LAN has only one directly attached gateway router. In particular, `sydr2` is not a second gateway on Sydney LAN1. Alternative backbone paths therefore do not provide gateway redundancy for `10.10.10.0/24` when `sydr1` loses OSPF participation. No VRRP/HSRP configuration is supplied.

### Addressing plan

| LAN | Subnet | Gateway | Hosts | Host address range |
|---|---|---|---|---|
| Sydney LAN1 / Staff | `10.10.10.0/24` | `sydr1`: `10.10.10.1` | `sydpc1`–`sydpc9` | `10.10.10.11`–`10.10.10.19` |
| Sydney LAN2 | `10.10.20.0/24` | `sydr2`: `10.10.20.1` | `sydpc10`–`sydpc17` | `10.10.20.11`–`10.10.20.18` |
| Melbourne LAN1 | `10.20.10.0/24` | `melr1`: `10.20.10.1` | `melpc1`–`melpc9` | `10.20.10.11`–`10.20.10.19` |
| Melbourne LAN2 | `10.20.20.0/24` | `melr2`: `10.20.20.1` | `melpc10`–`melpc17` | `10.20.20.11`–`10.20.20.18` |
| Brisbane LAN1 | `10.30.10.0/24` | `brisr1`: `10.30.10.1` | `brispc1`–`brispc9` | `10.30.10.11`–`10.30.10.19` |
| Brisbane LAN2 | `10.30.20.0/24` | `brisr2`: `10.30.20.1` | `brispc10`–`brispc17` | `10.30.20.11`–`10.30.20.18` |
| Data-centre web LAN | `10.100.10.0/24` | `dcr1`: `10.100.10.1` | `web1`–`web9` | `10.100.10.11`–`10.100.10.19` |
| Data-centre database LAN | `10.100.20.0/24` | `dcr2`: `10.100.20.1` | `db1`–`db8` | `10.100.20.11`–`10.100.20.18` |

Core transit links use six /30 subnets within `10.255.0.0`–`10.255.0.23`. Sydney, Melbourne, Brisbane, and data-centre transit links use three /30 subnets per site, starting at `10.255.1.0`, `10.255.2.0`, `10.255.3.0`, and `10.255.4.0`, respectively. Within each site block, subnet offsets `.0/30` and `.4/30` are backbone uplinks; `.8/30` is the router-to-router link. Consult `addressing.csv` for exact interface mappings.

### Routing and services

All 12 routers use the `kathara/frr` image and advertise their configured transit and LAN networks in **OSPF area 0**. Router IDs are explicitly assigned: `1.1.1.1`–`4.4.4.4` for the core, `5.5.5.5` and `6.6.6.6` for Sydney, `7.7.7.7` and `8.8.8.8` for Melbourne, `9.9.9.9` and `10.10.10.10` for Brisbane, and `11.11.11.11` and `12.12.12.12` for the data centre. These are OSPF identifiers, not additional configured interface addresses.

Hosts use static IPv4 addresses and a default route to their local `.1` gateway. Web-host startup files attempt to launch `python3 -m http.server 80`. Availability depends on Python and the service actually starting; the supplied verification scripts test ICMP, not HTTP. Database-role hosts have addressing and routing only. The supplied configurations do not define BGP, DHCP, DNS, NAT, or external Internet connectivity.

## 3. Deployment and experiment workflow

### Prerequisites

Use an environment with a working Kathará installation, a running Docker engine accessible to the current user, Bash, and the commands used by the scripts. The router image must provide FRR, `vtysh`, and the expected FRR init script. End-host images must provide the networking utilities used by the startup and verification commands. Only router images are explicitly specified in `lab.conf`; end-host image selection depends on the Kathará environment.

The host must have enough resources to run 80 containers. No measured minimum CPU or memory requirement is supplied. The helper scripts expect exactly one running container matching the `sydr1` naming pattern; avoid concurrent copies of this lab.

### Start and provision

Run all commands from the `Enterprise80_Eason` directory:

```bash
chmod +x scripts/*.sh
kathara lstart --noterminals -d topology_kathara/Enterprise80
./scripts/provision.sh
sleep 55
./scripts/verify_healthy.sh
```

For a fresh run when an earlier instance is still deployed, first use `kathara lclean -d topology_kathara/Enterprise80` to stop and remove that lab's current runtime state.

`provision.sh` checks for 80 startup files, identifies the running lab from its `sydr1` container, and executes each startup file inside the matching container using `docker exec -i ... bash -se`. This explicit provisioning addresses the original v1 observation that a successful `kathara lstart` did not necessarily mean that device addresses and FRR configuration were applied. A successful deployment is not a successful health check.

Proceed only after `verify_healthy.sh` passes. It checks `sydr1` addresses, the OSPF process, at least one FULL adjacency, a route lookup toward `web1`, Sydney-to-web connectivity, and Melbourne-to-Brisbane connectivity. These are representative checks, not an exhaustive test of all devices or paths.

### Inject, verify, and recover

```bash
./scripts/inject_fault.sh
./scripts/verify_fault.sh
./scripts/recover.sh
./scripts/verify_healthy.sh
```

The injection script first requires a passing healthy baseline. It then stops `watchfrr` to prevent automatic daemon respawning, stops `ospfd` on `sydr1`, and waits 55 seconds before returning. The wait is a convergence allowance, not proof that every expected routing change has occurred.

`recover.sh` reapplies `sydr1.startup`, waits 30 seconds, checks for a FULL adjacency, and pings `web1` from the router. Run `verify_healthy.sh` afterwards to include the end-host checks. Recovery uses the first running container whose name contains `_sydr1_`, so it requires particular care if multiple labs are running.

For an automated sequence from a clean, undeployed lab:

```bash
./scripts/run_demo.sh
```

This runs deployment, provisioning, healthy verification, injection, fault verification, and recovery. It leaves the lab running and does not perform the additional post-recovery `verify_healthy.sh` call shown above.

### Inspect and stop the lab

```bash
./scripts/device.sh sydr1 ip -br addr
./scripts/device.sh sydr1 vtysh -c 'show ip ospf neighbor'
./scripts/device.sh sydr1 ip -4 route
./scripts/device.sh sydpc1 ping -c 3 -W 2 10.100.10.11
kathara lclean -d topology_kathara/Enterprise80
```

If provisioning fails, inspect the first failing device and error before injecting a fault. If the healthy baseline fails, resolve the deployment or routing issue first; otherwise the observed failure cannot be attributed reliably to the intended injection.

## 4. Ground truth

### Scenario identity and correct diagnosis

| Field | Ground truth |
|---|---|
| Scenario ID | `enterprise80-sydr1-ospfd-down` |
| Topology | `Enterprise80` |
| Fault family | Routing daemon failure |
| Fault location | `sydr1` |
| Failed component | FRR OSPF daemon, `ospfd` |
| Root cause | The OSPF daemon is deliberately stopped on `sydr1` |
| Injection support action | Stop `watchfrr` first so it does not immediately restart `ospfd` |
| Affected LAN | Sydney LAN1 / Staff, `10.10.10.0/24` |
| Directly affected hosts | `sydpc1`–`sydpc9` |
| Local gateway | `10.10.10.1` on `sydr1` interface `eth2` |
| Representative remote destination | `web1`, `10.100.10.11` |
| Intended preserved state | Router/container remains running; interface addresses and links remain configured |
| Required repair outcome | Restore OSPF configuration and operation, route propagation, and end-to-end reachability |

**Reference diagnosis:** Sydney LAN1 loses remote enterprise connectivity because the OSPF routing process on its gateway, `sydr1`, has been stopped. The local gateway remains reachable because its interface and directly connected LAN remain configured. After OSPF converges, other routers are expected to lose usable OSPF reachability to `10.10.10.0/24`, breaking return traffic to Sydney LAN1. Restoring the configured OSPF process and allowing convergence should restore connectivity.

This diagnosis is based on the supplied topology and injection code. The package does not contain a live execution trace confirming these outcomes.

### Mechanism and fault boundary

In the healthy configuration, `sydr1` participates in OSPF over `eth0` toward `core1` and `eth1` toward `sydr2`. It advertises its directly connected Sydney LAN1 network through OSPF. Its configured interfaces are:

| Interface | Address | Connection |
|---|---|---|
| `eth0` | `10.255.1.1/30` | `core1`, peer `10.255.1.2` |
| `eth1` | `10.255.1.9/30` | `sydr2`, peer `10.255.1.10` |
| `eth2` | `10.10.10.1/24` | Sydney LAN1 |

Stopping `ospfd` removes `sydr1` from active OSPF participation. Neighbours are expected to detect its loss and recompute routes. The precise timing and local route cleanup must be observed in the deployed FRR environment; do not assume every route disappears immediately when the process is killed. An old LSA may also remain visible in the OSPF database even after the corresponding destination becomes unreachable in the routing table.

The intended fault is a routing control-plane failure, not an interface shutdown, host gateway change, web-server failure, or complete Sydney-site outage. Sydney LAN2 and the other sites are expected to retain connectivity through their own routers and the core. That unaffected scope needs separate live checks because the supplied fault-verification script does not test it.

### Expected evidence and current check coverage

| Observation | Healthy baseline | After injection and convergence | Current automated coverage |
|---|---|---|---|
| `sydr1` addresses | All three configured addresses present | Addresses retained | Healthy script checks all three; fault script checks the LAN address only |
| `ospfd` on `sydr1` | Running | Not running | Checked in both states |
| `sydr1` OSPF neighbours | Expected FULL adjacencies with `core1` and `sydr2` | OSPF unavailable/no active adjacencies | Healthy script requires at least one FULL neighbour; fault script does not inspect neighbours |
| `sydpc1` → `10.10.10.1` | Reachable | Reachable | Checked after injection |
| Remote route to `10.10.10.0/24` | Present through OSPF | Expected absent after convergence | Described in scenario; not checked by `verify_fault.sh` |
| `sydpc1` → `web1` | Reachable | Unreachable | Checked before and after injection |
| Same-LAN host communication | Expected reachable | Expected reachable | Not explicitly checked |
| Melbourne → Brisbane | Reachable | Expected to remain reachable | Checked in healthy baseline only |
| HTTP and database applications | HTTP optional; no database configured | Not an acceptance criterion | Not checked |

A passing `verify_fault.sh` confirms its four implemented checks: reachable gateway, retained LAN address, absent `ospfd`, and failed remote ping. It does not establish every broader ground-truth claim by itself. The scenario text's `loss>0` wording is also weaker than the script's actual requirement that the remote ping command fail; record packet-level results when reporting experiments.

### Additional evidence to collect

Run these commands in both the healthy and faulty states and retain the output:

```bash
./scripts/device.sh sydr1 ip -br addr
./scripts/device.sh sydr1 pgrep -x ospfd
./scripts/device.sh sydr1 vtysh -c 'show ip ospf neighbor'
./scripts/device.sh core1 vtysh -c 'show ip ospf neighbor'
./scripts/device.sh sydr2 vtysh -c 'show ip ospf neighbor'
./scripts/device.sh dcr1 ip -4 route show 10.10.10.0/24
./scripts/device.sh sydpc1 ping -c 3 -W 2 10.10.10.1
./scripts/device.sh sydpc1 ping -c 3 -W 2 10.10.10.12
./scripts/device.sh sydpc1 ping -c 3 -W 2 10.100.10.11
./scripts/device.sh sydpc10 ping -c 3 -W 2 10.100.10.11
./scripts/device.sh melpc1 ping -c 3 -W 2 10.30.10.11
```

During the fault, a nonzero result from `pgrep`, unavailable OSPF output on `sydr1`, and failed Sydney LAN1 remote pings are expected evidence rather than command-workflow failures. An empty exact-prefix route listing on `dcr1` supports the expected withdrawal; interpret it together with adjacency and connectivity evidence.

### Repair and acceptance criteria

The compact JSON and scenario file name `/etc/init.d/frr restart` as the nominal fix. However, the supplied startup files apply OSPF settings through `vtysh` without an explicit configuration-save command. A restart alone must therefore not be assumed to restore the complete running configuration in every environment. The packaged `recover.sh` addresses this by reapplying `sydr1.startup`, including its OSPF settings.

Accept recovery when `ospfd` is running, both expected Sydney-router adjacencies have recovered, the remote route to `10.10.10.0/24` is restored, and `sydpc1` can again reach `web1` while the local gateway remains reachable. Confirm unaffected-site connectivity as well. These full acceptance criteria extend beyond the two checks currently implemented in `recover.sh`.

## 5. Use in agent evaluation

The supplied scenario uses section-delimited text: `[PROMPT-TO-AGENT]`, `[INJECTION]`, `[POST-INJECT-CHECK]`, `[GROUND-TRUTH]`, `[FIX]`, `[DIAGNOSTIC-PROCESS]`, `[SCORING-AXES]`, and `[NIKA-LABEL]`.

Give the diagnostic agent the problem statement and the intended observation tools. Keep this README's answer-bearing sections, `ground_truth.json`, injection details, reference fix, and scoring criteria out of the agent's input when evaluating independent diagnosis.

The supplied scoring axes require identification of:

1. **Device:** `sydr1`.
2. **Component:** OSPF / the `ospfd` routing process.
3. **Cause:** the daemon is stopped or down.

A stronger explanation should connect the reachable local gateway to preserved local connectivity, explain the loss of remote routing, and propose a repair that restores OSPF and passes end-to-end verification. “Sydney is down” or “the web server is down” does not identify the supplied root cause. The diagnostic process in the scenario is an example route to the answer, not the only valid investigation sequence.

The scenario declares `routing_daemon_down`, `ROUTING_FAILURE`, and `in_taxonomy: true` under `[NIKA-LABEL]`. These are supplied metadata values; their compatibility with a particular external NIKA taxonomy or runner has not been independently established here.

## 6. Scope and reproducibility notes

- This release has one fault scenario over one 80-device topology. It is not an 80-scenario dataset.
- Topology redundancy and gateway redundancy are distinct: the core has multiple paths, but each LAN has one configured gateway.
- The executable injection stops both `watchfrr` and `ospfd`; the scenario text only lists `pkill ospfd`. Use the supplied injection script for the documented lifecycle and account for this difference when building a runner.
- The JSON fix is a compact description; use configuration-aware recovery and verify the result rather than relying on daemon restart alone.
- The checks sample selected paths. They do not measure full reachability, HTTP availability, application performance, latency, throughput, or diagnosis accuracy.
- Images are not pinned to explicit versions in `lab.conf`. Record the actual Kathará, Docker, FRR, and image versions or digests with experimental results.
- Fixed waits may be insufficient on a busy host. Confirm observable adjacency and route states before classifying a result.
- For each trial, record baseline output, injection time, fault evidence, the agent's diagnosis, repair actions, and recovery output. Restore and revalidate the healthy baseline before the next injection.

The intended result is a documented, inspectable troubleshooting experiment whose ground truth can be traced to configuration, a controlled fault, and collected network evidence.
