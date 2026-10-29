# Fault catalog review and benchmark selection for 13 topologies

Review date: 2026-10-25 (Australia/Sydney). Sources: main d0695b9d and Jennie's candidate branch 2acf8e01660a8c5721126c022af0ce97a57feb07. This was a static review of source code, scenarios, and existing validation records. No deployment, fault injection, or diagnosis-model calls were performed.

## Findings

Use Topology → Fault → Model → Run benchmark. A fault is a topology-specific instance within a shared family, rather than one command executed unchanged on arbitrary topologies. There is no evidence that an existing injection scenario has been validated on all 13 topologies. Prioritize generic mechanisms and expose protocol/service-specific mechanisms according to capabilities while preserving original contributions.

## Existing scenarios

This table describes mechanisms present in source code, not automatic execution already supported by the dashboard.

| UI topology | Source directory/file | Existing mechanisms |
|---|---|---|
| EnterpriseTopology | EnterpriseTopology/lab.py; tools/sade_cases.json | Interface down (r5/r6), keepalived stopped (r5/r8), application egress/database ingress ACL, OSPF passive-interface; healthy control, compound cases, ticket variants |
| EnterpriseTopology75 | EnterpriseTopology75/lab.py | Interface down, keepalived stopped, application egress ACL |
| Kairos Enterprise | EnterpriseTopology_Kairos/lab.py; scenarios/kairos_dns_record | Seven device-level faults from the main topology plus an incorrect DNS record |
| Campus80 | Campus80_Eason/ground_truth.json; fault.py | Stop r01 ospfd; handle watchfrr automatic restart during injection and restore the watchdog |
| Enterprise80 | Enterprise80_Eason/ground_truth.json; scripts | Stop sydr1 ospfd |
| Multi-AS ISP | Multi-AS-ISP-Backbone-W11-75/scenarios/S01–S08 | IS-IS/OSPF interface down, BGP neighbor shutdown, route blackhole, BGP prefix withdrawal; healthy, wrong-device tickets, compound scenarios |
| MultiSite | MultiSite_BGP_OSPF_Benchmark/lab.py | Disable both ISP interfaces, withdraw prefixes from both BGP originators, stop FRR in both branches |
| Jiayuan75 | FaulT-Bench/ground_truth/scenarios.jsonl | Stop HTTP process, incorrect DNS A record, remove OSPF LAN advertisement, EIGRP AS mismatch, healthy control |
| NIKA92 | Same as above | Incorrect gateway plus TCP filtering, incorrect DHCP router option, incorrect HAProxy backend port, BGP remote-AS mismatch, BGP outbound prefix filtering, healthy control |
| P20Enterprise | FaulT-Bench/dataset/p20enterprise_Q/custom/p20-enterprise-v3-* | Failover after primary uplink down, isolation after both uplinks down, server subnet interface down, remove OSPF advertisement, incorrect pc1 default gateway, healthy control |
| Sarah Enterprise75 | Sarah_Enterprise_75/ground_truth/SARAH-ENT-001–004.json | Incorrect default gateway, static blackhole route, router interface down, FORWARD firewall DROP |
| Sarah Service75 | Sarah_Service_75/ground_truth/SARAH-SVC-001–003.json | Stop DNS service, stop DHCP service, incorrect r3 default gateway |
| Jennie Enterprise75 (candidate) | Enterprise-SADE-W11-75/scenarios; scripts (Jennie branch) | Stop FRR, shut down BGP neighbor, stop DNS/HTTP service, interface down; healthy, second FRR fault, wrong-device tickets |

## Recommended common catalog

### Initial core families

| family_id | UI name | Existing examples | Adapter requirements |
|---|---|---|---|
| link_down | Link / interface down | Enterprise variants, Multi-AS, MultiSite, P20, Sarah Enterprise, Jennie | Fix device/interface targets; distinguish outage, redundant failover, and local isolation. Successful ping alone does not prove injection failed. |
| wrong_gateway | Incorrect default gateway | P20, both Sarah topologies, part of the NIKA compound fault | Save the correct route; choose an unavailable next hop in the subnet; verify local reachability and remote failure. Splitting NIKA into a single fault requires revalidation. |
| route_blackhole | Route blackhole | Multi-AS S04, Sarah ENT-002 | Fix destination prefix, table, and priority; restore the original route precisely; check whether a more specific route bypasses the blackhole. |
| traffic_filter | ACL / firewall blocking | Enterprise variants, Sarah ENT-004, part of the NIKA compound fault | Preserve INPUT/OUTPUT/FORWARD, DROP/REJECT, source/destination/port distinctions; independently validate affected and unaffected traffic. |
| healthy_control | Healthy / no fault | Enterprise, Multi-AS, Jiayuan, NIKA, P20, Jennie | No injection; each topology needs its own healthy baseline. False-premise tickets are variants. |

These are reusable templates, not executors already validated across 13 topologies.

### Capability-dependent extensions

| family_id | Name | Subtypes and requirements |
|---|---|---|
| routing_daemon_down | Routing service down | Distinguish ospfd-only from all of FRR; Campus, Enterprise80, MultiSite, Jennie; handle watchdogs and convergence. |
| routing_adjacency | Routing adjacency misconfiguration | OSPF passive-interface, BGP neighbor shutdown/remote-AS mismatch, EIGRP AS mismatch; preserve protocol and cause subtypes. |
| route_advertisement | Route advertisement / policy error | Remove OSPF advertisements, withdraw BGP network statements, reject via BGP prefix-list; distinguish local withdrawal from withdrawal at all originators. |
| gateway_service_down | Gateway redundancy service down | keepalived/VRRP in applicable Enterprise variants; separate from incorrect default gateway. |
| dns_service_down | DNS service down | Sarah Service, Jennie; DNS queries fail while IP services remain reachable. |
| dns_record_error | Incorrect DNS record | Kairos, Jiayuan; verify an incorrect answer rather than merely a timeout. |
| dhcp_service_down | DHCP service down | Sarah Service; validate renewal/new leases, since existing leases may conceal failure. |
| dhcp_option_error | Incorrect DHCP gateway option | NIKA; verify that a new lease receives the wrong router option and restore the lease. |
| http_service_down | HTTP service down | Jiayuan, Jennie; HTTP fails while the network path remains healthy. |
| lb_backend_error | Load balancer backend configuration | NIKA; direct backend access works while the load balancer returns 503. Distinct from an HTTP process stopping. |

standard / wrong-device / misleading-cause describe ticket_variant, not separate fault mechanisms. Compound scenarios combine validated instances, require validation of their combined effect, and recover in reverse order. An isolated second fault is not a completed compound scenario.

## Validation gaps and required fixes

- Jiayuan/NIKA scenarios.jsonl records validated-current-configuration, source hashes, and validation evidence. These were not rerun in this review and do not establish dashboard-runner integration.
- P20 docs/p20-enterprise/validation/status.md records one complete live cycle for six v3 scenarios, not three rounds. Use v3 only; do not count v2/v3 as separate topologies or duplicate scenarios.
- Sarah Enterprise ENT-001 still points to the older Sarah_Enterprise_Network. Its evidence does not directly validate the 75-device version. ENT-002–004 explicitly record 75-device automated_pass.
- Sarah Service DNS is marked PARTIALLY_VERIFIED_ON_75 because the IP control was not checked during the fault. DHCP and incorrect-gateway cases have contributor PASS records.
- Multi-AS ground truth explicitly states NOT_LIVE_TESTED; MultiSite remains planned_until_live_verified. Require evidence matching current source before upgrading status.
- Campus VALIDATION.md contains historical healthy/fault/recovery records. Static ground-truth descriptions are not complete validation evidence; use revision-matched records.
- Jennie scenarios are illustrative and lack runtime validation. Double quotes in inject_F04_http_down.sh and inject_F08_wrong_device.sh cause $(cat /tmp/http.pid) to expand on the host instead of in the container; fix and validate this. F07 is only a second FRR failure. Compound F03 still requires a complete scenario and dual-fault ground truth.
- Shared family names do not establish equal difficulty. Preserve separate instance_id/impact labels for single-link failover and dual-link isolation.

## UI and execution contract

1. Topology: keep all 13 entries browsable.
2. Fault: filter compatible instances by topology_id and use common labels such as Link down · r5/eth0. Mark unadapted instances as Pending adaptation and disable benchmark submission. Do not show 0 faults in a way that implies the source project has no scenarios.
3. Model: choose the diagnosis model here; retain Judge model under evaluation settings.
4. Run benchmark: run only the selected instance and explicitly selected ticket variants by default. Offer All supported faults separately. Clear the previous instance when topology changes.
5. Execution: acquire lab lock → confirm topology/deployment → healthy baseline → inject → verify actual fault and control → agent diagnosis → scoring → finally recover → recovery baseline. Failed injection must not count as failed diagnosis. Failed recovery blocks further runs.
6. The diagnosis model receives only the ticket, public topology information, and permitted tools. Do not expose root-cause labels in fault_id, injection commands, expected answers, or scoring ground truth.

Recommended instance fields: topology_id, instance_id, family_id, subtype, targets, requires, baseline/inject/verify/recover/recovery_verify adapters, ticket_variants, private_ground_truth, source_commit, validation_status, and evaluation_enabled. Resolve actual execution bindings through the backend catalog; do not accept shell commands from the browser.

## Implementation sequence

Normalize existing scenarios into the catalog while retaining provenance and evidence, then parameterize the runner and diagnosis-tool scope currently tied to EnterpriseTopology. Prioritize P20, Jiayuan/NIKA, and the existing Enterprise adapter where complete evidence is available. Enable each combination only after a complete live cycle. Stratify cross-topology comparisons by shared family/subtype and ticket conditions. Averaging every topology's different scenario set does not produce a fair ranking.

This document preserves review findings and recommendations. It does not delete original scenarios, automatically promote candidate scripts to executable status, or claim automatic benchmarking across all 13 topologies.
