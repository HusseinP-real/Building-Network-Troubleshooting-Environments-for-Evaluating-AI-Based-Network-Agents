# 75-device validation — 1 November 2026 (Australia/Sydney)

The expanded topology contains 75 devices: three spines, six leaves, six rack bridges, six servers and 54 clients. Its 84 point-to-point links use 168 interfaces. All 75 startup scripts are checked offline.

The live checker now plans 60×59 = 3,540 directed endpoint pings, 60 application checks, eleven ports per rack bridge, and the original BGP/three-path ECMP checks. Failover repeats every endpoint sweep and application check with two remaining leaf1 paths, then restores the uplink and reruns the baseline.

The six scenario definitions, original device addresses/interfaces, original 48 wire identities, and router configurations are preserved. New clients h5–h10 use .15–.20 in each existing rack subnet.

Offline validation passed: `python lab.py validate` parsed 75 devices and 84 links with Kathara integrity checks; `python -m unittest discover -s tests -v` passed all nine regressions. Both SVG and PNG diagrams were regenerated and visually reviewed. Docker reported that its daemon was unavailable, so 75-device live connectivity and failover have not been validated. The saved latest-health.json, latest-failover.json and environment.json below describe the historical 39-device run only; they are not evidence for this expansion. Reproduce with the README commands.

## Historical 39-device live validation

# Recorded validation — 19 October 2026 (Australia/Sydney)

This report applies to **DatacenterFabric**, not another topology's historical reports. Live validation ran from the added directory in the team repository with 39 Kathara-managed Docker containers.

| Verification | Result | Evidence |
| --- | --- | --- |
| Structure and addressing | 39 devices; 48 links; 96 unique link interfaces; connected graph | `results/structural-validation.json` |
| Startup shell syntax | All 39 scripts passed `bash -n` | Structural validator |
| Kathara parsing and integrity | 39 devices and 48 links parsed successfully | `python lab.py validate` |
| Live baseline | **162/162 checks passed** | `results/latest-health.json` |
| BGP | All 36 directed peer sessions established and receiving prefixes | Nine BGP assertions in health report |
| ECMP | Three installed next hops for all 30 leaf→remote-rack routes | Thirty kernel route assertions in health report |
| Endpoint connectivity | **552/552 directed pairs reachable** (24×23) | 24 endpoint sweep assertions in health report |
| Application/backend | Healthy application response from all 24 endpoints | 24 HTTP assertions in health report |
| Rack HTTP endpoints | Six services accessible from rack1h2 | Six HTTP assertions in health report |
| Link failover | **56/56 assertions passed**; all endpoint pairs and application checks remained healthy after convergence | `results/latest-failover.json` |
| Recovery | Restored leaf1 eth0 and **162/162 baseline checks passed again** | Failover recovery flag and latest health report |
| Offline regressions | **6/6 tests passed** | `python -m unittest discover -s tests -v` |

During failover, leaf1 eth0 was administratively down and each remote rack route on leaf1 retained two installed next hops. The verifier restored the interface in `finally`. This demonstrates reachability after convergence, not zero packet loss during convergence. All pairwise probes are ICMP and the HTTP checks use port 8080; this does not test every transport protocol or traffic load.

The baseline also checks every startup-ready marker, all six five-port bridges, and each endpoint's configured address and gateway. Individual commands and raw outputs are preserved in the JSON evidence. The health report's `endpoint_pairs` field is the planned coverage; the **552/552** conclusion follows from all 24 sweep assertions actually passing.

## Environment and reproduction

The tested SDK is Kathara 3.8.3. Docker was assigned approximately 8 GiB RAM and 11 CPUs. `results/environment.json` records Docker/Python/FRR versions, the immutable built image ID, inventory hash, device count and host mount/port checks. The base image declares anonymous Docker volumes at `/hosthome` and `/shared`; these are not bind mounts of the host home or project shared folder. The provenance recorder distinguishes volume mounts from bind mounts. The system-wide Kathara binary failed with a `pyexpat`/macOS compatibility error; validation used the Kathara Python SDK through the existing SADE virtual environment instead.

Use the README to build and start a fresh lab, then run `check` and `failover`. Successful saved results describe this run and do not imply that a later clone is running. No SADE model was called, no root-cause accuracy was measured, and no API costs were incurred by this topology validation.

The lab is stopped after validation to release local resources. Source, Docker image and reports are retained; run `python lab.py start` to demonstrate it again.
