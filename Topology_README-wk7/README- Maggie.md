# Kath5 Jiayuan Extended Network Topology

## Overview

This topology extends the original Kath5 topology in FaulT-Bench to create a larger and more realistic network troubleshooting environment.

The original Kath5 topology contains 15 devices, including 13 routers (`r1`–`r13`) and two end hosts (`pc0` and `pc12`). The extended topology contains **50 devices** while preserving the original routing structure and adding multiple branch networks and a central Server Zone.

The topology is designed to support connectivity testing, routing fault injection, and the development of troubleshooting scenarios for evaluating AI-based network agents.

---

## Topology Extension

The original Kath5 routing infrastructure was retained and extended with additional end devices.

The extended topology contains:

- Original Kath5 infrastructure: 13 routers and 2 hosts
- Branch A: 6 hosts (`a1`–`a6`) connected through `r7`
- Branch B: 6 hosts (`b1`–`b6`) connected through `r8`
- Branch C: 6 hosts (`c1`–`c6`) connected through `r9`
- Branch D: 6 hosts (`d1`–`d6`) connected through `r10`
- Branch E: 7 hosts (`e1`–`e7`) connected through `r12`
- Server Zone: 4 servers (`web1`, `dns1`, `db1`, and `file1`) connected through `r13`

This results in a total of **50 Kathará devices** and **29 collision domains**.

The new networks include:

| Network | Gateway | Connected Devices |
| --- | --- | --- |
| Branch A – `70.0.0.0/8` | `r7` – `70.1.1.1` | `a1`–`a6` |
| Branch B – `80.0.0.0/8` | `r8` – `80.1.1.1` | `b1`–`b6` |
| Branch C – `90.0.0.0/8` | `r9` – `90.1.1.1` | `c1`–`c6` |
| Branch D – `100.0.0.0/8` | `r10` – `100.1.1.1` | `d1`–`d6` |
| Branch E – `120.0.0.0/8` | `r12` – `120.1.1.1` | `e1`–`e7` |
| Server Zone – `130.0.0.0/8` | `r13` – `130.1.1.1` | `web1`, `dns1`, `db1`, `file1` |

The topology continues to use the routing protocols already present in Kath5, including OSPF and EIGRP.

---

### Device Configuration

The newly added devices use similar basic network configurations.

- **Branch hosts** (`a1`–`a6`, `b1`–`b6`, `c1`–`c6`, `d1`–`d6`, and `e1`–`e7`) have similar startup configurations, including an IP address, an active network interface, and a default gateway. Devices within the same branch mainly differ by their IP addresses.
- **Server Zone devices** (`web1`, `dns1`, `db1`, and `file1`) also use similar basic network configurations. They use different IP addresses and share the same default gateway through `r13`.

The specific configurations are:

1. **Branch A (`a1`–`a6`)**: connected to `r7` on the `70.0.0.0/8` network, with `70.1.1.1` as the default gateway.
2. **Branch B (`b1`–`b6`)**: connected to `r8` on the `80.0.0.0/8` network, with `80.1.1.1` as the default gateway.
3. **Branch C (`c1`–`c6`)**: connected to `r9` on the `90.0.0.0/8` network, with `90.1.1.1` as the default gateway.
4. **Branch D (`d1`–`d6`)**: connected to `r10` on the `100.0.0.0/8` network, with `100.1.1.1` as the default gateway.
5. **Branch E (`e1`–`e7`)**: connected to `r12` on the `120.0.0.0/8` network, with `120.1.1.1` as the default gateway.
6. **Server Zone (`web1`, `dns1`, `db1`, `file1`)**: connected to `r13` on the `130.0.0.0/8` network. Each server uses a different IP address within this network and shares `130.1.1.1` as the default gateway.

---

## Use Cases

Several representative use cases were defined in `USE_CASE.md` to describe how the topology may be used in realistic network scenarios.

The use cases include:

1. **Branch User Accesses Server Zone**  
   A user in Branch A accesses a service in the central Server Zone, for example `a1` communicating with `web1`.

2. **Network Engineer Verifies Cross-Branch Connectivity**  
   A network engineer verifies connectivity between different branch networks, such as `a1` and `b1`.

3. **EIGRP Branch User Accesses Server Zone**  
   A user in Branch E accesses the Server Zone, providing a scenario involving the EIGRP side of the topology.

4. **Server Communicates with Remote Branch**  
   A server in the Server Zone communicates with a remote branch device, such as `web1` communicating with `a1`.

5. **Network Engineer Verifies End-to-End Routing**  
   A network engineer uses tools such as `traceroute` to inspect the complete multi-hop routing path between different parts of the network.

---

## Test Cases

The extended topology was deployed and tested using Kathará.

The test cases are documented in `TEST_CASE.md` and include:

- Full topology deployment
- Local gateway connectivity
- Cross-branch connectivity
- Branch A to Server Zone connectivity
- Branch E to Server Zone connectivity
- Server Zone to Branch A connectivity
- End-to-end routing path verification using `traceroute`

The full topology was successfully deployed with:

- **29/29 collision domains**
- **50/50 devices**

Representative connectivity tests successfully verified communication between different branches and the Server Zone.

For example, the tested path from `web1` to `a1` was:

`web1 → r13 → r11 → r3 → r4 → r6 → r7 → a1`

This demonstrates end-to-end communication across multiple parts of the topology.

---

## Configuration Change and Fault Scenario

A routing fault scenario was developed based on the extended topology.

The fault is located on **r13**, which connects the central Server Zone to the EIGRP routing domain.

Under normal operation, the EIGRP configuration on `r13` contains:

```text
router eigrp 100
 network 103.0.0.0/8
 network 130.0.0.0/8
```
The fault removes: network 130.0.0.0/8

As a result, r13 no longer advertises the Server Zone network through EIGRP.
The fault was verified by testing that:
web1 can still reach its local gateway 130.1.1.1
a1 can no longer reach web1
a1 can still reach b1
Therefore, the fault affects remote reachability to the Server Zone while other parts of the network remain operational.

A separate fault topology is provided in: Kath5_Jiayuan_R13_EIGRP_Fault

The detailed fault description and verification results are documented in FAULT_SCENARIO.md.

## NIKA as a Reference
Existing NIKA scenarios in the FaulT-Bench dataset were reviewed as a reference for structuring network troubleshooting scenarios.

In particular, the following NIKA scenario was used as a reference:
ospf-enterprise-dist1-network-statement-removed.txt

This scenario represents a routing fault caused by removing an OSPF network statement. Although the extended Kath5 scenario uses EIGRP rather than OSPF, both scenarios involve a routing network statement being removed and a network no longer being advertised.

Following the NIKA scenario structure, the R13 fault scenario includes:
PROMPT-TO-AGENT
INJECTION
POST-INJECT-CHECK
GROUND-TRUTH
FIX
DIAGNOSTIC-PROCESS
SCORING-AXES

The corresponding scenario definition is:
r13-eigrp-server-network-statement-removed.txt

NIKA is currently used as a reference for scenario design and structure. This work does not claim that the extended topology has already been integrated into the NIKA evaluation pipeline.

## files
Kath5_Jiayuan_Extended/
├── lab.conf
├── README.md
├── USE_CASE.md
├── TEST_CASE.md
├── router configurations
└── host startup files

Kath5_Jiayuan_R13_EIGRP_Fault/
├── lab.conf
├── FAULT_SCENARIO.md
├── r13-eigrp-server-network-statement-removed.txt
├── modified r13 configuration
├── router configurations
└── host startup files

## Summary

This work extends Kath5 from a relatively small topology into a 50-device network environment with five branch networks and a central Server Zone.

The extended environment provides:
A larger multi-network topology
Representative use cases
Reproducible connectivity test cases
A validated EIGRP routing fault
Ground-truth information for troubleshooting
A NIKA-inspired fault scenario definition

This provides a more comprehensive environment for further network troubleshooting experiments and future evaluation of AI-based network agents.
