# Multi-Site Enterprise and Dual-ISP Network Troubleshooting Benchmark

**SOFT3888 | Network troubleshooting environment prototype | Kathara + FRRouting**

A reproducible, container-based **80-device** network designed to evaluate troubleshooting workflows on a multi-site enterprise topology connected to two simulated ISPs. It uses **OSPF for intra-AS routing** and **eBGP for enterprise-to-ISP route exchange**, with controlled fault injection, recovery checks, structured ground truth and user tickets.

> **Verified prototype, not a completed AI benchmark.** On **12 October 2026**, the developer reported successful live execution on macOS: **18/18 baseline checks**, **F01–F03 automated fault/recovery tests**, and **8/8 Python unit tests**. These are results from the developer's local environment, not independently reproduced CI runs. **SADE integration and NIKA/OwnTopologies format compatibility remain unverified.**

## 1. Project purpose

The client requested larger, realistic topologies (ideally **75–100 devices**), multiple subnets and protocols, repeatable faults and user reports varying in detail/accuracy. This contribution develops **one** 80-node topology with **three** repeatable fault scenarios and **twelve** prewritten tickets. It is intended to complement other team topologies, **not** to fulfill the client's aspirational ten-topology target by itself.

## 2. What is implemented

| Component | Implementation |
|---|---|
| Devices | **18 FRR routers, 20 Linux bridge switches, 42 endpoints** (80 total) |
| Routing domains | Enterprise AS65000, ISP-A AS65010, ISP-B AS65020 |
| Routing | OSPF **area 0** within each AS, eBGP on four enterprise–ISP links |
| Sites | Headquarters, Branch A, Branch B, Data Center; two simulated ISP services |
| Services | Two HTTP test endpoints (`:8080`) and ICMP reachability probes |
| Automation | Deterministic topology generator, static validator, baseline checker, fault injection/recovery and unit tests |
| Dataset | Three fault ground-truth records and four tickets per scenario |
| Agent evaluation | Offline prediction scorer exists; **no live SADE adapter** |

**Not implemented:** 802.1Q VLAN trunking, VRRP/first-hop failover, DHCP, DNS, ACL policy scenarios, multi-area OSPF, or external/public Internet connectivity. Switch nodes use simple Linux bridges, not full-featured managed switches.

## 3. Architecture overview

```text
                 ISP-A (AS65010)           ISP-B (AS65020)
                a1 -- a2 -- a3           b1 -- b2 -- b3
                 |           |            |           |
                e1          e3           e2          e4
                  \         /             \         /
               +------------------------------------------+
               | Enterprise AS65000                       |
               | Redundant e1--e2--e3--e4--e1 edge ring   |
               | OSPF area 0                              |
               +------------------------------------------+
                           |  |  |  |
                     HQ / Branch A / Branch B / DC
                      redundant site uplinks + LANs
```

The diagram is conceptual, not a port-level wiring diagram. See [Architecture](docs/ARCHITECTURE.md) and `inventory.json` for **exact links, interface numbers and addresses**. The ISP service ranges (`198.18.10.0/24`, `198.18.20.0/24`) are isolated lab/test networks, not access to the public Internet.

## 4. Documentation

| Document | Contents |
|---|---|
| [Architecture & IP/AS plan](docs/ARCHITECTURE.md) | Roles, subnet plan, link adjacency and routing decisions |
| [Deployment & operations](docs/DEPLOYMENT.md) | Installation, startup, checks, shutdown and troubleshooting |
| [Fault scenarios](docs/FAULT_SCENARIOS.md) | F01–F03 injection, expected behavior, controls, recovery |
| [Validation evidence](docs/VALIDATION.md) | Exact scope of the reported successful runs and how to save evidence |
| [Benchmark data and roadmap](docs/BENCHMARK_AND_ROADMAP.md) | Tickets, ground truth, limitations, SADE and next milestones |

## 5. Quick start

```bash
cd MultiSite_BGP_OSPF_Benchmark
chmod +x run_mac.sh
./run_mac.sh                    # generate + static checks + Python unit tests
kathara check                   # Docker/Kathara preflight
python3 lab.py start            # deploy lab
python3 lab.py check            # expect Baseline: 18/18 passed after convergence
kathara exec -d "$PWD" e1 "vtysh -c 'show bgp summary'"
kathara exec -d "$PWD" e1 "vtysh -c 'show ip ospf neighbor'"
```

**Only inject faults after `python3 lab.py check` passes.** Run sequentially and confirm full baseline after each repair:

```bash
python3 lab.py test-fault F01 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F02 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F03 --settle-seconds 35
python3 lab.py check
```

Shut down **only this lab**:

```bash
python3 lab.py stop
```

Do **not** use `kathara wipe` or `docker system prune` as routine project commands because they can affect other labs. Startup may take longer for 80 containers. Detailed instructions: [Deployment](docs/DEPLOYMENT.md).

## 6. Verified results and evidence status

| Check | Last reported result | Interpretation |
|---|---|---|
| Static validation | PASS: 80 devices, 68 collision domains, 92 distinct IPs, 20 routed P2P links | Consistency of generated configuration |
| Python unit tests | 8/8 PASS | Unit-level generator / executor checks |
| Baseline checks | 18/18 PASS | Four BGP neighbor assertions, twelve host connectivity probes, two HTTP probes |
| OSPF (e1) | Four `Full/DR` neighbors | Verified adjacency on e1; not an all-router OSPF audit |
| eBGP (e1 → a1) | Established; one prefix received | One verified peer observation; four peers covered by baseline checks |
| F01, F02, F03 | User reported all three tests passed and recovered | Fault effects and post-repair state; full logs should be committed as evidence if appropriate |
| SADE live agent runs | Not performed | No claims about AI diagnosis accuracy |

**Evidence policy:** do not manufacture trial logs or treat the 18 baseline probes as exhaustive verification of all 80 nodes. Keep raw `results/` evidence with dates and environment versions when sharing externally; sanitize host identifiers if needed.

## 7. Source of truth and caveats

- `tools/generate.py` regenerates `lab.conf`, device `*.startup` scripts, FRR configs and `inventory.json`. Update the generator, not only generated outputs.
- Site hosts use primary gateway `.1`; the `.2` routers are alternative routers but **no automatic gateway failover** is implemented.
- Enterprise border routers advertise an aggregate `10.0.0.0/8` backed by Null0. This simplifies return routes but can obscure some missing-specific-route issues.
- F01 and F02 both alter **two** ISP-A border routers. Treat these as single **scenario events affecting two devices**, not literal single-device failures.
- The customer-provided `OwnTopologies` repository was inaccessible when this prototype was developed. No dataset-schema compliance is claimed.
- The bundled `tools/evaluate_agent.py` scores supplied predictions offline; **it does not launch or connect to SADE**.

See [Benchmark & roadmap](docs/BENCHMARK_AND_ROADMAP.md) for the remaining work.
