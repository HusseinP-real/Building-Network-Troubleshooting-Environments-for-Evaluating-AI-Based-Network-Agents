# Reproduce, evaluate and review SOFT3888

## Current scope

The deliverables are Kath5_Jiayuan_75Devices (75 devices,
43 collision domains) and NIKA_Clos_Jiayuan_92Devices (92 /228). Each has four
core faults. There is one optional NIKA92 compound case and one healthy
negative-control case per topology: 11 source-backed cases in total.
The 92-device generator directly exports pinned NIKA DCClosService(l) and
reads committed service templates, with no 41-device prototype dependency.

The active Ground Truth catalog covers these two topologies and their 11
scenarios. It records source hashes, role coverage, fault labels, recovery
contracts and recorded evidence. Other inherited datasets remain separate.
Catalogs contain answers and are evaluator-only; never give them to agents.
See [delivery scope](soft3888-delivery-scope.md) for inclusion and evidence boundaries.

The original 560-scenario release, base80 manifest and 3960 archived results
are preserved. Their historical scores do not validate new custom scenarios.

## Prepare the environment

Linux, Docker28.x, Kathará's VDE plugin, `/dev/net/tun`, Python3.12 and uv are
host prerequisites. The script does not replace the host kernel, disable
TLS/signatures or globally prune Docker resources.

```sh
# From the repository root. Reuses existing SADE source; never resets it.
bash tools/setup_soft3888.sh
source .venv/bin/activate
python tools/check_soft3888_environment.py
```

On this cloud machine use `SOFT3888_VENV=/workspace/venvs/faultbench` for setup,
then activate that environment. `UV_CACHE_DIR`, `XDG_CACHE_HOME` and
`MPLCONFIGDIR` may be configured to writable cache directories.
`FAULTBENCH_RUNTIME_DIR` can relocate the verified runtime cache.

The builder creates the declared soft3888 images from digest-pinned bases.
On vfs, one read-only program tree per source image avoids per-device copies;
configuration, processes, routes and service data remain per-device. Manifests
verify original and device image IDs plus program-tree hashes. Root diagnostic
tools are tested; non-root tools requiring preserved file capabilities are
not claimed. Later APT rebuilds may select newer packages: preserve the
experiment's exact image IDs/receipts for software-identical reproduction.

## Verify network scenarios without model calls

```sh
python -m unittest discover -s tools -p 'test_*.py'
python tools/validate_soft3888.py Kath5_Jiayuan_75Devices --repeats 2
python tools/validate_soft3888.py NIKA_Clos_Jiayuan_92Devices --repeats 2
python tools/validate_soft3888.py Kath5_Jiayuan_75Devices --experiment faultbench/experiments/jiayuan75_control.json --repeats 1
python tools/validate_soft3888.py NIKA_Clos_Jiayuan_92Devices --experiment faultbench/experiments/nika92_control.json --repeats 1
python tools/validate_soft3888.py NIKA_Clos_Jiayuan_92Devices --experiment faultbench/experiments/nika92_compound.json --repeats 1
python tools/summarize_soft3888.py --output docs/soft3888-validation-results.md
python tools/build_ground_truth_catalog.py --topology Kath5_Jiayuan_75Devices --topology NIKA_Clos_Jiayuan_92Devices
```

Run large labs sequentially. The validator uses fresh unique labs, real
commands/exit codes, convergence gates and exact-lab cleanup. Both no-fault
cases were checked on fresh deployments. These are not model diagnosis runs.
The compound recipe tests both partial repair orders. The source NIKA design
has seven expected-down sampled external-client paths; its service paths are
checked independently. Do not turn these inherited boundaries into invented
injected faults.

## Run SADE and an alternative model fairly

Provide `ANTHROPIC_API_KEY` and `FAULTBENCH_OPENAI_API_KEY` securely in environment
settings, then save/publish the configuration. The second binding is mapped
in memory to `OPENAI_API_KEY`, whose prefix is reserved by the cloud proxy.
No secret value belongs in Git or chat. Existing direct OpenAI bindings win.

```sh
# Planning makes no model calls and needs no keys.
python tools/evaluate_soft3888.py --manifest faultbench/benchmarks/soft3888_pilot.csv
# Four pilot cases: one core fault and one healthy control per topology.
python tools/evaluate_soft3888.py --manifest faultbench/benchmarks/soft3888_pilot.csv --execute
# Eight core faults + two healthy controls. Two agents, three repeats = 60 runs.
python tools/evaluate_soft3888.py --repeats 3 --execute
python tools/evaluate_soft3888.py --summarize
# Keep the additional compound workload separate.
python tools/evaluate_soft3888.py --manifest faultbench/benchmarks/nika92_compound.csv --execute
```

The default agents are SADE/Claude and react-full/GPT-5, reusing the existing
runner and identical diagnostic tool backends. Both receive only device/L2
layout and the user ticket. Ground Truth, expected checks and fixes remain
outside their context. Runs are sequential; each gets a fresh lab. Preflight
checks credentials and runtime before spending model tokens. Authentication,
no output, judge failure and cleanup failure retain separate statuses.

`plan.json` records source hashes, the exact cells and repeats. Actual
`result.json` stores the returned verdict, tools/tokens, per-axis judgments,
agent duration and lifecycle duration. `comparison.json` is computed from
actual result files: confusion matrix, precision/recall/false-positive rate,
exact device set accuracy, graded root-cause accuracy and cost/timing.
Missing predictions reduce classification coverage; they are not counted as
correct negatives. No runs produces `not_run`, not invented zero/100% scores.
Root-cause accuracy uses must root-cause/mechanism judge axes, separately from
overall outcome score. Existing judge billing is unavailable and stays null;
agent-reported cost must not be labeled total evaluation cost.

The new pilot was attempted and stopped before deployment because both model
credentials were absent. `docs/validation/soft3888/model-evaluation-preflight.json`
records that actual blocked execution. The historical alternative-agent
comparison can be reproduced without keys:

```sh
python tools/report_archived_agents.py
python tools/compute_metrics.py --check
python tools/dataset_stats.py --check
```

See soft3888-agent-comparison.md: the archived comparison is on the original
dataset, and archived wall_seconds includes lifecycle work. It is not a new
accuracy/speed/cost result on the 75/92-device topologies.

## Other team topologies

Other team topology configurations are outside this delivery's active catalog.
The shared tools can inspect the current checkout, but no new acceptance is
claimed for P20Enterprise or other team deliverables. Team manifests select
existing source cases and must be regenerated when those cases change:
`python tools/build_team_manifests.py`. Historical integration evidence is
separate from current inventory, exhaustive fault validation and model scores.

```sh
docker pull kathara/base:latest
docker pull kathara/frr:latest
python tools/build_team_images.py
python tools/prepare_soft3888_runtime.py --image kathara/base:latest --image kathara/frr:latest --image kathara/base-stress:latest --image kathara/frr-stress:latest --image frr-with-vrrp-relay:latest
python tools/validate_team_smoke.py
python tools/check_soft3888_environment.py
```

The stress/VRRP variants are rebuilt from package recipes already supplied by
SADE/the project. The build uses signed Debian repositories over verified
HTTPS, preserves installed FRR binaries and records resolved source digests.
An initial unused FRR repository fetch was blocked by the proxy; the build
now limits package installation to the Debian repositories that supply these
packages, without weakening artifact verification. Failed attempts remain
recorded separately.

`kathara/dhcp` could not be pulled and has no supplied build recipe; Kath1
requires the team's original image or Dockerfile. It is not silently replaced.
The current environment also rejected creation of a VLAN netdev in an
isolated capability probe. Read the actual legacy startup/smoke reports before
calling VLAN-based labs healthy here; a suitable host/network capability is
required. Preserve source configurations rather than claiming a network fix
from a passing inventory test.

Legacy datasets and recorded cloud reports are reference evidence; their
counts and outcomes do not establish current acceptance of unrelated team
work. Historical 50-device variants and older standalone cases are not part
of the active delivery catalog. Do not add them just to satisfy stale links.
