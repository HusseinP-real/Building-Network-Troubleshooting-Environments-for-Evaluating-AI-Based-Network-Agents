# Independent Enterprise Topology

A standalone network troubleshooting lab: **10 FRR routers, 25 independent VLAN-aware Linux switches, 40 endpoints, and 108 point-to-point links**. Each of the 75 devices has its own Docker image tag and runs in its own Kathara-managed Docker container. All source and runtime reports are contained in this directory. The customer's repository is not a dependency.

The 75-device version was validated on 2026-10-08: **222/222 health checks and 20/20 fault assertions passed**, with all 75 containers running. See [runtime validation](docs/validation.md).

## Quick start

Requirements: Python 3, Docker running, and Kathara. No Python packages, API keys, or LLM subscriptions are needed. The initial image build needs Internet access. Runtime networks are isolated; no host ports or home directories are exposed by the launcher.

```bash
# From the repository root:
cd enterprise-topology
python3 lab.py build
python3 lab.py start
```

`build` creates a shared `enterprise-topology:base` layer and 75 distinct images (`enterprise-topology:r1`, `enterprise-topology:s1`, `enterprise-topology:staff`, and so on). Each dedicated image contains that device's startup script and label; Kathara supplies its configuration directory and runs the matching startup script from this lab. `start` launches 75 separate containers, waits 45 seconds for protocol convergence, and runs health checks. Provision Docker Desktop with enough memory and CPU for 75 containers; if a slow machine needs longer to converge, rerun `python3 lab.py check`. Read failing startup logs before assuming that extra waiting will help.

If the older lab is running, stop it with `python3 lab.py stop` before launching the regenerated topology. Rebuild images after changing startup scripts or the Dockerfiles.

```bash
python3 lab.py status
python3 lab.py check
python3 lab.py exec r1 vtysh -c 'show ip ospf neighbor'
python3 lab.py exec r5 vtysh -c 'show ip route'
python3 lab.py exec s1 bridge vlan show
python3 lab.py exec s3 bridge link show
python3 lab.py exec office ip -4 addr show eth0
python3 lab.py exec office curl -i http://app.enterprise.test/
python3 lab.py exec r5 cat /var/log/enterprise-startup.log
```

To stop and remove **only this lab's** containers and virtual links:

```bash
python3 lab.py stop
```

Source files and saved reports remain on disk. Runtime device changes are ephemeral. To apply persistent source changes, stop and start this lab. Do not use a global Kathara wipe or Docker prune.

## Network structure

| Component | Routers | Switches | Purpose |
|---|---|---|---|
| Backbone, Area 0 | r1-r2 | - | Redundant core |
| Shared services, Area 0 | r3-r4 | s13-s15 | DMZ, DNS/DHCP, operations |
| Headquarters, Area 10 | r5-r6 | s1-s4, s16-s19 | Staff and guests |
| Branch, Area 20 | r7-r8 | s5-s8, s20-s22 | Office and engineering |
| Data center, Area 30 | r9-r10 | s9-s12, s23-s25 | Application and database simulator |

Every regional router connects to both cores. Each region has a distribution-switch pair and multiple dual-homed access switches. STP prevents Layer 2 loops. Keepalived runs VRRP, with virtual gateway `.1`, primary router `.2`, and backup `.3` in each VLAN. OSPF distributes subnet routes across areas. VLAN gateways are passive OSPF interfaces.

The original `staff`, `guest`, `office`, and `engineering` endpoints receive DHCP leases. The 31 new endpoints use unique static addresses in their VLANs; the five original service endpoints remain static. Consult [the design](docs/design.md), [interface table](docs/interfaces.csv), and [inventory](inventory.json).

## Services and access policy

- DNS: `infra`, 10.40.20.10, resolves the local `enterprise.test` names only.
- DHCP: centralized dnsmasq; regional routers relay requests, including explicit relay allowances in the guest policy.
- Application: `app.enterprise.test`, 10.30.10.10:80. Each request calls the backend. Returns HTTP 200 when healthy and HTTP 503 when its backend is unavailable.
- Database simulator: 10.30.20.10:8080, a lightweight HTTP server, not SQL or a production database.
- DMZ: `dmz.enterprise.test`, 10.40.10.10:80.
- Guests may query DNS and access DMZ HTTP; other routed guest traffic is rejected.
- The database permits application TCP/8080 and operations access. Other routed database access is rejected.
- Switches are inspected through Kathara commands; they do not have IP management interfaces in v1. Operations can reach router loopbacks, but this is in-band management, not a separate management fabric.

## Reversible fault experiments

Run one fault at a time, starting from a passing health check.

```bash
python3 lab.py fault inject core-uplink
python3 lab.py exec staff curl -i http://app.enterprise.test/
python3 lab.py fault repair core-uplink

python3 lab.py fault inject gateway-service
python3 lab.py exec r6 ip -4 addr
python3 lab.py fault repair gateway-service

python3 lab.py fault inject database-acl
python3 lab.py exec office curl -i http://app.enterprise.test/
python3 lab.py fault repair database-acl
python3 lab.py check
```

Allow several seconds after injection or repair for routing and VRRP to converge. `core-uplink` disables r5 eth0; its second core connection should preserve application reachability. `gateway-service` stops keepalived on r5, testing virtual gateway takeover, not total router failure. `database-acl` rejects app-to-backend TCP/8080, causing HTTP 503 while the backend remains accessible from operations.

The full baseline check intentionally reports a fault while one is active (for example, a missing neighbor or VRRP process). Use scenario-specific assertions to judge expected degraded behavior.

Automated fault verification applies each fault, verifies its state and impact, repairs it in a `finally` block, and checks recovery:

```bash
python3 tools/verify_faults.py
python3 lab.py check
```

Abruptly terminating the verifier can interrupt repair; use the matching repair command or stop/start the lab before the next experiment.

## SADE diagnosis and ground truth

`tools/sade_eval.py` runs SADE against one injected fault at a time, compares its final resource and fault type with hidden ground truth, and repairs the lab. See the [SADE evaluation guide](docs/sade-evaluation.md) for setup, commands, result format, and the limits of this local scoring workflow.

## Files and reproducibility

| File | Purpose |
|---|---|
| `lab.conf` | Kathara node, link, per-device image, and network sysctl definitions |
| `Dockerfile.device` | Per-device image label and startup-script snapshot, built on the common base |
| `*.startup` | Device initialization |
| `r*/etc/frr/frr.conf` | OSPF configuration |
| `r*/etc/keepalived/keepalived.conf` | VRRP configuration |
| `infra/etc/dnsmasq.conf` | DNS and DHCP configuration |
| `app/srv/app.py` | Application with a real backend dependency |
| `tools/generate.py` | Deterministic source generator for topology and device files |
| `lab.py` | Scoped lifecycle, inspection, health checks, fault actions |
| `results/latest-health.json` | Most recent health-check evidence |
| `results/fault-verification.json` | Most recent automated fault evidence |

`python3 tools/generate.py` rewrites generated files. Edit the generator for persistent structural changes. Regeneration alone does not modify running containers. The Dockerfile uses the available upstream FRR image and Debian package repositories; future rebuilds may change package versions. See the validation report for the versions tested here.

## Scope and references

This is an independently authored implementation inspired by the network-lab and fault-verification approach of [NIKA](https://github.com/sands-lab/nika). It does not copy the customer's local labs and is not yet registered as a NIKA scenario. BGP, external connectivity, a real database engine, and LLM evaluation are outside v1.

Implementation references: [Kathara lab configuration](https://www.kathara.org/man-pages/kathara-lab.conf.5.html), [Kathara directory structure](https://www.kathara.org/man-pages/kathara-lab-dirs.7.html).
