# SOFT3888 TU14 04

P20 builds reproducible network troubleshooting environments for evaluating AI-based network agents.

## New custom topology

[P20Enterprise](FaulT-Bench/docs/p20-enterprise/README.md) adds actual network configuration: three routers, four PCs, two server endpoints and six subnets. It includes server-interface, missing-return-route and wrong-gateway fault scenarios with an isolated validator. All four cases passed three live test cycles on 16 September 2026, including recovery and cleanup. See the topology guide for saved evidence. NIKA/SADE evaluation remains pending.

From `FaulT-Bench/`:

```sh
python3 tools/validate_p20_enterprise.py --check-only
python3 tools/validate_p20_enterprise.py --repeat 3
```

The second command requires Docker, Kathara and the `kathara/base` image. The guide covers topology, use cases, tests, configuration changes and NIKA reference mapping.

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
