# Use cases and test cases

## Use cases

| ID | Report mapping | Actor and goal | Flow and acceptance criteria |
|---|---|---|---|
| UC01 | US1, FR1 | Developer deploys a complex environment | Copy Kath3, launch it and verify all 32 named devices accept commands. Check the nominated baseline paths before any fault. |
| UC02 | US2, FR2 | Evaluator verifies a healthy network | Laptop0 reaches gateway, PC4 and Router2; PC4 reaches Router2. Route and experimental rule state match baseline. |
| UC03 | US3, FR3 | Evaluator introduces one controlled fault | Inject gateway-only or filter-only case. Expected affected paths fail while controls work. Repeated injection creates no duplicate filter. |
| UC04 | US4 | Evaluator changes configuration and restores service | Restore only the gateway in the compound case; PC4 recovers but Router2 stays filtered. Remove the tagged filter and verify the full baseline. |
| UC05 | US5, FR4 | Evaluator audits the root cause | Compare scenario ground truth with route/rule snapshots, probe results and filter counters. Keep diagnosis evidence separate from tickets. |
| UC06 | FR5 preparation | Evaluator challenges an inaccurate user report | Healthy false-premise ticket claims failure; verification finds healthy probes and no injected fault. Agent response evaluation remains a later step. |
| UC07 | FR6 preparation | Developer prepares agent evaluation | Resolve the four native scenarios through the new manifest. Actual agent traces and scoring remain unexecuted in this update. |

## Test cases

All new live cases start as NOT RUN. Offline parser and unit-test passes do not change that status.

| ID | Procedure | Expected result and evidence |
|---|---|---|
| TC01 | Offline check-only | Four IDs resolve uniquely; injection shells parse; check devices belong to Kath3. |
| TC02 | Deploy temporary Kath3 | 32 nodes accept commands; correct gateway and no experimental filter; baseline paths succeed twice consecutively. |
| TC03 | Run healthy control | No injection occurs; the failure allegation is unsupported by healthy checks. |
| TC04 | Inject wrong gateway | Gateway .1 remains reachable; PC4 and Router2 fail from Laptop0; PC4 still reaches Router2. |
| TC05 | Inject filter only | Gateway and PC4 work from Laptop0; Router2 fails only on the affected path; PC4's control works. |
| TC06 | Inject compound, then repair gateway | Both off-subnet targets initially fail. PC4 recovers after gateway repair; Router2 remains blocked and tagged DROP counter increases. |
| TC07 | Repeat injection | Route remains at the intended value; exactly one tagged rule exists when filtering is expected. |
| TC08 | Restore after each fault | Correct route, no tagged filter and all nominated paths healthy again. |
| TC09 | Three complete cycles | Every case, partial repair and recovery repeats; retain the unique JSON report. |
| TC10 | Repeat a fresh invocation | Fresh deployment reproduces baseline and faults; distinguish startup failure from intended injected failure. |
| TC11 | Offline error-handling tests | Baseline failure blocks injection; fault-check failure still attempts repair; transport/tool errors cannot pass. |
| TC12 | Agent integration | NOT RUN: external setup, actual agent trace and judge result required. |

## Connectivity matrix

| State | Laptop0 → gateway | Laptop0 → PC4 | Laptop0 → Router2 | PC4 → Router2 |
|---|---|---|---|---|
| Healthy | success | success | success | success |
| Wrong gateway | success | failure | failure | success |
| Filter only | success | success | failure | success |
| Compound | success | failure | failure | success |
| Compound with gateway repaired | success | success | failure | success |
| Recovered | success | success | success | success |

The wrong-gateway and compound ping patterns are the same initially. Configuration evidence and partial repair distinguish them. ICMP failures alone do not establish an HTTP/DNS outage. Coverage is the documented path matrix, not every pair of endpoints in the 32-device network.
