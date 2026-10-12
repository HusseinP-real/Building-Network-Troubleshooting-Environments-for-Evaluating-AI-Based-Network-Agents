# Enterprise80 v2

80-device Kathará OSPF benchmark lab: 12 FRR routers, 68 hosts across Sydney, Melbourne, Brisbane, and a data centre. 18 routed /30 links, 8 LANs. Controlled single fault: `ospfd` stopped on `sydr1`.

**Start here:** `USAGE_GUIDE_CN.md`.

The explicit provisioning script executes the `.startup` configurations with checked Docker commands. It addresses the v1 observation that FRR and IPs were not configured despite a successful `kathara lstart`. A completed deploy is not a successful health check.

This artifact has undergone static validation, not a live Kathará/Docker integration test. Integration into FaulT-Bench/NIKA/SADE runner is not included.
