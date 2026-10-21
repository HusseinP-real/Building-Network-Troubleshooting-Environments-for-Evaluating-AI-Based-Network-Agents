# SADE local enterprise benchmark v3

This is a local evaluation on one 75-device Kathara topology, not an official NIKA score. Version 3 has 20 tickets: seven individual physical faults across four fault classes, alternate fault locations, two compound states, accurate/vague/misleading reports, and three healthy false-premise reports. Seeded scheduling changes order, not fault parameters. Alternate locations are explicit reproducible cases; arbitrary location randomization is not implemented.

## Scoring

Scores are separate:

- `rca_exact`: anomaly state, complete device set, and every resource/fault-type/device triple match hidden ground truth. Missing, extra, swapped or contradictory causes fail.
- `explanation_correct`: an independent no-tools LLM judge checks causal mechanisms, relevant live evidence, completeness and contradictions.
- `repair_correct`: the judge approves the prose AND every structured repair action matches a targeted command from the hidden approved plan.
- `full_correct`: all three above pass. Correct labels alone cannot earn full credit.

The deterministic command-plan gate never executes model commands. It accepts the runner's recovery command and declared simple alternatives (for example, a direct deletion of the injected ACL rule). Quoting differences are normalized with `shlex`. Other equivalent repair commands can be rejected: this is a conservative, constrained repair-plan metric, not a general shell equivalence checker. The LLM judge can make mistakes; review its recorded reasons and keep judge model/rubric fixed when comparing runs. It runs in a fresh empty temporary workspace, with no tools, MCP, project settings or continuation of the diagnosis session.

Judge failure or missing quality assessment leaves explanation, repair and full correctness unscored (`null`), and makes the CLI run unsuccessful. Structural scores and environment recovery still remain available. Summary metrics use all attempts conservatively and also show scored-only rates and unscored counts. Historical reports are not modified or retroactively assigned quality credit. `summarize` recomputes structural fields and only retains v3 quality judgments; it does not make model calls.

Each live case calls the diagnosis model and a separate judge. Judge defaults to the same model in an independent session; use `--judge-model` to choose a different one. Judge usage/cost/reasons are recorded separately. Repairs in the environment are always performed by the runner; evaluating recommendations does not establish that the agent can execute a repair.

## Setup and running

Start Docker Desktop and ensure Kathara is installed. Use the Python interpreter from the NIKA environment (install its `sade` extra). Authenticate the model in the execution shell; never store credentials in the repo.

```bash
python3 lab.py status
python3 lab.py check
/path/to/nika/.venv/bin/python tools/sade_eval.py validate --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run core-uplink --nika-root /path/to/nika --model MODEL
/path/to/nika/.venv/bin/python tools/sade_benchmark.py run --nika-root /path/to/nika --model MODEL
```

Default: `--prompt-style generic --tool-profile atomic`. Generic instructions do not explicitly hint at VRRP or redundant uplinks. Atomic mode exposes basic reachability, device inventory and individual read-only container commands, with no helper MCP server. The initial five-flow reachability map remains shared across tool profiles; the ablation removes bulk root-cause diagnostic helpers, not all aggregate reachability. SADE project skills remain available in both live profiles. Sweep mode also provides bulk diagnostic helpers.

Each case starts from a full healthy baseline, verifies every injected fault, starts a fresh diagnosis session, scores, then restores faults in reverse order and verifies full baseline health. Cleanup includes partially applied injections. If restoration fails, the suite stops. Reports include versions, manifest hash, actual system prompt, tool trace without the previous 10,000-character trace truncation, model, budgets, profile, judge verdict and recovery evidence. MCP responses themselves still have bounded per-command output.

Health checks retry each failed read-only probe up to three times with a two-second delay, retaining all attempts in the health JSON. Successful probes are not repeated. Persistent failures still block model calls. Fault mutation commands and paid model requests are never automatically retried by this policy. SDK error results are raised after draining the stream, with subtype and turn count included for diagnosis.

## Output format

```text
=== DIAGNOSIS ===
is_anomaly: true
resource_id: interface/r5/eth0
fault_type: interface_down
faulty_devices: r5
root_causes: [{"resource_id":"interface/r5/eth0","fault_type":"interface_down","device":"r5"}]
repair_actions: [{"device":"r5","command":"ip link set eth0 up"}]
diagnosis_text:
Explain observations and the causal mechanism.
repair_text:
Explain targeted restoration and checks.
=== END ===
```

For multiple causes use `multiple` for scalar resource/fault fields and list all triples. For healthy state use `false`, `none`, `none`, `none`, and two empty JSON arrays; recommend no corrective changes. Legacy single-cause answers can still receive structural credit, but missing separate repair plans cannot receive repair or full credit.

## Paired ablations

```bash
/path/to/nika/.venv/bin/python tools/sade_benchmark.py run \
  --nika-root /path/to/nika --model MODEL --judge-model JUDGE_MODEL \
  --ablation --seed 42 --repeats 1 \
  --cases core-uplink-vague core-uplink-misleading database-ingress-acl-misleading healthy-policy
```

This runs each selected ticket under generic/guided × atomic/sweep, plus a no-tools control. Twenty cases × five configurations = 100 diagnosis calls plus quality judging for one full pass; use a subset first. Reports include `by_experiment` groups. Keep model, judge, cases, seed, turn budget and repeats fixed. In no-tools mode, the judge assesses causal correctness without requiring inaccessible live observations. Misleading tickets are explicit paired cases and are scored by category.

## Dashboard and historical results

```bash
/path/to/nika/.venv/bin/python dashboard/server.py --nika-root /path/to/nika
python3 tools/sade_benchmark.py report results/sade/benchmark-REPORT.json
python3 tools/sade_benchmark.py summarize
```

The loopback dashboard defaults to generic/atomic, allows profile selection, shows separate field/explanation/repair/full outcomes, and labels old reports as legacy field accuracy. Historical 100% exact RCA is not full v3 correctness. Restart an existing dashboard process to load updated server code. Results are under `results/sade/`; old raw reports remain intact.

## Verification

```bash
/path/to/nika/.venv/bin/python -m unittest discover -s tests -v
python3 tools/verify_sade_cases.py compound-uplink-acl compound-ospf-gateway
```

The reusable verifier makes no model calls. It validates actual injection, captures per-cause diagnostics, restores only its injected faults, checks full baseline health, and saves a verification artifact. Offline regressions cover wrong explanations/repair verdicts, unsafe or wrong-owner repair commands, healthy unnecessary repairs, missing/invalid judge output, compound completeness, and cleanup after failure. Offline judge fixtures verify grading contracts, not semantic judge accuracy. Actual model ablations are still required before claiming an improved accuracy estimate.

## Isolation

Ground truth, injection and recovery commands remain outside the diagnosing prompt. Diagnosis runs with native file/shell tools disabled. Container startup disables hosthome/shared host mounts. The command validator rejects `..` traversal and restricts configuration/network-state reads; arbitrary `/proc` process files are excluded. These controls reduce leakage paths but are not a formal OS sandbox around the diagnosing SDK process.

### Local verification on 2026-10-13

All 18 offline regression checks passed, as did Ruff, Python compilation, JavaScript syntax checking and dashboard rendering checks. Both compound states were injected and restored in the real running lab, covering all four new individual faults; each final baseline passed 222/222 checks. Evidence: `results/sade/verification-20261013T041620Z.json`.

No authenticated model session or API key was available in the execution environment, so no live v3 model/judge run or accuracy ablation was performed. Semantic judge accuracy remains unvalidated; the offline negative tests validate scoring gates and judge-response handling. Historical raw reports were preserved.


## Faster benchmark batches

Both runners default to `--max-turns 20` (previously 30). Repeats still default
to 1. A turn budget is not a token or wall-clock cap; one turn may issue
multiple tools. For development, use a small representative subset:

```bash
python tools/sade_benchmark.py run --nika-root /path/to/nika --model MODEL \
  --cases core-uplink healthy-outage core-uplink-misleading compound-uplink-acl
```

The runner prints a `Checkpoint:` path before starting and atomically updates
it after each attempted trial. Resume an interrupted batch with:

```bash
python tools/sade_benchmark.py run --nika-root /path/to/nika \
  --resume results/sade/benchmark-TIMESTAMP.json
```

Resume uses the saved model, turn budget, judge, order and repeats. It skips
all recorded attempts, including failed answers, rather than retrying until
success. Changed case manifests are rejected. Environment restoration failures
stop the batch; inspect and repair the lab before starting a new batch.
A trial interrupted before its result was registered may need to run again;
verify the lab is healthy first.

Agent budget exhaustion preserves returned final text, tool trace and usage.
A valid final diagnosis can still be scored; otherwise the failure is marked
`max_turns`. Reports count `budget_exhausted` and include `by_configuration`
metrics separated by model, budget, judge, benchmark version and tool/prompt
configuration. Older aggregate metrics remain for compatibility and may mix
configurations; use `by_configuration` for comparisons. Environment restoration
is performed by the runner; it is not evidence that the agent executed a repair.
