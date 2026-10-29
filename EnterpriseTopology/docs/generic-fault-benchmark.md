# Generic fault benchmark guide

Thirteen topologies share four fault families and a healthy control. The UI workflow is Topology → Fault → Model → Benchmark. Each fault has fixed targets for its selected topology.

## Original Enterprise 20-ticket benchmark

For comparison with the Haiku 55% full-correctness report from 16 October 2026,
select **Enterprise Topology** and **Evaluation settings → Scenario coverage →
Original Enterprise benchmark · 20 tickets**. Choose the diagnosis model and keep
**Quality judge** on **Claude Haiku 5.5**. **1 pass** runs each of the 20 tickets
once; **5 passes** runs 100 diagnoses.

This option uses the existing `tools/sade_cases.json`, native lab adapter and v3
scorer, with seed 42, generic investigation prompts and atomic tools. The case
manifest matches the historical report. Per user preference, the new dashboard
limits each diagnosis to **20 interaction turns**, while the historical Haiku
report allowed 30. Record that budget difference when comparing results; a fully
controlled comparison requires rerunning Haiku under the same 20-turn budget.
The SDK/runtime has also been updated since the historical run.

The runner checks the full native baseline before every ticket and verifies
injection and restoration. The selected generic fault does not affect this suite.
This suite is available only on the original Enterprise Topology, not on the
other topologies. Pending faults and active operations continue to block runs.
Restart the dashboard server after updating its Python code.

## Workflow

1. Start the selected Kathara lab. The UI does not automatically start or stop 75–92 containers.
2. Choose the topology and fault, then click **Validate selected fault & recovery**. Validation does not call a model.
3. Validation checks the source endpoint address, interface, default route, and three baseline probe paths, then injects the fault, verifies its effect and an independent control, performs precise recovery, and rechecks the baseline. The healthy control runs baseline checks only.
4. After validation passes, select a model and run the benchmark. All 5 generic cases becomes available only after all five cases pass validation.
5. If recovery fails, original configuration backups and pending records are retained. Use Recover under Advanced laboratory debugging before continuing.

## Fault scope

| Option | Injection and recovery |
|---|---|
| Link / interface down | Disable the test endpoint interface to isolate it; restore the interface and its original default route. |
| Incorrect default gateway | Replace the endpoint default route with an explicitly specified incorrect onlink next hop; restore the original route. |
| Destination route blackhole | Add a /32 blackhole route for the remote test IP at the source endpoint; remove only the injected route. |
| ICMP traffic blocked | Add an ICMP DROP rule in the source endpoint OUTPUT chain matching only the test destination; remove only that rule. |
| Healthy network | No injection; check baseline paths. |

This is an endpoint-connectivity benchmark. Traffic filtering checks ICMP and does not imply every application is blocked. Link failure affects endpoint access and does not test core redundancy. Baseline checks cover selected endpoints and probe paths, not every protocol and service throughout the network. Contributor-specific scenarios remain in source files but are hidden from the default selection list. Legacy faults with pending recovery records remain visible for recovery.

## Fixed targets

| Topology | Test endpoint | Remote target | Independent control endpoint | Lab directory |
|---|---|---|---|---|
| enterprise-75 | app_client01 / eth0 | db_client01 / 10.30.20.20/24 | app_client02 | `EnterpriseTopology` |
| enterprise-75-standalone | app_client01 / eth0 | db_client01 / 10.30.20.20/24 | app_client02 | `EnterpriseTopology75` |
| p20-enterprise | pc1 / eth0 | pc10 / 10.10.3.12/24 | pc11 | `FaulT-Bench/topology_kathara/P20Enterprise` |
| sarah-enterprise-75 | pc1 / eth0 | pc3 / 10.10.2.10/24 | pc10 | `Sarah_Enterprise_75` |
| sarah-service-75 | pc1 / eth0 | pc10 / 10.21.10.30/24 | pc11 | `Sarah_Service_75` |
| jennie-enterprise-75 | pc01 / eth0 | pc02 / 10.20.2.20/24 | pc03 | `Enterprise-SADE-W11-75/lab` |
| multi-as-isp | as65010h1 / eth0 | as65010h2 / 10.10.1.6/30 | as65010h3 | `Multi-AS-ISP-Backbone-W11-75/lab` |
| multisite | ba_h01 / eth0 | bb_h01 / 10.30.10.21/24 | ba_h02 | `MultiSite_BGP_OSPF_Benchmark` |
| jiayuan-75 | a1 / eth0 | pc0 / 20.1.1.10/8 | a2 | `FaulT-Bench/topology_kathara/Kath5_Jiayuan_75Devices` |
| nika-92 | client_1 / eth0 | client_2 / 192.168.2.2/24 | client_3 | `FaulT-Bench/topology_kathara/NIKA_Clos_Jiayuan_92Devices` |
| kairos-enterprise | app_client01 / eth0 | db_client01 / 10.30.20.20/24 | app_client02 | `EnterpriseTopology_Kairos` |
| campus80-eason | pc01 / eth0 | pc06 / 10.10.2.20/24 | pc02 | `Campus80_Eason` |
| enterprise80-eason | brispc1 / eth0 | brispc10 / 10.30.20.11/24 | brispc11 | `Enterprise80_Eason/topology_kathara/Enterprise80` |

`tools/build_generic_faults.py` compiles targets statically from lab.conf/startup files at a fixed Git revision and records source SHA-256 hashes. `tools/generic_faults.py` executes only its own generated commands, not contributor injection scripts. Jennie's candidate lab source has been imported. Premature host-shell expansion in its HTTP scripts was fixed, but its native candidate scenarios were not live-tested in this evaluation.

## Command line

Run from the repository root with Kathara and the NIKA/SADE dependencies installed:

```sh
python3 EnterpriseTopology/tools/generic_faults.py enterprise-75 link_down
```

Validation results, including commands and observations, are stored in each lab's `results/control/generic-validation-<family>.json`. Records apply only to the current mapping and adapter-code fingerprints. Source changes require revalidation. Every benchmark still checks the baseline, injection state, and recovery state.

The backend uses `SADE_GENERIC_TOPOLOGY` to bind the evaluator, read-only MCP tools, lab lock, and report to the selected topology. Calling legacy scripts without this variable preserves the original Enterprise-specific evaluation. Generic mode uses only the generic prompt and atomic tools. The diagnosis model does not receive the selected fault ID, injection commands, or private ground truth.

Regenerate mappings after refreshing sources:

```sh
python3 EnterpriseTopology/tools/import_dashboard_topologies.py --ref origin/main
python3 EnterpriseTopology/tools/build_generic_faults.py --ref origin/main
```

## Validation records and limitations

All four real injections and the healthy control completed a full cycle on the current Enterprise lab. The original default route was restored and pending records were cleared. The other 12 topologies have target mappings and offline checks but require validation after their own labs start. This evaluation did not start those labs or call paid diagnosis models. Thirteen mapped topologies must not be reported as thirteen live-validated topologies.

Generic validation requires iproute2 and ping at the source endpoint; ICMP filtering additionally requires iptables and appropriate privileges. Missing capabilities or a failed baseline cause validation to fail and keep benchmarking disabled. Disabling an interface can remove the default route; recovery restores the route saved before injection.

Injection and baseline failures remain environment errors. Model-scoring metrics in generic reports exclude attempts with state_verified=false from their denominator while retaining error records for audit. The runner performs recovery; the model diagnoses and recommends actions without applying repairs.

Recorded offline regression results: 85 passed, 11 skipped (live opt-in), plus 138 passing parameterized subtests. Six browser flows passed, covering 13 topology options, the generic fault list, per-combination validation state, correct topology/fault submission, recovery locks, and mobile layout. The actual service page had no JavaScript errors or horizontal overflow. Enterprise native healthy checks passed 222/222. Raw records are under `results/generic-faults-20261025/`. These are the previously recorded results, not new runs performed during translation.

## Claude authentication and billing

Claude uses ANTHROPIC_API_KEY when set in the dashboard server environment. If
absent, it uses the existing Claude Code login, which can consume Claude subscription
quota. The dashboard shows the chosen authentication preference before starting.
An invalid API key fails; the runner does not retry with a subscription. Restart the
server after changing the key. SDK cost values are estimates, not billing statements.

## GPT-6.1 through Codex subscription

Agent model and Quality judge both offer GPT-6.1 Sol and GPT-6.1 Terra. These
options require an existing ChatGPT login in Codex and consume that account's
Codex subscription limits. API-key authentication is rejected; the SDK child
explicitly blanks API keys and forces ChatGPT login before inference. No model
substitution is made if the selected model is unavailable.

For a subscription-only run, choose a GPT agent and a GPT judge (or Same as agent).
Keeping a Claude judge requires ANTHROPIC_API_KEY and API billing for that stage.
Changing the judge also changes the comparison conditions with historical runs.

The Codex adapter uses a temporary workspace, disables inherited MCP services,
shell execution and integrations, and exposes only the existing read-only network
tools and diagnostic Skills through a host JSON-to-MCP bridge. Each SDK turn
requests a tool-call batch or returns the final diagnosis. The investigation is
bounded by max_turns (20 in the dashboard); each SDK turn times out after 240s.
The transport differs from the Claude agent's native tool calls and is recorded
as host-json-mcp-bridge. Keep that difference visible in cross-model comparisons.

Reports record auth_mode=codex-subscription and cumulative input/cache/output
usage. Subscription dollar cost is unknown (not zero), so total_cost_usd is null.
Each diagnostic case has its own ephemeral Codex thread; judge threads are
separate and receive no network tools. The existing strict scorer and recovery
workflow remain in use. Restart the dashboard after updating backend code.
