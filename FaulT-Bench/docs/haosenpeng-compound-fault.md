# haosenpeng Compound Fault: Wrong Gateway and ICMP Filtering

Scenario: [`kath3-laptop0-wrong-gateway-and-icmp-drop`](../dataset/kath3_Q/custom/kath3-laptop0-wrong-gateway-and-icmp-drop.txt).

## Scenario Author and Troubleshooting Agent Responsibilities

The scenario author writes both the trouble ticket in `[PROMPT-TO-AGENT]`
and the deterministic injection commands in `[INJECTION]`. The harness
executes those commands. The troubleshooting agent receives the ticket and
a topology overview, then uses diagnostic tools to investigate. It does not
translate the author's fault description into injection commands or receive
the reference diagnosis. `[GROUND-TRUTH]`, `[FIX]`, and `[SCORING-AXES]`
provide the reference material for scoring the diagnosis.

## Fault Composition

1. Change Laptop0's default gateway in Kath3 from `172.16.20.1` to the
   unassigned address `172.16.20.99`.
2. Add an ICMP DROP rule to the same host's iptables `OUTPUT` chain,
   targeting `192.168.100.1`.

The first component comes from `kath3-laptop0-wrong-gateway`. The second
adapts the filtering mechanism in `simple-bgp-router2-iptables-icmp-drop`
to a host's `OUTPUT` chain and a single destination. The original BGP
scenario uses a router's `FORWARD` chain. Both components affect one device,
so the compound fault works with the existing single-device injection format.

| Stage | Laptop0 to gateway .1 | Laptop0 to PC4 | Laptop0 to 192.168.100.1 | PC4 to 192.168.100.1 |
|---|---|---|---|---|
| Healthy baseline | Reachable | Reachable | Reachable | Reachable |
| Both faults injected | Reachable | Unreachable | Unreachable | Reachable |
| Gateway repaired only | Reachable | Reachable | Unreachable | Reachable |
| Filter removed only | Reachable | Unreachable | Unreachable | Reachable |
| Both faults repaired | Reachable | Reachable | Reachable | Reachable |

During the gateway-only repair stage, the filter's packet counter should
increase. This demonstrates that the second fault actually drops traffic.
The ticket does not reveal the root causes; scoring requires identifying
both problems.

## Run the Live Network Validation

Start Docker and install Python 3.12+ and the Kathara CLI. Run these commands
from `FaulT-Bench/`:

```bash
python3 tools/validate_haosenpeng_fault.py --check-only
python3 tools/validate_haosenpeng_fault.py
```

SADE, the Python Kathara API, and LLM API keys are not required. The second
command performs the following steps:

1. Copy the complete Kath3 topology into a unique temporary directory and
   start an isolated lab without hosthome/shared mounts.
2. Wait for the healthy baseline configuration and connectivity checks to
   pass. Do not inject faults if the baseline fails.
3. Use the repository's `parse_scenario` to read the scenario, execute its
   injection commands, and run its six post-injection checks.
4. Repeat the injection to verify that the tagged rule is not duplicated.
5. Verify both partial repairs, the DROP counter, and both complete repair
   orders.
6. Attempt to clean up only this temporary lab on either success or failure,
   and write the evidence to a JSON report.

The default output is `faultbench/runs/haosenpeng-validation.json`
(gitignored). Use `--output /path/to/report.json` to choose another location.
Deployment errors are retained in the report. The temporary topology
configuration remains at the report's `temporary_lab` path for inspection.
If cleanup fails, run `kathara lclean -d /path/to/temporary/Kath3` against
that specific temporary directory.

This validator exercises a live container network and does not run an LLM
agent benchmark or produce agent scores. It requires actual device command
exit codes and ping packet-loss output. Missing output, timeouts, and
unknown expectations do not automatically pass.

## Manual Injection and Troubleshooting

For a step-by-step experiment, first confirm that nobody else is using the
lab associated with `topology_kathara/Kath3/`. From that directory, run
`kathara lstart --noterminals`, then execute the commands below. Verify the
healthy baseline row in the table before every injection.

```bash
kathara exec laptop0 -- ip route show default
kathara exec laptop0 -- ping -W2 -c2 172.16.20.1
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara exec pc4 -- ping -W2 -c2 192.168.100.1
```

Run `kathara connect laptop0` and paste the scenario's `[INJECTION]` `cmd`
contents into the device shell. Use `exit` to return to the host terminal.

```bash
kathara exec laptop0 -- ip route show default
kathara exec laptop0 -- ip neigh show
kathara exec laptop0 -- iptables -S OUTPUT
kathara exec laptop0 -- iptables -L OUTPUT -n -v -x
```

Repair the gateway first, then repeat both off-subnet pings. One destination
should become reachable while the other remains blocked:

```bash
kathara exec laptop0 -- ip route replace default via 172.16.20.1
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara exec laptop0 -- iptables -L OUTPUT -n -v -x
```

Remove the specific experimental rule and repeat the probes. Preserve all
other firewall rules:

```bash
kathara exec laptop0 -- iptables -D OUTPUT -d 192.168.100.1/32 -p icmp -m comment --comment haosenpeng-compound-icmp -j DROP
kathara exec laptop0 -- ping -W2 -c2 172.16.10.4
kathara exec laptop0 -- ping -W2 -c2 192.168.100.1
kathara lclean
```

## Run the Agent Benchmark

The custom scenario lives in `dataset/kath3_Q/custom/`, separately from the
paper's original 560 scenarios, preserving the definition of `base80.csv`.
The current `resolve_scenario` searches this directory, but
`list --scope base` and `sweep --scope base` do not include it. Use the
scenario ID or the dedicated manifest.

After setting up the SADE environment and API keys described in the main
README, run the following commands from `faultbench/`:

```bash
./fb.sh bench --manifest benchmarks/haosenpeng.csv --agents cc-baseline --dry-run
./fb.sh bench --manifest benchmarks/haosenpeng.csv --agents cc-baseline --runs-root runs/haosenpeng_p1
```

The benchmark deploys the network, injects and checks the fault, runs the
agent, scores its diagnosis, and cleans up. It registers the lab name through
the Python API; the temporary manual experiments use the CLI. Finish manual
experiments before running the benchmark because the existing harness's
container-counting and cleanup helpers assume one network at a time. The
full benchmark requires the external agent environment; the live validation
script does not.

## Validation Evidence

[`validation/haosenpeng-compound-fault.json`](validation/haosenpeng-compound-fault.json)
records scenario and topology SHA-256 hashes, software versions, raw command
outputs for each stage, device exit codes, check results, rule counters, and
cleanup results. Its `kind` is explicitly
`live-network-validation-without-llm`.

One local rerun also encountered a Kath3 baseline failure before injection:
router1's `ripd` process was running, but `show ip rip` returned
`RIP instance not found`, leaving router0 without remote routes. The validator
refused to inject after the baseline timeout and cleaned up that lab. The
failure report was retained locally at
`faultbench/runs/haosenpeng-baseline-rejected.json`. Such deployment or
initialization failures must not count as successful fault injection. If this
occurs, inspect the RIP processes, running configuration, and routing tables;
clean up the corresponding temporary lab and rerun. Do not bypass the
baseline checks.
