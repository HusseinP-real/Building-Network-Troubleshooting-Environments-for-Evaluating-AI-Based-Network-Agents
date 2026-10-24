# SADE benchmark diagnostic audit — 2026-10-13

## Conclusion

No direct ground-truth read was found in the current runner or the 12 saved runs from 2026-10-13. The stronger explanation for perfect scores is a narrow, fixed fault suite with tailored instructions and diagnostic sweeps. This is an evidence-based inference, not proof that every possible leakage path is excluded.

## Checks performed

- Inspected `tools/sade_eval.py`, `tools/sade_lab_mcp.py`, `tools/sade_benchmark.py`, `tools/sade_cases.json`, `lab.py`, and SADE project instructions.
- Audited all 12 individual saved runs dated 2026-10-13: 12/12 exact RCA. Recorded tools: reachability (12), helper listing (3), container diagnostics (132), helpers (43), Skill (12). No recorded request referenced ground_truth, sade_cases, ../, /shared, or /hosthome.
- Ran the existing eight offline robustness tests using the NIKA virtual environment; all passed, including SDK option capture for no-tools mode. These tests do not make model calls or prove runtime SDK security.
- Checked the live r5 and app containers. `/shared` and `/hosthome` exist but Docker inspection identifies them as named volumes, not host directory bind mounts. `/shared/tools/sade_cases.json` was absent in both. Other devices and every file in these volumes were not exhaustively inspected.
- Supplied an incorrect owner to the scorer: localization, device correctness and exact RCA failed.
- Supplied correct structured fields with an intentionally false explanation and harmful repair text: exact RCA still passed. The text is not graded.
- Tested the command validator offline: `cat /etc/frr/../../../shared/tools/sade_cases.json` is accepted. No such read was executed.

## Findings

1. Prompt construction excludes ground truth and injection commands. The SDK disables Bash, Read, Glob and Grep; live mode intentionally loads project instructions and Skill. It is not an OS filesystem sandbox.
2. Twelve tickets represent three fixed injected faults and healthy state. Vague/misleading variants change the ticket, not the physical root cause. Repeats and shuffled schedules do not randomize the faulty device or interface.
3. The system prompt explicitly directs the agent to inspect redundant links and VRRP even when application reachability succeeds. These are the two faults that otherwise require deeper discovery.
4. Public ontology contains only three fault classes. `infra_sweep` supplies all router interface states, OSPF neighbors, keepalived processes, and app OUTPUT rules. This is real telemetry, but the helper is tailored to the suite and greatly reduces search difficulty.
5. Exact RCA measures agreement on anomaly, device, resource and fault type. It does not validate causal reasoning, evidence sufficiency or remediation. Environment repair is performed by the runner, not the agent.
6. The cat whitelist uses string prefixes without path normalization. Traversal escapes the intended directories. This is a confirmed validator weakness, not evidence that the saved runs leaked ground truth. Other broad allowances, including /proc and process options, merit a separate hardening review.
7. The trace truncates each tool result to 10,000 characters. It cannot always reconstruct the complete content delivered to the model.

## Recommended experiments

1. Run the existing no-tools control and compare separately with live runs. This establishes the amount of ticket-only inference; no-tools alone does not prove absence of leakage.
2. Keep the same live fault and compare generic instructions against the current tailored prompt.
3. Compare generic per-device tools against the suite-specific helpers, under declared command/time budgets.
4. Randomize valid fault owners and interfaces, add held-out faults and alternative causes with similar symptoms, and include healthy controls. Maintain reproducible seeds and hidden manifests.
5. Add a deterministic telemetry-only baseline to measure whether this suite requires an LLM at all.
6. Normalize and restrict diagnostic paths, isolate the agent workspace from manifests/results, and capture complete auditable tool results.
7. Report structured identification accuracy separately from explanation and remediation quality.

No benchmark logic was changed, no faults were injected, and no paid model calls were made during this audit.
