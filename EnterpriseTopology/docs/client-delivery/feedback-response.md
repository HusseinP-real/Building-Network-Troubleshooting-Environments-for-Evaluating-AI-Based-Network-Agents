# Client feedback response record

Recorded on 23 October 2026 (Australia/Sydney). Source: feedback from last week as reported by the team in this conversation. The exact original meeting date, attendees and minutes are not verified here. This document does not establish client sign-off.

| Reported feedback | Story | Response / current behavior | Evidence and remaining limit |
|---|---|---|---|
| Choose a topology on the web page | US01 | The topology explorer and run form synchronize selection; the map and fault list refresh together. | Browser workflow and topology API tests passed. Selection alone does not establish automatic execution support. |
| Choose the fault to inject before benchmark execution | US02 | The selected topology supplies its own fault catalog; the server rejects mismatches. Healthy controls perform no injection. | HTTP, catalog and browser checks passed; native execution support varies by topology. |
| Run a benchmark after choosing topology and fault | US03 | The selected fault group and model configuration reach the existing EnterpriseTopology runner without a prerequisite manual injection. | Real HTTP and MOCK browser workflow passed. Automatic SADE is currently limited to enterprise-75; a model-backed run was not repeated in this validation. |
| Expected agent diagnostic accuracy approximately 50%-70% | US04 | Recorded as a benchmark difficulty target, separate from software-test success. Actual results must remain unchanged even outside the target. | Score calculation and denominator regressions passed. No new agent accuracy measurement was performed, as requested. Confirm primary metric and reference configuration with the client. |

US05-US12 are team proposals documented during preparation of the final delivery. Ask the client to review their value and acceptance criteria; do not backdate them as prior client requests.

## Review still required

- Confirm whether exact RCA fields or full correctness is the intended primary accuracy metric.
- Confirm which topologies must support automatic benchmark execution at final delivery; retain US03 as partial until that scope is resolved and verified.
- Identify any client-requested changes not captured in the team's summary, and attach the original feedback evidence.
- Record client decisions, accepted limitations, UAT results and sign-off after the review meeting.
