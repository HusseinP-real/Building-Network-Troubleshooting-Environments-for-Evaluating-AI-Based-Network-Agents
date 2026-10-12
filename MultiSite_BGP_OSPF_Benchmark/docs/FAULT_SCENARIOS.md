# Fault Scenarios and Acceptance Criteria

## General test protocol

For each scenario: healthy baseline → inject one defined scenario event → observe expected failure and unaffected control route → repair in cleanup → confirm affected route recovers → rerun 18/18 baseline. The tested fault events may each act on **two router devices** to overcome path redundancy.

## Scenarios

| ID | Category | Actual injected change | Expected affected probe | Control probe | Restoration |
|---|---|---|---|---|---|
| **F01** | ISP-A peering interface outage | Bring `a1:eth1` and `a3:eth1` down | HQ host cannot ping `198.18.10.10` | HQ host can still ping ISP-B `198.18.20.10` | Bring both interfaces up |
| **F02** | BGP prefix withdrawal | Remove `network 198.18.10.0/24` from `a1` and `a3` BGP processes | HQ host cannot ping `198.18.10.10` | ISP-B service remains reachable | Restore BGP `network` statements |
| **F03** | Branch A routing outage | Stop FRR on `ba_r1` and `ba_r2` | HQ host cannot ping `10.20.10.21` | HQ can still ping DC `10.40.10.21` | Restart FRR on both routers |

## Commands

```bash
python3 lab.py check
python3 lab.py test-fault F01 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F02 --settle-seconds 35
python3 lab.py check
python3 lab.py test-fault F03 --settle-seconds 35
python3 lab.py check
```

## Reported live validation (12 October 2026)

- **F01:** user supplied console output: baseline before fault was true; injection OK; expected ISP-A ping loss observed; ISP-B control path remained healthy; repair OK; result had `passed: true`; subsequent 18/18 baseline passed.
- **F02/F03:** user subsequently confirmed both completed without errors, and post-repair checks passed. Raw command logs were not supplied in this conversation; add the actual run outputs to `results/evidence/` when available.

## What these tests do / do not demonstrate

**Demonstrate:** repeatable action and repair scripts, controlled affected/unaffected reachability, and post-repair validation. **Do not demonstrate yet:** exact BGP RIB/FIB deltas for every router, performance under multiple concurrent independent faults, all-router route coverage, SADE root-cause inference, or statistically repeatable agent performance. The final benchmark should add direct protocol-state assertions and repeated run metadata.

## Ground truth and tickets

Ground truth is stored in `scenarios/F01/ground_truth.json` and equivalents; each `tickets.json` has four perspectives. These are scenario labels written ahead of time, not generated through a live agent. Keep ground truth inaccessible to an agent being evaluated. Some original metadata may still say `planned_until_live_verified`; **update that field in the generator** to reflect actual test evidence if a client-facing schema requires a run-status field, instead of relying on manual edits to regenerated JSON.
