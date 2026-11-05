# Enterprise-SADE-W11: 75-device Kathara troubleshooting benchmark (candidate)

**Status: generated and statically validated; NOT deployed or end-to-end tested.**

## Network inventory

| Type | Count |
|---|---:|
| ISP routers | 2 |
| BGP edge routers | 4 |
| OSPF core routers | 6 |
| Distribution routers | 8 |
| Linux bridge switches | 10 |
| Client hosts | 35 |
| Service hosts | 10 |
| **Total** | **75** |

There are 5 high-level zones (HQ, 3 branches, DC) with 10 LANs. Every device has a `lab.conf` entry, its own startup file, and independently defined interfaces. Switches are separate Linux bridge containers, not merely Kathara collision domains.

## Requirements

- macOS or Linux; Docker Engine / Docker Desktop; Kathara CLI installed
- Images: `kathara/frr:9`, `kathara/base:latest`, `kathara/dnsmasq:latest`
- Assign enough Docker Desktop memory for 75 containers. Actual usage is unknown until tested.

## Run

```bash
python3 scripts/validate_static.py
./scripts/start.sh
# Allow routing to converge, then:
./scripts/baseline.sh
./scripts/inject_F03_dns_down.sh
kathara exec -d lab pc01 -- dig @10.20.9.10 web.corp.test
./scripts/recover_F03_dns_down.sh
./scripts/stop.sh
```

If DNS is unavailable, confirm `dnsmasq` is supported in the chosen image. HTTP server requires `python3` installed in `kathara/base`. All dependency assumptions must be checked on actual images.

## Protocol design

- OSPF area 0 on core ring, redundant edges, and dual-homed distribution routers.
- eBGP between ISPs and edges (AS64500/64501 and AS65001–65004).
- Edge routers redistribute BGP learned routes into OSPF; ISPs learn enterprise `10.0.0.0/8` through BGP (static discard summary is used only as a fallback, while specific OSPF routes take precedence).
- Ten access segments `10.20.1.0/24`–`10.20.10.0/24`.
- `srv01=10.20.9.10` DNS; `srv02=10.20.9.11` HTTP port 8000.

## Scenario design

Eight preliminary examples are in `scenarios/`. Injection and recovery scripts in `scripts/` are *candidates* until verified by post-injection probes. `F07_second_fault` is intended to be combined with `F03_dns_down` for multi-fault testing. `F06_false_premise` deliberately injects nothing. The other planned categories (ACL, route blackhole, wrong cause, failover) require further implementation and are NOT included as working scenarios.

For clean experiments, use a **freshly launched lab for each scenario**; run baseline, inject, verify fault and symptoms, present only ticket and topology summary to SADE, record tool calls, then score diagnosis and recover/clean. Never show the scenario's ground truth or injection command to the agent.

## SADE integration

SADE builds on NIKA. This package does **not** claim to contain a functional bridge to your specific SADE checkout. First confirm how your NIKA version registers custom labs, provides tool access, and parses scenarios. `scenarios/*/scenario.json` contains the evaluation inputs for an adapter (not NIKA's native scenario schema). Do not report measured accuracy until actual diagnostic executions have been logged.

Suggested metrics: detection accuracy, device localisation, root-cause accuracy, multi-fault recall, false positive rate, wall-clock time, tool calls, API cost. For false-premise cases, correct output is `is_anomaly=false`.

## Notes on repeatability

- Startup scripts under `lab/` are designed for Kathara; they are **not** executed by `docker compose`.
- Each OSPF router has multiple redundant links; verify individual OSPF adjacency and BGP peer establishment before making research claims.
- This configuration is a starting point, not a tested 75-container production benchmark.
- Results should be based on >=3 independent runs per scenario if resources permit.

## Sources

- https://www.kathara.org/man-pages/kathara-lab.conf.5.html
- https://www.kathara.org/man-pages/kathara-exec.1.html
- https://docs.frrouting.org/en/latest/vtysh.html
- https://github.com/Overlxrd-uwu/SADE-NetworkAgent
- https://arxiv.org/abs/2608.27021
