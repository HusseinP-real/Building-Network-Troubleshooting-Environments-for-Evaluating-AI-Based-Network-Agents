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
