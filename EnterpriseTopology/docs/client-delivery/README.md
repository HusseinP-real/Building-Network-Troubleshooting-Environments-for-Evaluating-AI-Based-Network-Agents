# Client delivery report and requirements records

Recorded on 2026-10-23 (Australia/Sydney). This directory supports final delivery and acceptance. It does not expand feature scope or rerun model benchmarks.

## Reading order

- `report/main.tex`: English client report, compilable with a PDF preview in the Codex LaTeX editor.
- `user-stories.md`: readable requirements and acceptance criteria.
- `user-stories.json`: the same requirements in structured form.
- `feedback-response.md`: client feedback, related user stories, responses, and remaining limitations.
- `test-results.md` / `test-results.json`: results summarized from saved test evidence.
- `../../results/delivery/`: raw XML, browser TAP, real-network JSON, and console logs.

US01–US04 come from client feedback relayed by the team on October 23: topology selection, fault selection, benchmarking, and an agent diagnosis accuracy target of approximately 50%–70%. The previous week's meeting minutes have not been independently verified. US05–US12 are additional team proposals awaiting client acceptance, not previously agreed client requirements.

At the time of this delivery record, automatic SADE benchmarking was connected only to `enterprise-75`. Browsing multiple topologies did not mean all supported automatic benchmarking. The report and US03 retain this limitation as part of that dated record.

## Reporting test results

The supplied rubric does not require a 100% pass rate or specify a code-coverage threshold. Report scope, counts, outcomes, defect impact, and remaining limitations.

- **Executed-test pass rate** = Passed / (Passed + Failed + Error). Report N/A when the denominator is zero.
- **Execution proportion** = (Passed + Failed + Error) / (Passed + Failed + Error + Skipped + Not run). List inapplicable cases separately rather than silently removing them.
- **Agent diagnosis accuracy** is a separate metric and must not be combined with software-test pass rates.
- Duplicate assertions, pytest subtests, and browser parent containers are not additional independent tests.

A 100% result means only that every executed test within the stated scope passed in that run. It does not establish a defect-free product, client acceptance, or completion of all requirements. A final regression after fixes may legitimately reach 100%; failures should not be retained artificially. Preserve evidence of failures and explain their impact. Core workflow failures, scoring errors, and recovery failures take priority and cannot be hidden behind an overall high pass rate.

## Test boundaries

- Offline tests: parsing, independent scoring examples, error denominators, configuration isolation, fault catalogs, concurrency, and recovery-failure paths.
- HTTP integration: real temporary loopback servers with substitutes at model/network execution boundaries; these do not establish successful real-agent runs.
- Browser tests: real Chrome and pages explicitly marked MOCK executor; selection, submission, results, failure recovery, healthy controls, keyboard access, and small-screen layout.
- Real network: explicit opt-in using the existing Kathara network and the same environment lock. Inject only reversible faults owned by this topology, check affected and control paths, recover, and verify the full baseline. No model is called.
- This delivery exercise does not remeasure model accuracy or paid API cost, and does not establish independent installation in the client's environment, complete cross-browser coverage, or a full accessibility audit.

## Reproduction and record updates

Run offline tests from `EnterpriseTopology/`; temporary loopback ports must be allowed:

```sh
python -m pytest tests -q --junitxml=results/delivery/offline-tests.xml
```

Browser tests require Playwright and Chromium/Chrome. Set `NODE_PATH`, `BROWSER_EXECUTABLE`, and `NIKA_TEST_PYTHON` as needed for local dependencies:

```sh
node --test tests/dashboard_delivery.cjs
```

Real-network tests are skipped by default. Run them explicitly only when system revalidation is needed and baseline and environment ownership have been confirmed. This does not rerun model benchmarks:

```sh
RUN_LIVE_DELIVERY=1 python -m unittest discover -s tests -p test_live_delivery.py -v
```

To refresh the report from existing evidence without running tests or models:

```sh
python tools/record_delivery_results.py
```

## Outstanding delivery decisions

Confirm the official project name, recipient, final scope, client acceptance of additional criteria, whether diagnosis accuracy primarily means exact RCA or full correctness, the deployment environment, code/document access, independent installation, and UAT results. The 50%–70% range is a difficulty target. Report actual results without changing scoring rules to force them into that range.
