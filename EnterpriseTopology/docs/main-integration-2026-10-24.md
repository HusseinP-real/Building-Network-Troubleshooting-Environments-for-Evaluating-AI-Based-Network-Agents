# Main integration — 24 October 2026

`origin/main` at `1711b169` was merged into `haosenpeng` at `8872eae7` without conflicts. Existing Dashboard and evaluator changes are retained. The working checkout is `enterprise-topology/SOFT3888_TU14_04`; the other Capstone checkout has not been updated.

## Dashboard support

The existing minimum of **75 real devices** remains in effect. Virtual shared-LAN drawing nodes do not count toward this minimum. Catalog import reads an exact Git archive and parses data; it never runs contributed scripts. Each map and its new fault metadata record the same source revision. Refresh with:

```sh
python3 EnterpriseTopology/tools/import_dashboard_topologies.py --ref origin/main
```

| Topology | Real devices | Fault catalog | Manual Dashboard operations | Automatic SADE |
| --- | ---: | --- | --- | --- |
| EnterpriseTopology | 75 | 7 mechanisms, 2 compounds, 1 healthy group / 20 tickets | Available | Available |
| EnterpriseTopology75 | 75 | 3 mechanisms, 1 healthy group | Available | Unavailable |
| MultiSite | 80 | F01–F03 | Available | Unavailable |
| Multi-AS ISP | 75 | S01–S08 | Unavailable | Unavailable |
| Jiayuan enterprise | 75 | 5 scenarios | Unavailable | Unavailable |
| NIKA Clos | 92 | 6 scenarios | Unavailable | Unavailable |
| **Kairos enterprise** | **75** | **7 native mechanisms + DNS record misconfiguration** | **Unavailable** | **Unavailable** |
| **Eason Campus80** | **80** | **r01 ospfd stopped** | **Unavailable** | **Unavailable** |
| **Eason Enterprise80** | **80** | **sydr1 ospfd stopped** | **Unavailable** | **Unavailable** |

The three additions support topology exploration and per-topology fault selection. Their map, catalog and execution status synchronize across both selectors. Manual and automatic requests are rejected on the server as well as disabled in the UI. Catalog access does not demonstrate live health or agent accuracy. Kairos's seven native definitions share the existing EnterpriseTopology mechanisms; its DNS scenario is additional and has not been added to the 20-ticket SADE suite.

A future executable adapter must establish the selected runtime instance, complete baseline, transport error semantics, fault predicates, recovery checks and shared ownership journal before enabling controls. Enterprise80's current native verification can conflate failed Docker commands with expected negative probes; its baseline checks only part of the network. Existing native scripts remain available for their documented standalone workflows, without a new claim of validation.

Smaller additions remain available in the repository:

- [Kairos Kath3](../../FaulT-Bench/topology_kathara/Kath3_Kairos/kairos_wrong_gateway/README.md): 32 devices, wrong default gateway.
- [Sarah enterprise](../../Sarah_Enterprise_Network/README.md): 6 devices, wrong default gateway.
- [Sarah services](../../Sarah_Service_Network/README.md): 7 devices, stopped DNS or DHCP service.

These and the previously excluded small labs are recorded with counts, source revision and exclusion reason in `dashboard/topologies/excluded.json`.

## Repository cleanup

- Removed the 117-file nested `Enterprise80_Eason/Campus80_Eason` copy only after every file matched the canonical `Campus80_Eason` byte for byte. All unique topology sources, configurations and historical validation logs remain.
- Removed tracked Finder/R history files and Python bytecode. Added cache and future native-log ignore rules. Historical logs cited by validation documents remain tracked.
- Retained the existing local ignore rule for environment leases and recovery journals.
- Corrected Enterprise80 documentation to use the repository's actual directory name and link to the canonical Campus80 package.

## Validation

Final offline/HTTP run: **77 passed, 11 skipped**, with 91 passing parameterized subtests. The 11 skipped tests are opt-in real network cycles. The JUnit XML expands subtests, so its 179 entries are not 179 independent test methods. [JUnit evidence](../results/integration-20261024/offline-tests.xml).

```sh
/path/to/nika-demo/.venv/bin/python -m pytest EnterpriseTopology/tests Campus80_Eason/tests -q --junitxml=/tmp/main-integration-offline.xml
```

Browser regression: **6 leaf workflows passed** using the explicitly labelled MOCK executor, real local HTTP and Chrome. This includes map/fault selector synchronization for all three new catalogs, disabled execution buttons, the original selected benchmark flow, compound recovery, healthy controls and mobile layout. The Node runner additionally counts the parent group; it is not an extra workflow. Run with Playwright on `NODE_PATH`, `BROWSER_EXECUTABLE` pointing to Chrome, and:

```sh
node --test EnterpriseTopology/tests/dashboard_delivery.cjs
```

Ruff lint and formatting checks passed for the modified Python modules and tests. JavaScript syntax checks and `git diff --check` passed. Snapshot regeneration from the pinned source revision is covered by a regression test; all new devices, edges, fault IDs and source paths are checked. Server-side rejection tests cover every new catalog fault without acquiring a runtime lease.

No new labs were deployed, no live fault was injected, and no model/API request was made. Existing network resources remain unchanged. Previous delivery evidence remains historical and has not been overwritten.

During final review, additional untracked local files with ` 2` suffixes were present elsewhere in this checkout. They are outside the confirmed nested duplicate cleanup and have been left untouched and excluded from the integration commit.
