# P20Enterprise validation evidence

## Version 3: 75 devices, seven sites

On 2026-10-13, **all six scenarios passed one complete live cycle**, including repeated fault injections, exact repairs and two consecutive passing recovery rounds. All 75 devices passed initial address/gateway/forwarding verification. Connectivity probes cover all 50 endpoints; neighbor checks cover all 25 routers. The inventory contains 25 routers, 35 PCs, 15 servers, 47 non-overlapping subnets and eight OSPF areas.

All 34 offline regression tests, generated-file consistency and shell syntax checks passed. Original v2 interfaces, addresses, routing settings and device roles were checked against the previous commit and preserved; new core interfaces connect the added sites.

A three-cycle run was started, then stopped during the second cycle at the user's request to finish sooner. The full run therefore records `passed: false` with `KeyboardInterrupt`; this is not a completed three-cycle PASS. The first complete cycle is verified separately in [v3-live-summary.json](v3-live-summary.json). All six first-cycle cases passed baseline, fault and recovery stages; five injected faults also passed repeated injection. The second cycle additionally passed healthy, failover, isolation, advertisement and server-link with recovery, but gateway recovery was not completed in that cycle.

Scoped cleanup succeeded: all 75 temporary devices and 47 collision domains were removed. Full raw observations and configuration snapshots are saved locally at `faultbench/runs/p20-enterprise/v3-live-validation.json`. Older evidence below applies only to v2. NIKA/SADE agent evaluation was not run.

The installed macOS Kathara binary failed before deployment due to an incompatible bundled `pyexpat` library. Live checks used official Kathara 3.8.3 installed in a temporary Python environment at `/tmp/p20-kathara-env`, with Docker 28.4.0. Until the installed executable is repaired, reproduce with:

```sh
PATH=/tmp/p20-kathara-env/bin:$PATH /tmp/p20-kathara-env/bin/python tools/validate_p20_enterprise.py --repeat 1
```

The temporary environment may be removed by macOS; follow [Kathara's Python installation guide](https://github.com/KatharaFramework/Kathara/wiki/pip) to recreate it if needed.

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
