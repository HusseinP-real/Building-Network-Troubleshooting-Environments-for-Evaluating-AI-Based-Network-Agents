# Scoring v4 and controlled comparisons

New runs use scorer 4.0. Saved reports keep their original scores. Each new case also records legacy_strict (v3 string/scalar checks), format_compliant, repair_validation and repair_review_required. The summary includes legacy_strict_metrics. No model repair command is executed.

Structured root_causes are authoritative for RCA. Every cause and device must match, with no missing or extra causes. Scalar resource_id/fault_type disagreement is reported separately as a format warning. The independent judge still checks substantive contradictions in the explanation and repair.

Repair PASS requires both judge approval and a deterministic approved equivalent plan. Rules accept shell token quoting/spacing, ip link optional dev, and targeted iptables delete-rule option order/long aliases, /32 host addresses, redundant tcp match, default filter table and default ICMP reject option. Devices, chain, source/destination, protocol, port and action remain significant. Existing reference alternatives remain supported. Unknown judge-approved plans require REVIEW; they do not receive pass credit. Incorrect recognized operations, wrong owners, unsafe compound commands and unnecessary changes on healthy cases fail. Judge failures remain unscored. REVIEW does not prove that a repair works; resolve it by technical review before publishing a final full-correctness comparison.

For tonight and subsequent runs:

- Original Enterprise benchmark: all 20 tickets.
- One pass initially; subsequent repeats use the same settings.
- Dashboard original-suite limit is 20 turns, order seed 42.
- Live tools, Standard investigation (generic), Individual commands (atomic).
- Choose one fixed quality judge for every model; do not use Same as agent.
- Change only the diagnosing model. Keep suite manifest, scorer version, judge and environment constant.
- Keep API/subscription routing and tool transport in the report. Claude SDK and Codex bridge still differ; equal turn limits do not imply identical tool-call or token budgets.
- Separate errors, pending reviews and valid scores. Report both pass/attempted and pass/scored, plus coverage. Repeated runs are the same 20 tickets, not additional unique cases.

Restart the dashboard backend after any active benchmark finishes, then refresh the browser to load the new code. Do not compare v4 full correctness directly to the historical 55% v3 score. Use new runs under the same rubric, or explicitly re-evaluate saved answers into new artifacts with a common judge. This change does not itself invoke paid models or re-evaluate historical answers.
