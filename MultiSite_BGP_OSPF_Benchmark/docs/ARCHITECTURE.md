# Network Architecture and IP/AS Planning

## 1. Design objectives and boundaries

A large, reproducible enterprise/WAN topology for network troubleshooting experiments with multiple sites and two logically separate ISP providers. This is a standalone Kathara lab, not a claim of NIKA/OwnTopologies compatibility.

## 2. Device inventory

| Category | Number | Devices / roles |
|---|---:|---|
| Enterprise border routers | 4 | `e1`, `e2`, `e3`, `e4` |
| Enterprise site routers | 8 | `hq_r1/r2`, `ba_r1/r2`, `bb_r1/r2`, `dc_r1/r2` |
| ISP routers | 6 | `a1/a2/a3` and `b1/b2/b3` |
| Linux bridge switches | 20 | 6 HQ, 4 Branch A, 4 Branch B, 4 DC, 2 ISP access |
| Hosts / HTTP servers | 42 | 14 HQ, 9 Branch A, 9 Branch B, 8 DC, 2 external HTTP services |
| **Total** | **80** | 18 routers + 20 switches + 42 endpoints |

## 3. Autonomous systems and routing protocols

| AS | Name | Routers | IGP | Exterior routing |
|---|---|---|---|---|
| 65000 | Enterprise | `e1`–`e4`, and eight site routers | OSPF area 0 | eBGP on four border links |
| 65010 | ISP-A | `a1`, `a2`, `a3` | OSPF area 0 | eBGP with enterprise `e1`/`e3` |
| 65020 | ISP-B | `b1`, `b2`, `b3` | OSPF area 0 | eBGP with enterprise `e2`/`e4` |

OSPF area 0 is used within **each separate AS**, not a shared cross-AS OSPF domain. Prefix exchange across AS boundaries is done with eBGP.

## 4. Address plan

| Function | Network(s) | Assignment convention |
|---|---|---|
| HQ LAN | `10.10.10.0/24` | `hq_r1=.1`, `hq_r2=.2`, hosts `.21` onward |
| Branch A LAN | `10.20.10.0/24` | `ba_r1=.1`, `ba_r2=.2`, hosts `.21` onward |
| Branch B LAN | `10.30.10.0/24` | `bb_r1=.1`, `bb_r2=.2`, hosts `.21` onward |
| Data Center LAN | `10.40.10.0/24` | `dc_r1=.1`, `dc_r2=.2`, hosts `.21` onward |
| Enterprise routed P2P | `10.255.1.0/31` to `10.255.12.0/31` | Two IPs per routed link |
| ISP-A IGP P2P | `172.20.1.0/31`, `172.20.2.0/31` | `a1–a2–a3` |
| ISP-B IGP P2P | `172.21.1.0/31`, `172.21.2.0/31` | `b1–b2–b3` |
| eBGP P2P | `172.31.1.0/31` to `172.31.4.0/31` | Four enterprise↔ISP adjacencies |
| ISP-A HTTP subnet | `198.18.10.0/24` | Gateway `.1`, service `198.18.10.10:8080` |
| ISP-B HTTP subnet | `198.18.20.0/24` | Gateway `.1`, service `198.18.20.10:8080` |
| Enterprise advertised aggregate | `10.0.0.0/8` | Null0-backed BGP origin at enterprise edges |
| Router ID | `10.254.0.x` | Derived deterministically from router order |

`198.18.0.0/15` is reserved for benchmarking; in this project these addresses are only simulated inside the lab. AS65000/65010/65020 are private ASNs. The authoritative interface-to-IP mapping is the generated `inventory.json`.

## 5. Exact routed adjacency (20 P2P links)

```text
Enterprise ring (4): e1--e2, e2--e3, e3--e4, e4--e1
Enterprise site links (8):
  e1--hq_r1, e2--hq_r2
  e2--ba_r1, e3--ba_r2
  e3--bb_r1, e4--bb_r2
  e4--dc_r1, e1--dc_r2
ISP internal links (4): a1--a2, a2--a3, b1--b2, b2--b3
eBGP inter-AS links (4): e1--a1, e3--a3, e2--b1, e4--b3
TOTAL: 4 + 8 + 4 + 4 = 20
```

## 6. Layer-2 access model

Each site has a shared LAN collision domain and multiple access collision domains attached to Linux bridges. Each endpoint has a static `/24` IP and default gateway `.1`. Router2 `.2` has a LAN address but **VRRP is absent**; endpoint gateway failover is not automatic. Linux bridge behavior should not be described as VLAN trunking or STP-tested redundancy.

## 7. Design trade-offs and current limitations

1. A redundant enterprise edge ring and two ISP domains allow meaningful routing / path isolation experiments.
2. ISP-A service disruption in F01/F02 requires changing both ISP-A border peers because one surviving peering could maintain reachability.
3. Coarse `10.0.0.0/8` aggregate routing simplifies the proof of concept but is less realistic than explicit per-site BGP advertisements.
4. Application services are minimal Python HTTP endpoints, not production-tier services.
5. This is a static single-configuration topology; systematic topology scaling comparisons and independent repeated trials are future work.
