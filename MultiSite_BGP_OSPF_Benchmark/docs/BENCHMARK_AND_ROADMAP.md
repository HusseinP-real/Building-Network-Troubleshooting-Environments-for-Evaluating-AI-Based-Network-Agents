# Benchmark Data, Evaluation Plan and Remaining Work

## Dataset today

- One multi-site topology.
- Three fault scenarios (`F01`, `F02`, `F03`).
- Four agent-facing tickets per fault: **general user**, **network engineer**, **expert operator**, **misleading reporter**.
- Total: **12 prewritten tickets** linked to three distinct ground-truth states.

Tickets reside in `scenarios/FXX/tickets.json`; withheld labels reside in `scenarios/FXX/ground_truth.json`. **Do not expose ground truth to the diagnostic agent.** The current repository uses a project-specific schema; client OwnTopologies schema remains unknown because that repository was unavailable.

## Current evaluation tooling

`tools/evaluate_agent.py` accepts a JSON file of **external predictions** and compares their fault-presence, fault-type and exact fault-device-set fields with ground truth. This is an **offline scorer**, not SADE integration. Free-text root-cause semantics and correctness of proposed repairs are **not** automatically proven by that script.

## Proposed SADE experiment, not yet run

1. Ensure a healthy baseline and inject one fault.
2. Present a ticket **without** ground truth to the agent.
3. Expose a bounded, read-only set of diagnostic tools (`ping`, routes, OSPF/BGP observations).
4. Log model/version, tools, full observations, timestamps, agent answer and resource usage.
5. Score each prediction against withheld ground truth.
6. Repair the fault and confirm a healthy baseline.
7. Repeat per reporter type and scenario, avoiding contamination across trials.

Useful metrics: fault detection, fault type, exact device-set localization, separately adjudicated root cause, elapsed time and number of tool calls. Report small sample sizes honestly.

## Traceability against client direction

| Client direction | Current contribution | Next step |
|---|---|---|
| Large topologies (ideally 75–100 nodes) | One 80-node network | Validate broader node and link coverage |
| Multiple subnets and protocols | Multiple /24 LANs, /31 P2P; OSPF and eBGP | Add realistic route policies / VLAN / additional protocols where justified |
| Controlled fault scenarios | F01–F03 operationally tested | More categories, protocol-state assertions, repeatability |
| Reports of varied accuracy/detail | Four tickets per case | Test agent responses to ticket quality |
| Larger dataset (~10 topologies aspirational) | One topology | Coordinate distinct additions across team |
| SADE agent evaluation | Offline scoring utility only | Integrate actual SADE and preserve traces |
| Ground truth | Three scenario records | Align schema with client format when accessible |

## Suggested follow-on priorities

1. Save raw evidence for all three verified fault tests and update stale scenario status metadata at its generator source.
2. Strengthen protocol-specific assertions (`show bgp summary`, advertised routes, OSPF neighbors and routes) rather than only reachability.
3. Add independent one-interface outage scenario (service remains reachable but fault remains detectable), DNS/ACL faults and realistic BGP route-policy misconfigurations.
4. Introduce VLAN separation/VRRP only when corresponding acceptance tests are added; do not retroactively claim current switches implement those features.
5. Align final data schema with client, then integrate SADE and compare diagnosis behavior across ticket types.
