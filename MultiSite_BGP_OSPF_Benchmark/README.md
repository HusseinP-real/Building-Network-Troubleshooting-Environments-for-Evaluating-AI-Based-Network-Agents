# SOFT3888 — Multi-Site Enterprise / Dual ISP BGP–OSPF Troubleshooting Benchmark

**Status: Generated and offline validated; live Kathara, routing convergence, and SADE integration NOT yet verified.**

This is an **independent** SOFT3888 prototype, developed without access to the client's `OwnTopologies` repository. It uses Kathara for device emulation, FRRouting for OSPF and eBGP, and repeatable fault-case metadata. It is **not** advertised as NIKA-compatible or a completed SADE benchmark. Its goal is a usable starting point for the final evaluated dataset.

## Deliverables

- Exactly **80 nodes**: 18 FRR routers, 20 Linux bridge switches, 42 endpoints.
- 3 autonomous systems: enterprise **AS65000**, ISP-A **AS65010**, ISP-B **AS65020**.
- Headquarters, Branch A, Branch B and Data Center with separate `/24` LANs.
- Two simulated ISP service subnets, OSPF within ASes, eBGP between ASes.
- Deterministic generator, device inventory, Kathara lab and startup files.
- Three automated failure/repair scenarios and twelve user tickets, with separated ground truth.
- Runtime baseline checker and offline evaluation metrics script.

## Architecture

```text
               ISP-A (AS 65010)            ISP-B (AS 65020)
                 a1 -- a2 -- a3            b1 -- b2 -- b3
                 |      |     |            |     |      |
                 |    ext_A   |            |   ext_B    |
                 e1          e3            e2          e4
                  \         /                \         /
                Enterprise AS 65000: e1 -- e2 -- e3 -- e4 -- e1
                                      |       |       |
                            HQ routers, Branch A/B routers,
                            Data Center routers; OSPF Area 0
                                   |           |
                       bridged access switches and hosts
```

**Caution:** Diagram is conceptual; the exact point-to-point edges are stored in `inventory.json`. The enterprise e1–e4 ring is redundant. Each site has two uplinks, one per site router. Site endpoints use the `.1` router as their primary gateway; **automatic first-hop gateway failover is not implemented**, so loss of that router can still affect endpoint traffic.

## Network address and AS plan

| Function | Prefix / range | Equipment |
|---|---|---|
| Enterprise HQ LAN | `10.10.10.0/24` | hq_r1 `.1`, hq_r2 `.2`, hq_h01 `.21` |
| Branch A LAN | `10.20.10.0/24` | ba_r1 `.1`, ba_r2 `.2`, ba_h01 `.21` |
| Branch B LAN | `10.30.10.0/24` | bb_r1 `.1`, bb_r2 `.2`, bb_h01 `.21` |
| Data Center LAN | `10.40.10.0/24` | dc_r1 `.1`, dc_r2 `.2`, dc_h01 `.21` |
| Enterprise P2P | `10.255.1.0/31` through `10.255.12.0/31` | OSPF area 0 |
| ISP-A P2P | `172.20.1.0/31` through `172.20.2.0/31` | OSPF area 0 in AS65010 |
| ISP-B P2P | `172.21.1.0/31` through `172.21.2.0/31` | OSPF area 0 in AS65020 |
| eBGP peering links | `172.31.1.0/31` through `172.31.4.0/31` | Enterprise ↔ ISP border routers |
| ISP-A external service | `198.18.10.0/24` | a2 gateway `.1`, ext_a_web `.10` |
| ISP-B external service | `198.18.20.0/24` | b2 gateway `.1`, ext_b_web `.10` |
| Enterprise BGP aggregate | `10.0.0.0/8` | originated at each enterprise eBGP edge using Null0 summary route |

Notes: `198.18.0.0/15` is reserved for benchmark/testing purposes and is used entirely inside the isolated emulation; it is **not the public Internet**. All ASNs are private-use numbers. Prefix choice is laboratory-only; do not connect these networks to production without renumbering.

## Prerequisites

- macOS (including Apple Silicon) or Linux, **Docker Desktop running** and **Kathara CLI installed**.
- Python 3.9+, standard library only for scripts.
- Access to Docker images `kathara/frr:10` and `kathara/base:latest` (not guaranteed unless pulled/available).
- A workstation with adequate RAM for 80 containers. Use the mini profile first in constrained environments; currently the generator creates the full 80-node lab only.
- Connectivity to download images at least once. Check Docker resources first.

## Quick start on Mac

```bash
unzip MultiSite_BGP_OSPF_Benchmark.zip
cd MultiSite_BGP_OSPF_Benchmark
python3 tools/generate.py
python3 tools/validate_static.py
python3 -m unittest discover -s tests -v

docker info >/dev/null
kathara check
docker pull kathara/frr:10
docker pull kathara/base:latest
python3 lab.py start
# Wait for routing daemons and BGP/OSPF convergence, then:
python3 lab.py check

# Inspect live devices:
kathara exec -d "$PWD" e1 "vtysh -c 'show ip ospf neighbor'"
kathara exec -d "$PWD" e1 "vtysh -c 'show bgp ipv4 unicast summary'"
kathara exec -d "$PWD" hq_h01 "ping -c 2 198.18.10.10"

python3 lab.py test-fault F02 --settle-seconds 35
python3 lab.py stop
```

**Do not run live fault tests until baseline checks pass.** If one fails, start by inspecting `kathara exec ... 'ip addr'`, `vtysh -c 'show ip route'`, and device startup logs rather than interpreting failed ping as a valid injected fault.

## Fault scenarios

| ID | Injection | Expected symptom | Isolation / control | Repair |
|---|---|---|---|---|
| F01 | Disable a1 and a3 eBGP-facing `eth1` | ISP-A service unreachable | ISP-B service stays available | Bring both interfaces up |
| F02 | Withdraw `198.18.10.0/24` at both ISP-A border speakers | ISP-A prefix unreachable, eBGP sessions may stay up | ISP-B service stays available | Re-originate prefix |
| F03 | Stop FRR on both Branch-A routers | HQ loses path to Branch-A host | DC path stays available | Restart FRR |

Commands:

```bash
python3 lab.py inject F01
python3 lab.py repair F01
python3 lab.py test-fault F01 --settle-seconds 35
python3 lab.py test-fault F02 --settle-seconds 35
python3 lab.py test-fault F03 --settle-seconds 35
```

`test-fault` checks the healthy precondition, injects the fault, checks affected and unaffected paths, **always attempts repair in a `finally` clause** after injection, and checks recovery. F01 and F02 deliberately disrupt **both** ISP-A peerings: taking down only one peering may have no service impact because of redundancy.

**Known caveat:** `test-fault` records functional effect, but does not prove root cause; an additional FRR routing-state assertion and repeated trials should be added before a final client claim. These cases are designed, not yet experimentally validated on the user's machine.

## User reports / benchmark fairness

Each scenario has 4 tickets: general user, engineer, expert, and misleading. The `scenarios/FXX/ground_truth.json` files are for the evaluator **only**. Do not expose them to SADE inside the diagnostic prompt or accessible tools. Use each case as an independent trial with a fresh fault baseline. A misleading ticket should not redefine what the true fault is.

The included `tools/evaluate_agent.py` can score an external JSON list of model predictions against ground truth. **It does not run SADE and is not a SADE adapter.** See `docs/EVALUATION.md` for example schema and next integration steps.

## Generation and reproducibility

Run `python3 tools/generate.py` to recreate `lab.conf`, `*.startup`, `configs/**/frr.conf`, each router's mounted `/etc/frr/frr.conf`, and `inventory.json`. Avoid editing generated files directly; change the generator source. For reproducibility, record `git rev-parse HEAD`, `docker image inspect`, Kathara version, host OS, test timestamps, and each agent model/configuration.

## Important technical limitations

1. Docker and Kathara are unavailable in the current authoring environment; **no live network deployment or end-to-end validation has occurred here**.
2. External services are simple Python HTTP servers, not realistic multi-tier enterprise applications.
3. Only OSPF/eBGP plus transparent layer-2 bridging and basic HTTP are implemented. VRRP, VLAN trunks, STP stress cases, ACL, DNS and DHCP are *not implemented*; do not claim they are.
4. OSPF uses area 0 in each independent AS; not multi-area OSPF.
5. FRR command behavior, daemon config file mount and Docker image contents must be verified on your Kathara installation. If a startup or FRR command differs, fix it based on the live logs before accepting the benchmark.
6. An aggregate `10.0.0.0/8` Null0 advertisement simplifies return routing to enterprise sites; it may conceal configuration mistakes and must be considered in interpreting routing anomalies.
7. `OwnTopologies` is inaccessible and the dataset schema has not been confirmed; compatibility with customer dataset and NIKA is unverified.
8. SADE is not invoked by this package. Offline scoring is not evidence of agent performance.

## Extension priorities toward project goals

1. Obtain client schema and port these scenarios to it without leaking ground truth.
2. Add interface/BGP/OSPF state assertions and 3+ repeated runs per fault.
3. Implement branch gateway redundancy, multiple VLANs/subnets, DNS and ACL service faults.
4. Add SADE runtime connector with controlled read-only diagnostic tools and saved traces.
5. Compare diagnosis accuracy by reporter type, fault family, network size and protocol, with honest failures and per-run metadata.
6. Obtain customer confirmation of exact deliverable definitions and target scenario counts.

See `docs/ARCHITECTURE.md` and `docs/EVALUATION.md`.
