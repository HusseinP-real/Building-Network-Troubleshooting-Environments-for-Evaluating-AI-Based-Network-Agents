# Team integration: actual current outcomes

These are recorded reference integration outcomes. The active delivery catalog covers two topologies and 11 scenarios; this report does not establish current acceptance of other team configurations. A passing smoke checks deployment, exact device inventory, one local gateway and real MCP tools. It is not a claim that every route/service/fault is correct.

| Topology | Latest outcome | Actual evidence |
|---|---|---|
| Kath1 | blocked_missing_images | [JSON](../docs/validation/team-integration/Kath1-team-smoke-85cdeaa8a69b.json) |
| Kath2 | passed | [JSON](../docs/validation/team-integration/Kath2-team-smoke-f46a677286c1.json) |
| Kath3 | failed | [JSON](../docs/validation/team-integration/Kath3-team-smoke-aefbb18f98da.json) |
| Kath4 | failed | [JSON](../docs/validation/team-integration/Kath4-team-smoke-1d1bfe5ddf1a.json) |
| Kath5 | passed | [JSON](../docs/validation/team-integration/Kath5-team-smoke-a0c93995b2b6.json) |
| dc_clos_bgp | passed | [JSON](../docs/validation/team-integration/dc_clos_bgp-team-smoke-f4346fbc9a43.json) |
| ospf_enterprise_static | passed | [JSON](../docs/validation/team-integration/ospf_enterprise_static-team-smoke-e1d546f4d66a.json) |
| simple_bgp | passed | [JSON](../docs/validation/team-integration/simple_bgp-team-smoke-863c06cd9e73.json) |

The 75/92-device personal deliverables have separate full fault/recovery and no-fault reports in [the validation index](soft3888-validation-results.md).

Kath3/Kath4 startup and isolated capability probes show VLAN creation failures in this environment. Kath1 needs the unavailable kathara/dhcp image or its original Dockerfile. Source configurations were retained; failed attempts were not relabeled as passes.

No new model diagnosis or grading ran: the attempted pilot stopped at credential preflight. Source scenario prose is preserved; legacy healthy/recovery contract gaps remain explicitly listed in ground_truth/.

Historical 50-device variants are not included in the active delivery catalog. Recorded reference results must not be treated as current validation of the entire team repository.
