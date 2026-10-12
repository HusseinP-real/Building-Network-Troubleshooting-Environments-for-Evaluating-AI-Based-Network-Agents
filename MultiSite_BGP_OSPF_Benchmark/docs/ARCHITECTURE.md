# Network Architecture & IP/AS Planning — Design Record

## Requirements traceability

Client requirements from `P20-项目初始客户回答.txt`: ideally 75–100 devices with multiple subnets and protocols; larger topologies; initially single fault; varied user tickets; aspire to roughly ten topologies. This lab delivers an **80-node prototype** and **three single-fault scenarios**, not the final group target of ten.

## Logical routing domains

- AS65000: `e1`–`e4`, `hq_r1/r2`, `ba_r1/r2`, `bb_r1/r2`, `dc_r1/r2`. One OSPF area 0. A four-node edge ring carries redundant enterprise WAN paths.
- AS65010: `a1`–`a3` and external HTTP subnet `198.18.10.0/24`. Internal OSPF, eBGP neighbors at `a1` and `a3` toward `e1` and `e3` respectively.
- AS65020: `b1`–`b3` and external HTTP subnet `198.18.20.0/24`. Internal OSPF, eBGP neighbors at `b1` and `b3` toward `e2` and `e4` respectively.
- No connection between simulated ISPs. The ISP HTTP services are benchmark endpoints; external BGP networks are not actually connected to the Internet.

## P2P design

All 20 routed P2P links use `/31` to avoid wasting addresses. `inventory.json` is the authoritative device-to-device edge table. On a link, the `a` endpoint always receives the .0 address and the `b` endpoint the .1 address. Link identifiers are distinct Kathara collision domains.

## Enterprise LAN design

Each site's router1 owns LAN `.1` and router2 `.2`. Each switch has one uplink on the site's shared LAN collision domain and dedicated collision domains for access hosts. A Linux bridge connects each switch's access interfaces to the site LAN. This models access switching, **not true 802.1Q VLAN trunking or STP redundancy**. Hosts are assigned `.21`, `.22`, etc., with gateway `.1`.

## Exact link adjacency

```text
Enterprise ring: e1-e2, e2-e3, e3-e4, e4-e1
HQ: e1-hq_r1, e2-hq_r2
Branch A: e2-ba_r1, e3-ba_r2
Branch B: e3-bb_r1, e4-bb_r2
Data center: e4-dc_r1, e1-dc_r2
ISP A: a1-a2, a2-a3
ISP B: b1-b2, b2-b3
eBGP: e1-a1, e3-a3, e2-b1, e4-b3
```

## Design decisions / trade-offs

- We chose multiple sites + two independently routed ISP domains to complement an existing internal OSPF enterprise topology, rather than replicate its technology mix.
- Both redundant paths can conceal single-link failures. F01 therefore disables *both* ISP-A ingress sessions to test service disruption; a future hidden-fault scenario should intentionally test only one interface and verify adjacency degradation but service preservation.
- BGP export relies on a coarse enterprise `10.0.0.0/8` aggregate and concrete ISP service prefixes. For rigorous traffic engineering tests, refine this into per-site prefixes, BGP policies and explicit failover route assertions.
- The second site router has no first-hop failover role today. VRRP should be added after baseline routing works.
- Manual fault injection commands modify running state; stopping/restarting nodes resets to generated configs. Document this when running repeated experiments.

## Change-control and repeatability

- `tools/generate.py` is the source of truth for topology and routed configs.
- Regenerate before packaging. Run `tools/validate_static.py` and unit tests before creating PRs.
- Never claim live verification based only on static file checks.
