# User stories and acceptance criteria

Project title, recipient, final delivery scope and client acceptance must be confirmed before sign-off. Client feedback below was reported by the team in conversation on 23 October; the original meeting date/minutes have not been verified. Team proposals are newly documented requirements, not historical client commitments.

## US01 - Select and inspect a topology

As a network researcher, I want to choose a topology in the web interface so that I can inspect the network used for my next evaluation.

Source: `client_feedback_reported_by_team`. Implementation: `implemented_for_current_catalog`. Client acceptance: `pending`.

- The chosen topology updates the displayed devices, links and associated fault list.
- The map selector and benchmark form remain synchronized.
- The interface states whether automatic evaluation, manual execution or catalog exploration is supported.

Evidence: `test_dashboard_topologies.py`; `dashboard_delivery.cjs: topology selection refreshes faults and disables unadapted benchmark`

## US02 - Select a compatible fault

As a network researcher, I want to select an applicable fault for the chosen topology so that the evaluation uses the intended failure mechanism.

Source: `client_feedback_reported_by_team`. Implementation: `implemented_with_explicit_support_boundaries`. Client acceptance: `pending`.

- Only the selected topology's catalog is displayed; unsupported combinations are rejected by the server.
- Fault descriptions and targets are available to the operator.
- Healthy controls perform no injection, and ticket variants are not counted as different physical mechanisms.

Evidence: `test_manual_operations.py:ManualTests.test_catalog_deduplicates_tickets_and_filters_real_devices`; `test_dashboard_delivery.py:DashboardDeliveryTests.test_unadapted_topologies_cannot_launch_the_enterprise_runner`; `dashboard_delivery.cjs: healthy control cannot be manually injected`

## US03 - Run the selected benchmark workflow

As a network researcher, I want to select a topology, fault and agent model and start the benchmark from the web page so that I can evaluate the intended configuration without issuing manual fault commands.

Source: `client_feedback_reported_by_team`. Implementation: `partial_auto_evaluation_only_enterprise_75`. Client acceptance: `pending`.

- The submitted topology, fault group, model, repetitions and evaluation settings reach the existing runner unchanged.
- For an adapted environment the runner performs baseline, injection, diagnosis, scoring, result saving and recovery.
- An unadapted topology cannot accidentally execute against EnterpriseTopology.
- A current model-backed end-to-end run is required to verify agent execution; a MOCK browser run alone does not satisfy that condition.

Evidence: `test_dashboard_delivery.py:DashboardDeliveryTests.test_selected_fault_and_model_reach_existing_runner_unchanged`; `test_manual_operations.py:HTTPTests.test_selected_scope_and_all_scope_use_existing_runner`; `dashboard_delivery.cjs: selected topology/fault reaches the benchmark and its report`

## US04 - Measure a useful level of diagnostic difficulty

As a benchmark stakeholder, I want agent diagnostic accuracy to be approximately 50% to 70% under a declared reference configuration so that the benchmark has useful discriminatory difficulty.

Source: `client_feedback_reported_by_team`. Implementation: `empirical_target`. Client acceptance: `pending_metric_definition`.

- Report the reference model/version, fixed case manifest/hash, scoring version, prompt, tools, turn budget, seed, repetitions and denominator.
- Working primary metric: exact RCA correct / all attempted scheduled diagnoses; report scored-only accuracy, errors and full correctness separately. Confirm this metric choice with the client.
- Report actual accuracy even outside 50% to 70%; never clamp scores, remove failures or change the test set after seeing final results.
- The target remains empirically unverified until applicable model results are reviewed; no model benchmark was rerun for this report.

Evidence: `test_delivery_contracts.py:SummaryContractTests.test_accuracy_is_not_clamped_to_client_difficulty_target`; `test_delivery_contracts.py:SummaryContractTests.test_all_attempts_including_errors_remain_in_accuracy_denominator`

## US05 - Use reproducible validated fault scenarios

As a benchmark maintainer, I want each supported scenario to define its baseline, injection, observable impact, ground truth and recovery so that repeated evaluations begin and end in a known state.

Source: `team_proposal`. Implementation: `implemented_for_enterprise_scenarios`. Client acceptance: `not_yet_requested`.

- Verify a healthy precondition before mutation and the actual fault state after injection.
- Check the expected service impact and an unaffected control path; redundancy does not imply every failure must cause an outage.
- Verify repair predicates and the complete baseline before clearing owned pending faults.
- Record repeat runs as repeatability evidence without treating one repeat as a reliability guarantee.

Evidence: `test_live_delivery.py`; `test_manual_operations.py:ManualTests.test_native_adapters_reuse_exact_injection_and_repair`

## US06 - Produce trustworthy diagnosis scores

As a researcher, I want diagnosis scoring to follow an explicit ground-truth contract so that correct, partial, incorrect and unscored answers are distinguished consistently.

Source: `team_proposal`. Implementation: `implemented`. Client acceptance: `not_yet_requested`.

- Detection, device, resource, fault type and exact RCA are distinct metrics.
- Exact RCA requires every expected cause and rejects incorrect or duplicate additional causes.
- Missing quality judgement remains unknown; a correct label alone does not prove explanation or repair quality.
- The same result file is counted only once; errors remain visible in denominators.

Evidence: `test_delivery_contracts.py`; `test_sade_robustness.py`

## US07 - Evaluate misleading reports and healthy controls

As a researcher, I want accurate, vague and misleading tickets plus healthy controls so that the benchmark can distinguish diagnosis from simply accepting the reporter's claim.

Source: `team_proposal`. Implementation: `implemented`. Client acceptance: `not_yet_requested`.

- Ticket variants of one mechanism retain the same hidden ground truth.
- Healthy scenarios inject no fault and unnecessary repairs lose credit.
- The diagnostic agent cannot access evaluator ground truth, injection metadata or recovery journals.
- Report healthy false positives separately from exact RCA accuracy.

Evidence: `test_sade_robustness.py:RobustnessTests.test_variants_have_same_hidden_state`; `test_manual_operations.py:ManualTests.test_operator_journal_and_catalog_cannot_be_read_by_diagnostic_agent`; `test_sade_robustness.py:RobustnessTests.test_errors_in_denominator_and_healthy_false_positive`

## US08 - Recover safely from failed operations

As a lab operator, I want failures and interrupted operations to retain targeted recovery information so that another evaluation cannot run against an uncertain environment.

Source: `team_proposal`. Implementation: `implemented`. Client acceptance: `not_yet_requested`.

- Record mutation intent before executing a fault, including partially applied failures.
- Attempt all owned repairs and retain pending entries if repair or baseline verification fails.
- Reject concurrent or duplicate mutations and automatic runs while recovery is pending.
- Only the selected lab and owned fault components are modified; secrets are redacted from operator logs.

Evidence: `test_manual_operations.py`; `test_sade_robustness.py:RobustnessTests.test_fault_is_restored_even_when_agent_fails`; `dashboard_delivery.cjs: partial compound injection blocks benchmark until targeted recovery`

## US09 - Follow execution progress and errors

As a researcher, I want clear running, completed and failed states with progress and logs so that I can understand what happened during an evaluation.

Source: `team_proposal`. Implementation: `implemented`. Client acceptance: `not_yet_requested`.

- Display completed/total attempts and preserve error messages.
- Disable conflicting controls while work is in progress.
- Load the corresponding saved report after completion, without relabeling old results when the next configuration changes.

Evidence: `dashboard_delivery.cjs`; `test_dashboard_delivery.py:DashboardDeliveryTests.test_report_roundtrip_preserves_results_and_original_scope`

## US10 - Inspect traceable saved results

As a researcher, I want saved JSON results and readable summaries with configuration, status and per-case scores so that an evaluation can be audited and compared later.

Source: `team_proposal`. Implementation: `implemented_json_and_report_api_no_dedicated_export_control`. Client acceptance: `not_yet_requested`.

- Preserve per-run configuration, score components, errors and restoration status.
- Keep different models and execution configurations separate in comparisons.
- Saved report retrieval returns the original data; corrupt reports cannot break the report list.
- A dedicated browser download/export control is future scope unless separately implemented; JSON files and the report API are the current handover artifacts.

Evidence: `test_dashboard_delivery.py`; `test_delivery_contracts.py:SummaryContractTests.test_summary_preserves_separate_model_configurations`

## US11 - Install and operate the delivered system

As the receiving client, I want source code, environment prerequisites, operating instructions, limitations and test evidence so that I can take ownership of the deliverable.

Source: `team_proposal`. Implementation: `documentation_available_handover_pending`. Client acceptance: `not_yet_requested`.

- Provide source revision information, dependencies, startup and recovery instructions, support matrix and evidence paths.
- Identify required client infrastructure and credential setup without including secrets.
- A client or independent team member follows the guide in the intended environment; record the result before claiming deployment acceptance.

Evidence: `manual: independent installation checklist and client acceptance meeting`

## US12 - Operate the interface on common screen sizes

As a user, I want the main selection controls to work with a keyboard and on a small screen so that I can configure an experiment without layout barriers.

Source: `team_proposal`. Implementation: `implemented_for_tested_browser`. Client acceptance: `not_yet_requested`.

- The tested desktop and mobile viewports have usable selection controls and no horizontal page overflow.
- Keyboard selection updates the same underlying topology/fault values as pointer selection.
- State the tested browser and dimensions; do not claim comprehensive accessibility conformance from these checks.

Evidence: `dashboard_delivery.cjs: mobile form remains usable without horizontal page overflow`
