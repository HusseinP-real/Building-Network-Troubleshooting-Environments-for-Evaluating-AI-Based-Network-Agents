# Acceptance procedure

The size requirement is 75–100 devices. This lab has92: 88 exported from
NIKA `DCClosService(l)` plus four documented service/management nodes. Its
228 collision domains and all original router interfaces remain traceable.

`tools/test_nika92_reference.py` re-instantiates the pinned reference and
compares devices, interfaces, original router addresses, neighbor AS values,
router IDs and advertised prefixes. It also checks no duplicate addresses,
consistent link subnets, complete roles and four executable case contracts.

The live validator uses fresh copies and unique lab names. It must verify:

1. Exactly92 running devices and228 declared collision domains; runtime image
   IDs and shared-program hashes match.
2. All52 BGP router peer counts match the source graph: Super-Spines16,
   Spines12, Leaves4. All28 web servers are remotely reachable.
3. Four DNS servers answer preserved reference names and the added application
   record; DNS TCP, actual DHCP client address/default, HAProxy frontend and
   management allow/deny are correct. The whole baseline has99 assertions.
4. Each fault passes baseline, injection, post-check, repeated injection,
   explicit recovery and the complete healthy baseline after recovery.
5. One Leaf uplink failure leaves three sessions and service access working;
   restoring it brings back four sessions and the whole baseline.
6. Actual diagnostic MCP servers initialize and use all40 endpoint roles in
   deterministic sampled reachability. This is not an all-pairs test.
7. Exact-lab cleanup succeeds. Repeat on a second fresh deployment.

The DHCP `[TRIGGER]` releases and renews client_0 after server changes and
recovery. Fault and recovery commands alter disposable runtime state; source
healthy configurations remain unchanged.

Evidence is JSON under `docs/validation/soft3888/`, linked from the results
index. Inspect the topology/scenario/runtime hashes and real outputs. The
41-device reports are historical prototype tests only. No LLM diagnosis or
judge scores are implied by successful network acceptance.
