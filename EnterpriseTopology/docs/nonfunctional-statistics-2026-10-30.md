# Enterprise 75 — Non-functional Statistics Report

Data date: 30 October 2026 (Australia/Sydney, UTC+11). This report summarises existing results; no experiments were rerun to produce it.

The dataset contains six batches and 105 case executions: 89 fault cases and 16 healthy controls. Every per-case result identifies `topology_id=enterprise-75`.

## Results by batch

| Completion time (Sydney) | Model | Suite / Scorer | Cases | Injection verified | State verified | Recovery verified | Complete runs | Errors | RCA matches ground truth |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 01:24:28 | gpt-6.1-sol | 3.0 / 3.0 | 20 | 17/17 | 20/20 | 20/20 | 20/20 | 0 | 18/20 |
| 02:23:22 | gpt-6.1-terra | 3.0 / 4.0 | 20 | 17/17 | 20/20 | 20/20 | 19/20 | 1 | 19/20 |
| 08:45:34 | gpt-6.1-sol | 3.0 / 4.0 | 20 | 17/17 | 20/20 | 20/20 | 20/20 | 0 | 20/20 |
| 12:30:34 | claude-sonnet-5-5 | 3.0 / 4.0 | 20 | 17/17 | 20/20 | 20/20 | 20/20 | 0 | 20/20 |
| 13:30:04 | deepseek-flash | 3.0 / 4.0 | 20 | 17/17 | 20/20 | 20/20 | 3/20 | 17 | 3/20 |
| 17:16:48 | gpt-6.1-terra | generic-1.0 / 4.0 | 5 | 4/4 | 5/5 | 5/5 | 5/5 | 0 | 5/5 |

“Complete runs” uses the original reports' `complete_runs` field. It reflects model execution/scoring status and must not be used as the environment's fault execution success rate. The first five batches each contain 20 cases; the last contains five cases from `generic-1.0`. These are not six independent redeployments of the same scenario suite.

RCA is a model diagnosis metric. The first batch uses Scorer 3.0 and the others use Scorer 4.0. Retain results by batch rather than combining them into a model ranking under a single scoring definition.

## Available NFR statistics

| NFR | Metric | Result and definition |
|---|---|---|
| Reproducibility | Independent redeployments / Reproduction Success Rate | Not determinable. The records show repeated case execution, but do not identify independent teardown and redeployment for each execution. A redeployment success rate is therefore not reported. |
| Reliability | Fault Execution Success Rate | 89/89 = 100.00%. The denominator includes fault cases only and excludes healthy controls. Each compound-fault case counts as one case. |
| Reliability | Baseline and target-state verification | 105/105 = 100.00%. `state_verified` is set to true after baseline checks and post-injection state assertions pass. Baseline success is inferred from this code path; see the implementation evidence below. |
| Reliability | Environment recovery verification | 105/105 = 100.00%, including baseline rechecks after healthy-control executions. Recovery for fault cases alone is 89/89. |
| Reliability | Environment end-to-end validation | 105/105 = 100%. Defined here as successful baseline, target-state and recovery verification. This measures the test environment lifecycle. |
| Scalability | Device startup verification | All 202 health reports from the day passed 75/75 startup checks each. These checks concern the running environment and do not represent 202 independent deployments. |
| Scalability | Path and access-policy verification | 8,282/8,282 checks passed. Checks were selected by names containing `reachable`, `application HTTP`, `DMZ allowed`, `application denied`, `database denied` or `database allowed`. This includes expected-denial policy checks and is not an all-pairs device connectivity rate. |
| Scalability | CPU / Memory Usage | N/A. The evidence for the day does not provide resource samples suitable for this statistic. |

Recovery fields `repair_verified` / `environment_restored` record the test framework's cleanup repairs and subsequent baseline checks. They are not the success rate of repairs proposed or executed by the model. Model repair scores are retained separately as `model_repair_correct` in the original statistics file, `statistics.json`.

## Errors and statistical limitations

There were 18 model execution errors: one usage-limit error in the `gpt-6.1-terra` batch and 17 errors for reaching the 20-turn interaction limit in the `deepseek-flash` batch. Environment state and recovery verification still passed for these cases. Record these errors separately from fault injection failures.

All 202 health reports for the day have an overall `passed` value of true. They include repeated baseline/recovery checks and must not be added to the 105 case executions as additional experiments.

## Original reports and audit material

The original evidence archive prepared for this analysis contains six benchmark summaries, 105 per-case JSON results, 202 health JSON reports for the day, the statistics JSON, the original report and its generation script. Evidence paths inside that archive are preserved under `evidence/`. This repository document is the English translation of the statistical report; the archive and raw results are not bundled with this document.

Filenames use UTC. The date filter converts `generated_at` / `timestamp` to Sydney time. This report includes whole batches completed on the data date. To filter by individual case start time instead, use the case `timestamp` values in `statistics.json`.

Original benchmark summary filenames:

- `benchmark-20261029T132907421712Z.json`
- `benchmark-20261029T144002670043Z.json`
- `benchmark-20261029T205909440850Z.json`
- `benchmark-20261030T004935528679Z.json`
- `benchmark-20261030T013712748497Z.json`
- `benchmark-20261030T061020896998Z.json`

Implementation evidence: the `run_case` flow in [tools/sade_eval.py](../tools/sade_eval.py) checks the baseline through `lab.check`, verifies injected state through `_assert_state`, and performs framework repairs, state assertions and a full baseline check in `finally` before setting `repair_verified`. A copy of the implementation used for the analysis is retained in the original evidence archive for audit purposes.
