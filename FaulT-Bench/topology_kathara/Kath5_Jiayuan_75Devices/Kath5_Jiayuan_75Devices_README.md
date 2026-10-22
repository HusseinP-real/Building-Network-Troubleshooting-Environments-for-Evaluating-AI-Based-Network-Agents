> Reproduction tools, evaluator-only Ground Truth catalog and raw evidence
> are now included. Follow [the runbook](../../docs/soft3888-runbook.md).
> Docker images are locally built from the supplied recipes. Model inference
> and judge scoring require separately configured credentials.

> Development update: the original report below records historical tests.
> Current services, strict validation, runtime fixes and custom faults are
> described in [SOFT3888 development](../../docs/soft3888-development.md).
> Internal DNS now has an explicit service controller and intapp1 has a real
> HTTP application. New changes require their own hash-linked live reports;
> historical PASS statements do not automatically validate the new revision.

# Kath5 75-Device Topology Extension

**Project:** SOFT3888 – Building Network Troubleshooting Environments for Evaluating AI-Based Network Agents  
**Environment:** Kathará network emulation with FRRouting (FRR)  
**Topology directory:** `FaulT-Bench/topology_kathara/Kath5_Jiayuan_75Devices/`

## 1. Overview

This deliverable extends the team's existing **50-device Kath5 topology to 75 devices**. The extension adds five distinct network zones while retaining the original topology and its routing structure. Its purpose is to provide a larger and more varied environment for network connectivity testing and future AI-agent troubleshooting scenarios.

The resulting topology contains **21 routers and 54 end devices**. The 25 additional devices are distributed across Branch F, Branch G, a DMZ, a Management Zone, and an Internal Services Zone.

This is a **topology and infrastructure extension**, not a claim that a complete NIKA benchmark integration or AI-agent evaluation has been implemented.

## 2. Extension Summary

| Zone | Added devices | Connection and routing | Purpose |
| --- | --- | --- | --- |
| Branch F | `r14`, `r15`, `f1`–`f5` (7) | Connected to `r7`; OSPF Area 1 | Add a multi-hop branch network |
| Branch G | `r16`, `r17`, `r18`, `g1`–`g4` (7) | Dual uplinks from `r16` to `r5` and `r6`; OSPF Area 1 | Provide redundant routing paths and a failover test case |
| DMZ | `r19`, `dmzweb1`, `dmzweb2`, `dmzdns1` (4) | Connected to `r9`; OSPF Area 0 | Introduce reachable HTTP and DNS services |
| Management Zone | `r20`, `mgmt1`–`mgmt3` (4) | Connected to `r3`; OSPF Area 0 | Separate management-side hosts from user branches |
| Internal Services Zone | `r21`, `intdns1`, `intapp1` (3) | Connected to `r12`; EIGRP AS 100 | Extend the EIGRP portion of the topology and prepare internal services |
| **Total** | **25 devices** | | **50 → 75 devices** |

## 3. Network Design and Implementation

### 3.1 Branch F — Multi-hop OSPF extension

Branch F attaches to the existing `r7` router through `r14` and `r15`:

`r7 → r14 → r15 → f1–f5`

- `r7`–`r14`: `192.168.214.0/30`
- `r14`–`r15`: `192.168.215.0/30`
- Branch F LAN: `192.168.216.0/24`
- Routing: OSPF Area 1

This introduces additional routing hops between branch hosts and the original network.

### 3.2 Branch G — Redundant OSPF paths

Branch G uses two uplinks to the existing backbone:

```text
r5 ----\
        r16 -- r17 -- r18 -- g1–g4
r6 ----/
```

- `r5`–`r16`: `192.168.220.0/30`
- `r6`–`r16`: `192.168.221.0/30`
- `r16`–`r17`: `192.168.222.0/30`
- `r17`–`r18`: `192.168.223.0/30`
- Branch G LAN: `192.168.224.0/24`
- Routing: OSPF Area 1

The dual-uplink design supports testing route changes following a link failure. This is a useful basis for fault detection and root-cause analysis scenarios.

### 3.3 DMZ — HTTP and DNS services

The DMZ is connected through `r9 → r19`:

- Uplink: `192.168.230.0/30`
- DMZ LAN: `192.168.231.0/24`
- Gateway `r19`: `192.168.231.1`
- `dmzweb1`: `192.168.231.11`
- `dmzweb2`: `192.168.231.12`
- `dmzdns1`: `192.168.231.13`
- Routing: OSPF Area 0

Both web hosts serve simple HTML pages over HTTP using Python's HTTP server. The DNS host runs `dnsmasq` and provides records including:

| DNS name | Address |
| --- | --- |
| `web1.dmz.test` | `192.168.231.11` |
| `web2.dmz.test` | `192.168.231.12` |

DNS resolution was verified by querying `dmzdns1` directly. This does **not** imply that every client has been configured to use the DMZ DNS server as its default resolver.

### 3.4 Management Zone — Separate management subnet

The Management Zone is attached to `r3` through `r20`:

- Uplink: `192.168.240.0/30`
- Management LAN: `192.168.241.0/24`
- Gateway `r20`: `192.168.241.1`
- `mgmt1`: `192.168.241.11`
- `mgmt2`: `192.168.241.12`
- `mgmt3`: `192.168.241.13`
- Routing: OSPF Area 0; the management-facing interface is configured as passive

The management hosts have been validated for network connectivity, including access to a DMZ web service. A dedicated management application or access-control policy has **not** yet been implemented.

### 3.5 Internal Services Zone — EIGRP extension

The final three devices extend the EIGRP portion of the original topology through `r12`:

`r12 → r21 → intdns1 / intapp1`

- `r12`–`r21`: `192.168.250.0/30`
- Internal Services LAN: `192.168.251.0/24`
- Gateway `r21`: `192.168.251.1`
- `intdns1`: `192.168.251.11`
- `intapp1`: `192.168.251.12`
- Routing: EIGRP AS 100

`r21` uses a default route via `r12`. The existing `r12` configuration also has a static default route toward `r11`. These settings were retained because the existing FRR EIGRP/OSPF redistribution behaviour does not reliably provide all return routes automatically.

**Historical status:** Connectivity was tested before service development. Current source includes Internal DNS and HTTP startup/controller files; see the development report for current validation evidence.

## 4. Implementation Method

The extension was implemented in the topology source files rather than by making permanent manual changes only inside running containers:

1. Added Kathará device-to-network mappings in `lab.conf`.
2. Created or updated each device's `.startup` script to assign IP addresses, bring interfaces up, configure routes, and start required services.
3. Created or updated FRRouting configurations under `r*/etc/frr/frr.conf` to advertise the new networks through OSPF or EIGRP.
4. Added persistent DNS and web content files for the DMZ services.
5. Relaunched the lab with `kathara lclean` and `kathara lstart --noterminals` and tested the resulting network.

The new networks use dedicated point-to-point subnets and LAN subnets, keeping them separate from the existing branch address spaces. The extension preserves the original OSPF/EIGRP structure instead of replacing it with a new routing design.

## 5. NIKA Reference and Relationship

**Reference repository:** [sands-lab/nika](https://github.com/sands-lab/nika)

NIKA was used as a **design reference for network troubleshooting scenarios**, especially the idea of connecting a controlled network configuration fault with an observable symptom, validation checks, a known root cause, and a recovery action.

A specific local reference examined during development was:

`dataset/nika_ospf_Q/base/ospf-enterprise-dist1-network-statement-removed.txt`

The scenario format informed the planned documentation structure:

- `[PROMPT-TO-AGENT]` — a user-facing report or troubleshooting request
- `[INJECTION]` — the configuration change or failure introduced
- `[POST-INJECT-CHECK]` — observable evidence that the fault occurred
- `[GROUND-TRUTH]` — the intended fault location and cause
- `[FIX]` — the corrective action
- `[DIAGNOSTIC-PROCESS]` — possible diagnostic steps
- `[SCORING-AXES]` and `[NIKA-LABEL]` — evaluation-oriented metadata

The 75-device topology is an independently extended Kathará environment. **It is not presented as an official NIKA topology, a copied NIKA scenario, or an already integrated NIKA/SADE evaluation pipeline.** Scenario files following this reference format can be developed and validated in subsequent work.

## 6. Validation Performed

The following checks were completed during incremental development. The results below describe **specific executed tests**, not exhaustive coverage of every device-to-device path.

| Area | Checks performed | Observed result |
| --- | --- | --- |
| Branch F | OSPF neighbour state and Branch F ↔ Branch A connectivity | Neighbours reached Full; test pings succeeded |
| Branch G | OSPF neighbour state, cross-branch connectivity, and individual uplink shutdown tests | Routing changed to the available alternate path; connectivity was confirmed after convergence and links were restored |
| DMZ | OSPF neighbour state; HTTP requests to both web servers; direct DNS queries | HTTP pages returned successfully; DNS queries returned the configured addresses |
| Management Zone | OSPF neighbour state; `mgmt1` ↔ Branch A ping; `mgmt2` → DMZ HTTP | OSPF Full; bidirectional pings succeeded; HTTP content returned |
| Internal Services Zone | R21 EIGRP neighbour, local and cross-network pings, DMZ HTTP request, route lookups | R12 neighbour established; tested pings showed 0% packet loss; HTTP request succeeded; expected next hops were present |

### Recorded Internal Services validation examples

- `intdns1 → 192.168.251.1`: 4/4 ICMP replies
- `intdns1 → 192.168.250.1`: 4/4 ICMP replies
- `intapp1 → 70.1.1.11` (Branch A): 4/4 ICMP replies
- `a1 → 192.168.251.12`: 4/4 ICMP replies
- `intapp1 → http://192.168.231.11/`: DMZ HTML page returned
- `r12 → 192.168.251.12`: next hop `192.168.250.2`
- `r21 → 70.1.1.11`: next hop `192.168.250.1`

### Example validation commands

Run from the topology directory after starting the lab:

```powershell
kathara lstart --noterminals
kathara exec r21 -- vtysh -c "show ip eigrp neighbors"
kathara exec intapp1 -- ping -c 4 70.1.1.11
kathara exec a1 -- ping -c 4 192.168.251.12
kathara exec intapp1 -- curl -sS --max-time 5 http://192.168.231.11/
kathara exec r12 -- ip route get 192.168.251.12
kathara exec r21 -- ip route get 70.1.1.11
```

For DMZ DNS, a direct query can be made with:

```powershell
kathara exec a1 -- dig '@192.168.231.13' web1.dmz.test +short
```

## 7. Fault Scenario Opportunities

The extended network supports several **candidate** troubleshooting scenarios:

| Scenario idea | Potential observable symptom | Likely investigation area |
| --- | --- | --- |
| Branch G uplink failure | Route changes or temporary loss during convergence | OSPF neighbour and route state on `r16`, `r5`, `r6` |
| Missing OSPF network advertisement | A subnet becomes unreachable from other areas | Router OSPF configuration and routing table |
| EIGRP advertisement removed | Internal subnet unreachable from remote networks | `r12`/`r21` EIGRP configuration and learned routes |
| DMZ DNS misconfiguration | Domain name fails while direct IP access may still work | `dmzdns1` configuration and DNS queries |
| DMZ HTTP service stopped | Network connectivity exists but HTTP fails | Web host process and TCP service |

These are **scenario opportunities**, not a claim that all five faults have already been injected and fully validated in this 75-device deliverable. The Branch G single-uplink failover behaviour has been tested on the running topology.

## 8. Current Limitations and Next Steps

- Configure and test real DNS and application services on `intdns1` and `intapp1`.
- Define the intended management use case and any management-specific access restrictions or services.
- Create reproducible fault injection and restoration procedures, preferably in separate scenario copies so the clean base remains intact.
- Add user reports, expected symptoms, ground truth, diagnosis and repair steps, and post-injection validation for each selected fault.
- Expand testing coverage to include fault recovery, additional cross-zone paths, and any relevant non-functional requirements.
- Evaluate integration with the team's benchmark workflow only after that integration is implemented and verified.

## 9. Related Files

- `lab.conf` — Kathará network connections and device declarations
- `*.startup` — interface, route, and service startup configuration
- `r*/etc/frr/frr.conf` — OSPF/EIGRP routing configuration
- `dmzdns1/etc/dnsmasq.d/dmz.conf` — DMZ DNS records and settings
- `dmzweb1/var/www/html/index.html` and `dmzweb2/var/www/html/index.html` — HTTP test pages
- `USE_CASE.md` — existing use-case document (review/update as the new zones are finalised)
- `TEST_CASE.md` — existing test-case document (review/update to reflect executed 75-device tests)

---

**Status:** 75-device network expansion implemented and the listed connectivity/routing checks passed. Full service coverage, comprehensive fault scenarios, and benchmark integration remain future work.
