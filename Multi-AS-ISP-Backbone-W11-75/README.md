# Multi-AS ISP Backbone – SOFT3888 Week 11 (75 devices)

**Status: generated configuration, statically validated only. NOT run in Kathara, and NOT verified with SADE.**

## Purpose & distinctiveness

An ISP-style network instead of a campus/enterprise core/distribution/access design. Five Autonomous Systems: three provider/transit backbones and two customer ASes. 30 FRRouting routers (6 per AS), 45 Linux end hosts (9 per AS), 75 individual Kathara devices. All internal links are point-to-point; no invented L2 switch devices. 40 internal router links, 45 access links, 10 inter-AS eBGP links = **95 links**. Providers use IS-IS L2, customers use OSPF area 0, all ASes run an iBGP full mesh, and selected border routers use eBGP. Addresses/links are documented in topology.json.

## Requirements / Mac

- Docker Desktop and Kathara CLI configured for Docker.
- Docker images `kathara/frr` (routers) and `kathara/base` (hosts); enough memory to run 75 containers. Test a subset before a full start.
- FRR image must include `vtysh`, `isisd`, `bgpd`, `ospfd` and `/etc/init.d/frr`. Version differences may require startup changes.
- The project intentionally does not invent an SADE launch command.

## Quick start

```bash
cd Multi-AS-ISP-Backbone-W11-75
python3 scripts/validate_static.py
bash scripts/start.sh
# wait for convergence and inspect routers
bash scripts/exec.sh as65010r1 vtysh -c 'show bgp summary'
bash scripts/exec.sh as65010r1 vtysh -c 'show isis neighbor'
bash scripts/baseline.sh
# Fresh clean baseline, then controlled injection
bash scripts/scenario.sh inject S04
bash scripts/exec.sh as65200r1 ip route get 10.10.1.2
bash scripts/scenario.sh recover S04
bash scripts/stop.sh
```

## Topology and routing

AS65010 ISP North, AS65020 ISP South and AS65030 Transit use IS-IS level 2. AS65100 Customer East and AS65200 Customer West use OSPF. Each AS contains a ring plus two cross-links, six routers, nine hosts; border routers have independent eBGP interfaces. Internal iBGP peers are loopbacks carried by the IGP. Local /16 prefixes are originated at all routers using a high-metric blackhole aggregate route; longest-prefix routing prefers specific internal routes. This avoids needing route redistribution from a host subnet into BGP, but **verify FRR accepts and advertises the aggregate on your installed version**.

`topology.json` is the authoritative device/port/IP/link inventory. Host addresses: AS index 10/20/30/40/50, `10.<index>.1.<...>`; router loopbacks `10.<index>.255.1..6`.

## Experiments

S01 IS-IS adjacency down; S02 eBGP peering administratively shut; S03 OSPF internal link down; S04 high-priority route blackhole; S05 single-origin prefix withdrawal; S06 healthy false-premise ticket; S07 wrong-device ticket; S08 combined IS-IS + blackhole (manual two-step composition). See `scenarios/Sxx/ground_truth.json` and `ticket.txt`. **These are unvalidated scenarios; failover means some disruptions will not manifest as user-visible outages.**

## Scope and limitations

- Baseline script checks only selected connectivity and router outputs; it does not prove every device works.
- No live SADE/NIKA MCP adapter: mapping to your specific repo version is required, described in `docs/EVALUATION.md`.
- **Do not claim** 75 successful runtime containers, fault reproduction, or SADE accuracy until live results are collected.
- Don't compare scores with FaulT-Bench unless tool interface, model, turn budget, evaluation protocol and number of passes are controlled.
