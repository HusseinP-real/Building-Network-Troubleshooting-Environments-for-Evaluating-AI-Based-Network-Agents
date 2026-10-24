# Delivery validation record

Recorded: 2026-10-23T18:45:42.078632+11:00. Base revision: `28bfc7ffb42c3c6f4a256d23bc0bcca19cf5a3bc` plus the current local changes. Exact hashes of key sources are in `test-results.json`.

Current EnterpriseTopology delivery workflow; not exhaustive testing of every repository or topology.

| Evidence group | Passed | Failed | Error | Skipped | Pass / executed |
|---|---:|---:|---:|---:|---:|
| Offline + HTTP regression | 68 | 0 | 0 | 11 | 100.0% |
| Browser workflows (MOCK executor) | 5 | 0 | 0 | 0 | 100.0% |
| Real network cycles (no model) | 11 | 0 | 0 | 0 | 100.0% |

Offline execution proportion: **68/79 (86.1%)**. The 11 opt-in live tests are deliberately skipped in the offline command; real-network cycles are reported separately. Do not count these two invocations as different implementations of the same requirement. Browser statistics count leaf workflows only.

Real-network suite finished: **True**. Pending owned faults in its latest saved evidence: **[]**. A partial/in-progress live record is not a complete-suite claim.

## How to interpret the rates

Pass rate = passed / (passed + failed + errors). Skipped and not-run cases are shown separately. No aggregate rate mixes unit cases, browser workflows, health assertions and network cycles. A 100% rate applies only to the declared executed scope. It does not establish complete requirement coverage, absence of defects or client acceptance. The supplied rubric specifies no mandatory 100% threshold.

## Findings fixed during validation

- Repeated paths to the same result file previously inflated attempted counts; resolved paths are now deduplicated.
- Malformed saved report shapes previously crashed the report index; invalid entries are now skipped without hiding valid reports.

## Known limits and pending acceptance

- Automatic SADE evaluation is adapted only for enterprise-75; other catalogs are not equivalent to executable automatic benchmarks.
- No new model-backed end-to-end evaluation, diagnostic accuracy measurement or paid API cost measurement.
- Client UAT, independent installation in the intended client environment, and final sign-off remain pending.
- No source-code line/branch coverage percentage, broad performance SLA, full accessibility conformance or cross-browser claim is made.
- Offline live-test skips are counted separately from the explicitly opted-in real-network suite; browser parent groups and pytest subtests are not extra test cases.

## Agent accuracy

No benchmark or model request was rerun for this report. The client-reported **50%-70% diagnostic accuracy** is a difficulty target, not the software-test pass threshold. This report does not claim the target was met. Exact RCA over all attempts is the proposed primary interpretation; full correctness and scored-only rates remain separate. Confirm the primary metric and reference experiment with the client.

## Evidence

- `results/delivery/offline-tests.xml` and `offline-tests.log`
- `results/delivery/browser-tests.tap`
- `results/delivery/live-20261023T063153Z.json` and `results/delivery/live-console.log`
- `docs/client-delivery/user-stories.json`: provenance, acceptance criteria, implementation limits and test links
