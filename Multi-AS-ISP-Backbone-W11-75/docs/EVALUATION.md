# SADE Evaluation Plan (not an executable integration)

1. Boot fresh Kathara lab and collect `baseline.sh` with its stdout and exit status.
2. For each scenario capture pre-injection control plane: `show bgp summary`, `show ip route`, `show isis neighbor` or `show ip ospf neighbor`.
3. Inject scenario using `scripts/scenario.sh inject Sxx` and **verify fault really manifested**. Fail-over may keep end-to-end ping healthy, so adjacency/route tests matter.
4. Supply **only** ticket plus permitted topology overview to the agent via your NIKA/SADE MCP runner. Do not expose ground truth or injection commands.
5. Parse `is_anomaly`, faulty devices, root cause, proposed fix; store logs, tool count, tokens, runtime, API cost.
6. Compare with hidden ground truth, score presence precision/recall, exact device localization, root-cause accuracy, and over-diagnosis on S06. Repeat ≥3 trials with fresh deployment.
7. Recover or restart, confirm baseline. Keep agent configuration/model/budget constant for controlled comparisons.

**Current state:** no SADE adapter bundled because exact local runner/API schema is not available. Scenarios are design hypotheses and have not been executed against SADE.

`S05` tests removal at a *single* BGP router, not loss of the whole customer's aggregate. `S01` and `S03` represent control-plane link faults with potential redundancy; don't assert host outage without a probe. `S08` is a manual composition of two faults.
