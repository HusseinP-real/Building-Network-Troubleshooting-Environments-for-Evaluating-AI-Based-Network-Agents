# SOFT3888 TU14 04

P20 builds reproducible network troubleshooting environments for evaluating AI-based network agents.

## April’s P20 enterprise topology

[P20Enterprise v3](FaulT-Bench/docs/p20-enterprise/README.md) expands April's topology to **75 devices: 25 routers, 35 PCs and 15 server endpoints**, with 47 subnets, eight OSPF areas and redundant site uplinks. Six scenarios cover failover, site isolation, OSPF advertisement withdrawal, a server-interface fault, a wrong gateway and a healthy control. See the [versioned validation status](FaulT-Bench/docs/p20-enterprise/validation/status.md); the old nine-device report applies only to v1. NIKA/SADE evaluation remains separate.

From `FaulT-Bench/`:

```sh
python3 tools/validate_p20_enterprise.py --check-only
python3 tools/validate_p20_enterprise.py --repeat 3
```

The second command requires Docker, Kathara and the `kathara/base` and `kathara/frr` images. The guide covers topology, use cases, tests, configuration changes and NIKA reference mapping.

## Existing Kath3 client deployment and demo

The [client demo guide](FaulT-Bench/docs/client-demo/README.md) covers the existing 32-device Kath3 topology, use cases, native fault scenarios, configuration changes, tests and NIKA reference mapping.

From `FaulT-Bench/`:

```sh
python3 tools/validate_client_demo.py --check-only
python3 -m unittest discover -s tools -p 'test_validate*.py' -v
```

With Kathara and Docker running, validate all four cases and recovery over three cycles:

```sh
python3 tools/validate_client_demo.py --repeat 3
```

Live validation uses a unique temporary lab and saves evidence under `FaulT-Bench/faultbench/runs/client-demo/`. Offline passes do not establish live-network or AI-agent success.

See the [FaulT-Bench README](FaulT-Bench/README.md) for external agent setup and the existing benchmark pipeline. The [original compound-fault walkthrough](FaulT-Bench/docs/haosenpeng-compound-fault.md) covers interactive diagnosis and repair. New custom cases remain separate from published dataset layers and frozen results.

## Data centre fabric

[DatacenterFabric](DatacenterFabric/README.md) provides 75 devices and 84 links with eBGP, three-path ECMP and an application/backend dependency. Its six evaluator-only fault/healthy cases, ground truth, injection checks and recovery plans are in [scenarios.json](DatacenterFabric/scenarios.json). See the [validation report](DatacenterFabric/docs/validation.md) for network and failover evidence; live SADE diagnosis evaluation remains pending.

## Other team topologies

- [Main integration and Dashboard support matrix](EnterpriseTopology/docs/main-integration-2026-10-24.md): merge status, nine displayed topologies, execution limits, cleanup and validation.
- [Enterprise topology and SADE evaluation](EnterpriseTopology/README.md), including Haosen’s existing dashboard.
- [Standalone 75-device enterprise topology](EnterpriseTopology75/README.md).
- [Multi-site BGP/OSPF benchmark](MultiSite_BGP_OSPF_Benchmark/README.md).
- [Abilene/YUMAng extension](SOFT3888_Abilene_YUMAng_Deliverable/README.md).
- [Missing-return-route scenario](kathara_scenario/missing_return_route/README.md).
- [Kairos enterprise topology](EnterpriseTopology_Kairos/README.md) and [Kath3 wrong gateway scenario](FaulT-Bench/topology_kathara/Kath3_Kairos/kairos_wrong_gateway/README.md).
- [Eason Campus80](Campus80_Eason/README.md) and [Enterprise80](Enterprise80_Eason/README.md).
- [Sarah enterprise](Sarah_Enterprise_Network/README.md) and [DNS/DHCP service network](Sarah_Service_Network/README.md).
- [Enterprise-SADE-W11 candidate](Enterprise-SADE-W11-75/README.md): 75-device topology, statically validated only; not deployed or end-to-end tested.
- [Kath6 static-route example](Own/README.md): small proof-of-concept scenario.
- [NIKA complex enterprise OSPF run guide](README_RUN.md): installation notes for a separately supplied patch package.

Additional member documentation is in `Topology_README-wk7/`.
