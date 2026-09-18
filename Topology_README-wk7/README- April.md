# SOFT3888 TU14 04

P20 builds reproducible network troubleshooting environments for evaluating AI-based network agents.

## New custom topology

[P20Enterprise v2](FaulT-Bench/docs/p20-enterprise/README.md) expands April's topology to **40 devices: 16 routers, 16 PCs and eight server endpoints**, with 29 subnets, five OSPF areas and redundant site uplinks. Six scenarios cover failover, site isolation, OSPF advertisement withdrawal, a server-interface fault, a wrong gateway and a healthy control. See the [versioned validation status](FaulT-Bench/docs/p20-enterprise/validation/status.md); the old nine-device report applies only to v1. NIKA/SADE evaluation remains separate.

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
