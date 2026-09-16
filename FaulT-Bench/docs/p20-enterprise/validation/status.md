# P20Enterprise validation evidence

## Version 2: 40 devices, multi-area OSPF

**PASS:** all six scenarios passed three cycles, including repeated injections,
repairs, recovery, final configuration verification and scoped cleanup.
Finished: 2026-09-16T12:31:43.360729+00:00.

- 33 offline tests passed across the P20Enterprise and existing demo validators.
- 157 live check rounds: 140 matching rounds and 17 transient convergence rounds.
- Every required stage ended with two consecutive matching rounds.
- All 40 devices passed initial and final address/gateway/forwarding checks.
- Connectivity probes cover all 24 endpoints; every stage checks all 16 routers' OSPF neighbor counts.
- Failover verifies the backup next hop, followed by restoration of the primary next hop.
- A separate fresh-deployment failover run also passed using the Kathara CLI execution backend.
- Final cleanup returned zero. NIKA/SADE agent evaluation was not run.

[Tracked evidence summary](v2-all-cases-three-cycles.json) includes topology/scenario
hashes, image digests, per-stage outcomes, configuration evidence and the SHA-256
of the full raw report. The full report is saved locally under
`faultbench/runs/p20-enterprise/v2-all-three-cycles-final.json` (ignored by Git). The separate
CLI-backend run is saved beside it as `v2-failover-kathara-cli.json`.

There was temporary packet loss during convergence. These results establish
stable recovery and correct backup routing, not zero-loss failover or an SLA.
An initial CLI trial exposed a route-parser issue with the `nhid` field; it was
fixed and regression-tested before these successful results. Repeated OSPF advertisement
withdrawal also exposed an absent-statement error; the injection now verifies
absence safely, and the final run uses the corrected version. A slower three-cycle
CLI run was deliberately stopped and cleaned before the complete Docker-exec run.

## Version 1: historical evidence only

`20260916-all-cases-three-cycles.json` records the previous nine-device,
static-routing topology and four cases at commit `9d4a351`. It is retained as
historical evidence and does not validate the expanded v2 topology.
