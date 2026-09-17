# Runtime validation

Validated on 2026-09-16T05:23:59.460884+00:00.

## Environment

- Host: macOS with Docker Desktop 4.88.1, ARM64 containers.
- Docker Engine: 29.7.2; Linux kernel: 7.0.12-linuxkit.
- Kathara: 3.8.3.
- FRRouting: 10.5.3.
- dnsmasq: 2.90; keepalived package: 2.2.7.
- Lab image: enterprise-topology:1.
- Image identifier: sha256:f99d08c0348c71ab1e2f41b4e12545889b91c927f8a0ceeb280858ca9c82a761.

## Results

- 34 devices deployed: 10 routers, 15 switches, 9 endpoints.
- 57 separate two-endpoint links deployed.
- 99/99 final health checks passed after all faults were repaired.
- 20/20 fault experiment assertions passed across three scenarios.
- All 34 nodes reported READY at handover; the lab is left running for inspection.

Health checks cover device startup, every expected OSPF neighbor, VLAN-aware STP bridges, blocked redundant access ports, four DHCP clients, DNS, application/backend HTTP, guest isolation, backend access restrictions, router loopback reachability, and expected primary/backup virtual gateway ownership.

## Fault evidence

| Scenario | Verified degraded state | Verified business outcome | Recovery |
|---|---|---|---|
| Core uplink | r5 eth0 down; two OSPF neighbors remain Full | Staff can still access the application and backend | Interface restored; application healthy |
| Gateway service | r5 keepalived stopped; virtual gateway moves to r6 | Staff can still access the application and backend | keepalived restarted; primary ownership restored |
| Database ACL | Explicit TCP/8080 rejection on app | Application returns HTTP 503; operations still reaches the backend | Rule removed; application returns healthy response |

These tests demonstrate eventual recovery and reachability, not zero packet loss or measured convergence performance. Gateway testing stops the VRRP service rather than powering off the entire router. The backend is an HTTP dependency simulator, not a database engine. Full switch outages, all combinations of multiple faults, NIKA adapters, BGP, and agent evaluation have not been tested or implemented.

## Evidence files

- [Final health report](../results/latest-health.json)
- [Fault report](../results/fault-verification.json)
- Earlier timestamped health files retain the initial failed iterations; latest-health.json is the final baseline.

## Implementation corrections discovered during validation

Container network sysctls are set in lab.conf at creation time because the runtime /proc/sys mount is read-only. Guest-policy exceptions explicitly permit DHCP relay traffic from the gateway router addresses. Every regional router has two Area 0 core uplinks, so failure of one uplink does not depend on learning inter-area routes through a non-backbone area.
