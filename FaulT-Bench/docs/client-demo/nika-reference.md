# NIKA reference and repository integration

This implementation follows the scenario/fault/verification/evaluation separation described in the official [NIKA task guide](https://github.com/sands-lab/nika/blob/main/docs/creating-benchmark-tasks.md). It uses this repository's native FaulT-Bench section format rather than asserting that project JSON is a NIKA API.

| Concern | Existing repo mechanism | Client demo addition |
|---|---|---|
| Network environment | `topology_kathara/Kath3` | Actual 32-device inventory and diagram |
| Fault definition | `[INJECTION]` in native scenario files | Separate gateway and filter cases alongside existing compound case |
| User report | `[PROMPT-TO-AGENT]` | Accurate single-fault tickets and a false-premise healthy ticket |
| Verification | `[PRE-CHECK]`, `[POST-INJECT-CHECK]` | Offline validation and isolated live suite |
| Reference diagnosis | `[GROUND-TRUTH]`, `[FIX]`, `[SCORING-AXES]` | Ground truth and repair definitions for the new cases |
| Agent evaluation | Existing `faultbench` runner and external SADE/NIKA tooling | Dedicated `benchmarks/client-demo.csv` |

The existing `faultbench/lab.py` registers agent-facing labs through the Kathara Python API so NIKA tools can find a named lab. The new CLI validator serves human network validation only. Do not assume its temporary CLI lab can be discovered by agent tooling.

Ground truth is evaluator material. The ticket is agent-facing; avoid mounting the complete repository or exposing injection/ground-truth files to the agent. Validate those boundaries using the chosen external agent setup.

The new cases make no claim of a version-specific NIKA taxonomy mapping. Their NIKA-label sections explicitly mark them as project reference cases. Pin and inspect the team's selected NIKA version before adding native adapters or taxonomy labels. The existing original compound scenario and published reference datasets are unchanged.

References: [NIKA](https://github.com/sands-lab/nika), [task creation](https://github.com/sands-lab/nika/blob/main/docs/creating-benchmark-tasks.md), the local `faultbench/scenario.py`, `faultbench/lab.py`, and `docs/haosenpeng-compound-fault.md`.
