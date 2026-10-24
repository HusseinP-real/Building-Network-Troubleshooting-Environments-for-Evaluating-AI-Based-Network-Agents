# Benchmark configuration and optional laboratory debugging

Dashboard provides one benchmark form: topology → fault injection → agent model → Run benchmark → results. Topology is a network explorer with a synchronized topology selector and a link back to benchmark configuration. Manual laboratory actions are secondary, under a collapsed Advanced laboratory debugging disclosure. The server filters the catalog to topologies with at least 75 real devices; virtual shared LAN nodes do not count. Selecting a topology changes the map, fault catalog, support status and fixed execution directory together. Controls remain disabled until the selected map loads successfully.

## Use

From the repository root, run:

```sh
python3 EnterpriseTopology/dashboard/server.py --port 8766 \
  --nika-root /Users/husseinpeng/Documents/ChatGPT/Capstone/nika-demo
```

The server uses that NIKA installation's Python for both the existing evaluator and fixed manual worker. `--python` can select another server-side interpreter. Browser requests cannot select interpreters, paths or commands. The UI binds only to loopback. Existing model credentials remain in the server environment; manual actions do not need them.

1. In **Configure a run**, select a topology, the fault to inject, and an agent model. The fault list is filtered to the selected topology. Expand **Fault scenario** for its description, targets, expected impact and runtime details.
2. Click **Run benchmark** directly. No manual injection is required. The evaluator owns baseline checks, injection, diagnosis, scoring and recovery. Progress appears underneath, then the new report is selected in Results. Existing saved reports are explicitly labelled with their original topology and fault scope; changing configuration prepares a new experiment without relabelling old scores.
3. **Evaluation settings** contains the quality judge, repeats, diagnostic settings and scenario coverage. The default evaluates the selected mechanism's associated ticket cases. For example, `core-uplink` includes its accurate, vague and misleading tickets using the same injection mechanism. An alternative scope runs all 20 EnterpriseTopology cases.
4. For independent environment inspection or recovery, expand **Advanced · laboratory debugging** below the benchmark progress area. These optional manual actions never call a model API. Healthy controls can run a baseline but cannot be injected. They are not prerequisites for a normal benchmark.
5. Pending laboratory changes block a new benchmark and show a **Review recovery** notice in its form. A pending entry means a mutation was attempted and has not been conclusively recovered, including commands that failed or timed out after possibly taking effect. Use the original compound selection to recover all attempted components, or select an individual pending entry for targeted repair. All attempted repairs are tried even if an earlier repair fails. Pending entries clear only after repair predicates and the full baseline pass. If another component still keeps the baseline unhealthy, repair it and retry recovery; repeated repairs are scoped and idempotent.

Saved health on the topology page is historical. Empty pending state is not proof of live health. The dashboard does not deploy, rebuild or clean labs; start the intended lab through its own existing lifecycle before testing.

## Support matrix

“Adapted” below means a native execution path is implemented and covered offline. It does **not** claim a real container cycle passed during this change.

| Topology ID | Real devices | Manual execution | Automatic SADE |
| --- | ---: | --- | --- |
| `enterprise-75` | 75 | 7 faults, 2 compounds, 1 grouped healthy control | Selected group or all 20 ticket cases |
| `enterprise-75-standalone` | 75 | Its own 3 native faults plus a healthy control | Disabled |
| `multisite` | 80 | Its own F01–F03 | Disabled |
| `multi-as-isp` | 75 | Catalog only: 8 scenarios | Disabled |
| `jiayuan-75` | 75 | Catalog only: 5 scenarios | Disabled |
| `nika-92` | 92 | Catalog only: 6 scenarios | Disabled |

EnterpriseTopology mechanisms come directly from `lab.py:FAULTS`; metadata and verification predicates come from `tools/sade_cases.json`. Ticket wording variants are grouped by their `fault` field. The three healthy tickets are grouped as one no-mutation control.

| Mechanism | Target | Expected effect |
| --- | --- | --- |
| `core-uplink` | r5 eth0 | One OSPF uplink down; redundant paths retain application access |
| `core-uplink-r6` | r6 eth0 | Alternate-location uplink failure |
| `gateway-service` | r5 keepalived | r6 assumes staff gateway ownership |
| `gateway-service-r8` | r8 keepalived | Branch standby daemon stopped; r7 remains primary |
| `database-acl` | app OUTPUT TCP/8080 | Backend blocked; application returns HTTP 503 |
| `database-ingress-acl` | database INPUT from app TCP/8080 | Backend ingress blocked; ops direct access remains |
| `ospf-passive-r7` | r7 OSPF eth0 | Link remains up, but adjacency is suppressed |
| `compound-uplink-acl` | r6 eth0 + database ingress ACL | Both causes injected and independently checked |
| `compound-ospf-gateway` | r7 OSPF eth0 + r8 keepalived | Both control-plane failures injected and checked |

EnterpriseTopology75 uses its own `lab.py`, `FAULTS`, health probes and directory, with only its three actual mechanisms (`core-uplink`, `gateway-service`, `database-acl`). MultiSite uses its native `FAULTS`, `fault`, `exec_cmd`, and `run_checks`: F01 disables two ISP-A peering interfaces, F02 withdraws ISP-A's service prefix from both speakers, and F03 stops FRR on both Branch-A routers. MultiSite also checks all 80 device endpoints, verifies the affected path and an unaffected control path, and requires the native inner-command exit marker. Expected probe failure is inverted inside the remote shell, so a transport failure cannot count as successful fault verification. Recovery waits for convergence and checks the full baseline.

Adapters compare the selected view against the local device inventory and interface/collision-domain bindings. Shared LAN spoke IDs are resolved to their real collision domain. Compatibility is never inferred by renaming devices.

Other executors were inspected but left disabled for this interactive workflow. Multi-AS's existing `scripts/scenario.sh` refuses S08 and its baseline script explicitly requires human interpretation of protocol output. The FaulT-Bench validation runner used by Jiayuan/NIKA creates temporary experiment copies, deploys and cleans them as a batch lifecycle. It is not directly an adapter for an already selected persistent lab. Their catalogs are read from existing scenario ground truth, with no execution claimed. An additional adapter must bind the actual runtime instance and establish baseline, effect checks, transport semantics and recovery before enabling these controls.

## Exclusion, persistence and isolation

- `POST /api/manual` accepts exactly `topology_id`, `fault_id`, `action`. Actions are `baseline`, `inject`, `verify`, `recover`. Unknown IDs, cross-topology faults, extra fields and catalog-only execution requests are rejected. Injection of healthy controls is rejected.
- `POST /api/run` requires the selected topology and fault, validates scope and existing model/profile fields, and rejects automatic execution outside EnterpriseTopology. `GET /api/faults?topology_id=…` and `/api/manual/status?topology_id=…` expose operator metadata and execution state.
- Each native lab directory has `results/control/environment.lock` and an atomic, fsynced `state.json`. Pending intent is persisted **before** each uncertain mutation. These files are ignored by Git and survive server restarts. A corrupt journal fails closed. Do not delete the recovery journal to bypass a blocked environment.
- `flock` prevents overlapping manual mutations, duplicate clicks, other dashboard processes, and EnterpriseTopology evaluator CLI sessions. Automatic subprocesses inherit the lease descriptor. Interrupted workers retain it while still running. Nested evaluator calls share the owning context; unrelated threads cannot bypass exclusion.
- Direct operator-issued Docker/Kathara commands and native lifecycle CLIs remain outside this coordinator. Do not run those against a lab while it is controlled by a dashboard/evaluator session.
- Fixed native adapters use only the selected lab's directory. They do not call global Kathara wipe or Docker prune. No browser command, path, shell fragment or deployment recipe is accepted.
- New dashboard execution logs redact inherited secret values. Ground truth/catalogs and recovery state are for operators and the scorer. The diagnostic prompt and its existing read-only MCP tools do not receive them. Regression tests reject access to catalog, journal and manifest paths from the diagnostic agent.

## Validation recorded for this change

On 22 October 2026 (Australia/Sydney):

- 46 offline tests passed in the existing NIKA Python environment, including topology/fault grouping, unchanged scoring/evaluator regressions, native command mapping, illegal HTTP requests/origins, process/thread exclusion, duplicate requests, selected-case invocation, credential redaction, healthy controls, failed/partial injection recovery, corrupt state and restart persistence, and diagnostic/scorer isolation.
- Browser QA used `tests/serve_dashboard_fixture.py` on a separate loopback port. The page explicitly says **MOCK executor**. Its real HTTP handlers, UI and durable lease/journal coordinator were exercised with fake execution/model steps: normal baseline/inject/verify/recover; a compound injection failing on the second component; retained pending recovery; successful compound recovery; healthy-control injection disabled; selected automatic evaluation; automatic/manual mutual exclusion; topology switching; and catalog-only controls disabled.
- After the workflow correction, browser QA directly selected `gateway-service-r8` and clicked **Run benchmark** without opening manual tools. The mock run completed and its corresponding one-case report rendered with 1/1 complete runs. Topology explorer selection synchronized back to the benchmark form, and unadapted automatic targets remained disabled.
- The actual server on port 8766 was opened separately and checked read-only for EnterpriseTopology and MultiSite selection, target directory, matching map, catalog and button support. No mutation button or model-backed benchmark was run against real labs.
- Real-container and paid model validation were **not performed**: target-environment confirmation was requested, but the response clarified the desired workflow rather than authorizing a container cycle. Historical saved health is not current validation evidence.

Run the offline suite (it opens temporary loopback HTTP test servers):

```sh
/Users/husseinpeng/Documents/ChatGPT/Capstone/nika-demo/.venv/bin/python \
  -m unittest discover -s EnterpriseTopology/tests -v
```

Reproduce the separate browser mock fixture:

```sh
python3 EnterpriseTopology/tests/serve_dashboard_fixture.py --port 8877
```

All implementation changes remain local. No commit or push was made.


## Material Design presentation

The benchmark form follows the [Material 3 select guidance](https://github.com/material-components/material-web/blob/main/docs/components/select.md): outlined fields with floating labels, supporting text, themed focus/disabled states, and elevated menus with selected-state checks. Native select elements retain the application values; an accessible read-only combobox and listbox present those values. Pointer selection, Arrow keys, Enter, Escape, Tab, Home/End and type-ahead use the same native change events as the existing benchmark configuration. Programmatic selection and disabled-state changes are synchronized. No external UI runtime or model call is required.

The primary fields use a three-column layout on desktop. Evaluation settings occupy a matching three-column grid, then two columns and one column at narrower breakpoints. The run action sits beside a compact readiness summary. Browser validation checked 1440px desktop and 390px mobile layouts (56px fields, no horizontal overflow), menu/keyboard selection, dynamic fault lists, healthy controls, disabled benchmark states, and a complete MOCK run confirming selection of r8 maps to `gateway-service-r8` in its result report. The browser viewport override was reset after validation.
