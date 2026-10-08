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

Use an Anthropic API key or authenticate Claude Code with `claude auth login`. Do not put credentials in this lab or its result files. Run the evaluator with the Python interpreter from that NIKA environment and point `--nika-root` at the checkout:

```bash
cd /path/to/SOFT3888_TU14_04/enterprise-topology
export ANTHROPIC_API_KEY=... # omit if Claude Code is already logged in
/path/to/nika/.venv/bin/python tools/sade_eval.py validate --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run core-uplink --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run gateway-service --nika-root /path/to/nika
/path/to/nika/.venv/bin/python tools/sade_eval.py run database-acl --nika-root /path/to/nika
```

Run cases one at a time. Each run requires a healthy baseline, injects its fault, waits for convergence, verifies the injection, runs SADE with read-only lab tools, scores its final diagnosis, then repairs and verifies repair. The command writes `results/sade/<UTC timestamp>/<case>.json`. That result contains the prompt, tool trace, prediction, expected ground truth, and exact comparison. `results/sade/` is ignored by Git.

The public ontology has three IDs: `interface_down`, `vrrp_service_stopped`, and `backend_acl_reject`. SADE sees a catalog of possible resources and must submit one `resource_id` and `fault_type`. The local scorer reports detection, device, resource localization, fault type, and exact `(resource_id, fault_type)` correctness. The expected pair and root-cause description are in `tools/sade_cases.json` and are never included in the agent prompt or diagnostic MCP responses.

For a saved SADE final message, score without injecting a fault:

```bash
/path/to/nika/.venv/bin/python tools/sade_eval.py score core-uplink answer.txt
```

If a run reports `repair_verified: false`, inspect and repair the lab before starting another case. Verify healthy recovery with `python3 lab.py check`.

## Interpreting the cases

The core uplink and gateway service cases retain application reachability through redundancy. SADE must inspect routing and VRRP state after an initially healthy user traffic map. The database ACL case changes an allowed application-to-backend HTTP path and is visible in the first reachability check. The diagnostic MCP exposes only read-only commands and known-allowed traffic paths, so intentional guest and database policy denials are not counted as faults.

## Verification performed

On 2026-10-08, the MCP server was exercised through a real stdio client. All five known-allowed baseline flows returned HTTP 200. Each of the three faults was injected into the running 75-device lab, detected by the diagnostic tools, repaired, and verified. The final full lab check passed 222/222 assertions. The model diagnosis itself has not been run here because the local Claude Code session is not authenticated and no `ANTHROPIC_API_KEY` is configured.
