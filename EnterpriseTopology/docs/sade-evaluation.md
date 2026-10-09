# SADE evaluation on the 75-device lab

This integration runs the SADE symptom-aware workflow and skill library from a NIKA checkout against this standalone Kathara lab. It injects one of the three existing faults, gives SADE a user ticket and public fault ontology, compares SADE's structured diagnosis with hidden ground truth, and repairs the fault in a `finally` block. The lab is not registered as a NIKA benchmark scenario, so these are local exact-match RCA results rather than official NIKA benchmark metrics.

## Setup

From this `enterprise-topology` directory, with Docker Desktop and Kathara installed:

```bash
python3 lab.py build
python3 lab.py start
```

In a NIKA checkout, install the optional SADE SDK:

```bash
cd /path/to/nika
uv sync --extra sade
```

Use an Anthropic API key or authenticate Claude Code with `claude auth login`. Do not put credentials in this lab or its result files. To enter a key for the current shell session without echoing it or saving it in shell history, run `read -s 'ANTHROPIC_API_KEY?Anthropic API key: '` in zsh, press Enter, then run `export ANTHROPIC_API_KEY`. Do not paste the key into chat. The evaluator defaults to `claude-haiku-5-5`; use `--model MODEL_ID` on a run to compare another model, or set `SADE_MODEL` for the shell session. The model ID is saved in each result JSON.

Run the evaluator with the Python interpreter from that NIKA environment and point `--nika-root` at the checkout:

```bash
cd /path/to/SOFT3888_TU14_04/enterprise-topology
/path/to/nika/.venv/bin/python tools/sade_eval.py validate --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run core-uplink --nika-root /path/to/nika --model claude-haiku-5-5
/path/to/nika/.venv/bin/python tools/sade_eval.py run gateway-service --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run database-acl --nika-root /path/to/nika
```

Run cases one at a time. Each run requires a healthy baseline, injects its fault, waits for convergence, verifies the injection, runs SADE with read-only lab tools, scores its final diagnosis, then repairs and verifies repair. The command writes `results/sade/<UTC timestamp>/<case>.json`. That result contains the prompt, tool trace, prediction, expected ground truth, and exact comparison. `results/sade/` is ignored by Git.

The public ontology has three IDs: `interface_down`, `vrrp_service_stopped`, and `backend_acl_reject`. SADE sees a catalog of possible resources and must submit one `resource_id` and `fault_type`. The local scorer reports detection, device, resource localization, fault type, and exact `(resource_id, fault_type)` correctness. The expected pair and root-cause description are in `tools/sade_cases.json` and are never included in the agent prompt or diagnostic MCP responses.

## Run and summarize the local benchmark

### Presentation dashboard

From the `enterprise-topology` directory, start the loopback-only UI:

```bash
python3 dashboard/server.py
```

Open `http://127.0.0.1:8765`. The page opens the newest saved benchmark report automatically, so it can be demonstrated without a fresh model call. Choose another saved report from the dropdown to compare runs. The dashboard shows exact RCA, completion, five scoring axes, a per-attempt scoring matrix, diagnosis time, tool calls, and injection/repair evidence.

If `python3 lab.py start` says a device already exists, first run `python3 lab.py status` and `python3 lab.py check`; a healthy running lab does not need to be started again. If the dashboard says port 8765 is in use, open the existing page or use `python3 dashboard/server.py --port 8766` and open that port instead.

**Run benchmark** calls the existing `tools/sade_benchmark.py run` command with the chosen model and repeat count, then loads its new summary. The server uses the Python interpreter at the NIKA checkout's `.venv/bin/python` and passes that checkout as `--nika-root`. For a different checkout, start it with `--nika-root /path/to/nika`; use `--python /path/to/python` if its interpreter is elsewhere. Docker/Kathara, a healthy started lab, and model authentication are required for a live run. Keep the server in the same environment as the model credentials; the browser never receives the API key. A live run can incur model API charges.

The UI listens on `127.0.0.1` only. It reads saved `results/sade/benchmark-*.json` files and does not alter scoring or benchmark contracts. It displays the conservative rates over all attempts and labels these as local SADE results, not official NIKA scores.

Once the lab is healthy and the API key is available in the same shell, run all three cases sequentially:

```bash
/path/to/nika/.venv/bin/python tools/sade_benchmark.py run --nika-root /path/to/nika --model claude-haiku-5-5
```

Use `--repeats 3` for three passes per case after a one-pass smoke test. Every attempt gets an individual `results/sade/<timestamp>/<case>.json` with the prediction and ground truth. The command prints each case's status, exact RCA score, and repair status, then writes `results/sade/benchmark-<timestamp>.json`. If repair verification fails, it stops before injecting another fault.

For existing saved runs, with no API request or fault injection:

```bash
python3 tools/sade_benchmark.py report results/sade/benchmark-complete-20261008.json
python3 tools/sade_benchmark.py summarize
python3 tools/sade_benchmark.py summarize --out results/sade/history-summary.json
```

`report` prints a previously saved aggregate JSON as a readable terminal report. `summarize` calculates a new report from individual runs and prints the same format. The summary includes attempts, scored runs, complete runs (injection, scoring, and repair verified), errors, each scoring axis, per-case exact RCA counts, and a run list with paths, tool calls, token usage, timing, and status. Each metric reports both the conservative rate over all attempts (failed attempts count as incorrect) and the rate over scored runs. With no paths supplied, `summarize` includes every saved individual run, including exploratory runs; pass specific result paths to reproduce one benchmark pass. Treat a small number of runs as a functional demonstration, not a statistically stable agent accuracy estimate. These are local enterprise-topology results, not official NIKA benchmark scores.

If an older parser rejected an otherwise complete diagnosis because it omitted only the optional closing `=== END ===` marker, use `python3 tools/sade_benchmark.py rescore <result.json>` to rescore that saved text. The corrected file retains the original parser error in `parser_correction` for auditability. Then run `summarize` again to refresh the aggregate.

For a saved SADE final message, score without injecting a fault:

```bash
/path/to/nika/.venv/bin/python tools/sade_eval.py score core-uplink answer.txt
```

If a run reports `repair_verified: false`, inspect and repair the lab before starting another case. Verify healthy recovery with `python3 lab.py check`.

## Interpreting the cases

The core uplink and gateway service cases retain application reachability through redundancy. SADE must inspect routing and VRRP state after an initially healthy user traffic map. The database ACL case changes an allowed application-to-backend HTTP path and is visible in the first reachability check. The diagnostic MCP exposes only read-only commands and known-allowed traffic paths, so intentional guest and database policy denials are not counted as faults.

## Verification performed

On 2026-10-08, the MCP server was exercised through a real stdio client. All five known-allowed baseline flows returned HTTP 200. Each of the three faults was injected into the running 75-device lab, detected by the diagnostic tools, repaired, and verified. A one-pass SADE benchmark using `claude-haiku-5-5` scored all three cases, with exact RCA correct in 3/3 complete runs. Injection and repair were verified for every run, and the final full lab check passed 222/222 assertions. The aggregate report is `results/sade/benchmark-complete-20261008.json` (local and ignored by Git). Three observations demonstrate that the workflow runs end to end; they do not establish a stable accuracy estimate.
