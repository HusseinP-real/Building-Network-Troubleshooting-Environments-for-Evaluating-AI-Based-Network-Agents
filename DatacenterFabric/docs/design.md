# Design, addressing and comparison

## Why a data-centre fabric

The checked-out team repository contains enterprise OSPF/VLAN/VRRP labs, the Abilene/YUMAng IS-IS extension, extended Kath topologies and a multi-site BGP/OSPF benchmark. This new implementation targets **east–west traffic between racks**, with eBGP at every routed hop and forwarding-table checks for three simultaneous next hops.

The comparison is based on the checked-out `main` tree and its member README files. Branch-only implementations may differ. The team repo also contains reference NIKA Clos tickets and frozen results under FaulT-Bench; those reference results are not evidence for this lab.

| Existing material | Focus | Addition in this lab |
| --- | --- | --- |
| EnterpriseTopology / EnterpriseTopology75 | Multi-area OSPF, STP, VLANs, VRRP | eBGP fabric and three active equal-cost spine paths |
| MultiSite_BGP_OSPF_Benchmark | Enterprise sites, ISP boundaries, intra-AS OSPF | No IGP; each rack is a separate AS, with exact export filters |
| Abilene/YUMAng | IS-IS backbone and synthetic site | Rack-based Clos with a full three-spine mesh |
| Extended Kath labs | Branches, gateway/routing faults, server zones | Uniform rack generation, all-pairs endpoint checks and kernel ECMP assertions |

This lab is smaller in device count than the enterprise labs; its contribution is a different routing structure and validation coverage. Six rack switches have one upstream leaf each. Spine redundancy preserves inter-rack paths after an uplink failure, but leaf or rack-switch failure isolates that rack. There is no dual-homed host, EVPN/VXLAN overlay, VLAN tenant isolation or VRRP.

## Routing

All three spines share private AS65000. Leaf N uses private AS65100+N. There is no peering within an AS. A route from rack 6 reaches leaf1 with path `65000 65106` through each of the three spines. The identical path and `maximum-paths 3` permit equal-cost next hops; live validation checks that all three are actually installed in Linux, rather than merely present in BGP's table.

Each BGP neighbor has an explicit inbound and outbound prefix list with `bgp ebgp-requires-policy` enabled. A leaf exports only its own rack `/24` and loopback `/32`, preventing it from becoming a transit path between spines. Each spine accepts exactly the two prefixes owned by each leaf. Spines export only the finite expected fabric prefixes. Network origination requires the connected prefix to exist (`bgp network import-check`). BGP timers are 3/9 seconds; no BFD is configured.

The design follows FRR's documented [ECMP configuration](https://docs.frrouting.org/en/latest/bgp.html#clicmd-maximum-paths-1-128) and [explicit eBGP policy](https://docs.frrouting.org/en/latest/bgp.html#clicmd-bgp-ebgp-requires-policy) behavior. For topology inspiration, see [RFC 7938: BGP in large-scale data centres](https://www.rfc-editor.org/rfc/rfc7938).

## Addresses

| Resource | Address |
| --- | --- |
| Rack N subnet | `10.60.N.0/24` |
| Rack N gateway / leaf `eth3` | `10.60.N.1/24` |
| Rack N endpoints h1–h4 | `10.60.N.11`–`10.60.N.14` |
| Spine S loopback | `10.254.0.S/32` |
| Leaf N loopback | `10.254.1.N/32` |
| Fabric leaf/spine pairs | Sequential `/31`s from `172.22.0.0/31` to `172.22.0.34/31` |
| Application | `10.60.5.11:8080` |
| Backend | `10.60.6.11:8080` |

Fabric pairs are generated in rack order, then spine order. The even `/31` address is assigned to the leaf and odd address to the spine. Leaf eth0/eth1/eth2 connect to spine1/spine2/spine3. Each spine's eth0–eth5 connect to leaf1–leaf6. Rack-switch eth0 goes to its leaf and eth1–eth4 to h1–h4. The machine-readable source of truth is `inventory.json`, with exact ports in `docs/interfaces.csv`.

Each rack bridge is its own Layer 2 segment. Static addresses and gateways make baseline connectivity independent of DHCP/DNS. All endpoints can reach one another; no tenant access isolation is claimed. Linux IP forwarding is enabled only on spines and leaves. ECMP checks prove installed next hops; they do not prove balanced bandwidth or packet-by-packet spreading.
