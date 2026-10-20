# Week 8 client deployment demo

For the newly implemented network topology, see [P20Enterprise](../p20-enterprise/README.md). This page documents the earlier work on the existing Kath3 topology.

The project demo now uses the repository's existing 32-device Kath3 topology and four native FaulT-Bench scenarios: a healthy false-premise control, a wrong gateway, an ICMP filter, and the existing compound fault. The validator demonstrates configuration changes, checks both affected and unaffected paths, restores the baseline, and records evidence without calling an LLM.

The topology and original compound scenario already existed. This addition supplies the independent cases, manifest, repeatable suite, topology inventory and use-case/test documentation. New live results are **NOT RUN** until the suite executes successfully on a working Kathara/Docker host. Historical reports in `docs/validation/` remain historical evidence, not proof of this new suite.

## Run from FaulT-Bench

```sh
python3 tools/validate_client_demo.py --check-only
python3 -m unittest discover -s tools -p 'test_validate*.py' -v
python3 tools/validate_client_demo.py --repeat 3
```

The first two commands are offline. The third deploys a unique temporary copy of the entire existing Kath3 lab and runs all four cases. Use the repository's existing Docker/Kathara setup. No SADE installation, Python Kathara API, or paid LLM keys are needed for this validator. Existing image requirements still apply.

For one case:

```sh
python3 tools/validate_client_demo.py --case compound
python3 tools/validate_client_demo.py --case gateway --repeat 3
```

Live runs create unique reports in `faultbench/runs/client-demo/` (gitignored). Reports contain topology/scenario hashes, device accessibility, available image digests, software versions, per-command results, configuration snapshots, DROP counters, recovery and cleanup outcomes. The temporary lab path is recorded for debugging. If cleanup fails, run `kathara lclean -d` against that exact path. No global prune is used.

Two consecutive successful check rounds are required for each stable state. Healthy probes require 0% packet loss; expected failures require a ping failure exit status and positive measured packet loss. Missing commands, execution markers, output or timeouts cannot count as successful fault evidence. A failed baseline stops injection. A failed injected case attempts restoration before cleanup. Repeat count covers cycles within one deployment; separate invocations test fresh deployment reproducibility.

## Review material

- [Actual topology](topology.md) and [machine-readable inventory](topology-inventory.json)
- [Use cases and test cases](use-cases-and-tests.md)
- [Configuration changes and presentation flow](configuration-demo.md)
- [NIKA reference and agent integration](nika-reference.md)

## Agent pipeline handoff

The new scenarios use the existing parser and `custom/` discovery. They do not change the published dataset layers, their manifests, or frozen results. After the external agent setup is ready, preview the manifest from `faultbench/`:

```sh
./fb.sh bench --manifest benchmarks/client-demo.csv --agents cc-baseline --dry-run
```

Actual agent execution requires the repository's documented external environment and credentials. This change does not claim to have run NIKA, SADE or an LLM judge. Finish manual lab validation before using the existing agent pipeline, whose lifecycle helpers assume one lab at a time.
