# Client Demo Runbook

## Goal

Demonstrate a reproducible topology extension, a controlled IS-IS configuration fault, observable network impact, and recovery.

## Demo Sequence

### A. Show the extension

Explain:

- Original NIKA Abilene: 12 routers + 12 hosts.
- Extension adds `yumang` + `pc_yumang`.
- `YUMAng` is synthetic and added for benchmark evaluation.
- NIKA regenerates addresses, FRR configuration, edge host and Kathara containers from the source topology.

Command:

```bash
uv run nika session containers --session_id <SESSION_ID>
```

Point out:
- `yumang`
- `pc_yumang`

### B. Healthy state

```bash
./scripts/02_verify_healthy.sh <SESSION_ID>
```

Highlight:
- `yumang eth0 = 10.0.0.31/31`
- `yumang eth1 = 10.254.0.49/30`
- `pc_yumang = 10.254.0.50/30`
- YUMAng ↔ SNVAng IS-IS neighbour = `Up`
- old ↔ new end-to-end pings succeed

Suggested narration:

> The topology is extended at the source level rather than by manually modifying a running container. The new site participates in the same IS-IS Level-2 domain and is reachable end-to-end.

### C. Inject the fault

```bash
./scripts/03_inject_and_verify_fault.sh <SESSION_ID>
```

Explain the fault:

> We remove IS-IS from YUMAng's backbone interface while leaving the physical interface up. This models a routing configuration error rather than a physical link failure.

Highlight:
- adjacency disappears / is no longer stable
- remote IS-IS routes disappear
- remote ping fails
- PC-to-PC communication fails

### D. Ground truth

Show `docs/ground_truth.json`.

Important distinction:
- User ticket = what the user/operator reports.
- Ground truth = the actual hidden fault and expected network state.

### E. User-report variants

Show `docs/user_tickets.json`.

Explain that the same underlying fault can be paired with:
- general user report
- NOC engineer report
- incomplete report
- partially misleading report

This supports evaluating an AI network agent under different report quality/expertise.

### F. Recovery

```bash
./scripts/04_recover_and_verify.sh <SESSION_ID>
```

Highlight the staged recovery:
1. adjacency restores
2. routes reconverge
3. forwarding restores

Suggested narration:

> We do not consider the fault recovered merely because the neighbour state is Up. The recovery script also waits for the routing table to reconverge and verifies end-to-end reachability.

## Questions You Should Be Ready For

**Why add a synthetic node to Abilene?**

The purpose is not to recreate historical Abilene exactly. We use a known NIKA topology as a reproducible baseline and extend it to create benchmark scenarios.

**Why this fault?**

It is deterministic, reproducible and isolates a control-plane configuration error. The interface remains physically up, making the diagnosis less trivial than a simple link-down fault.

**What makes this useful for AI-agent evaluation?**

The scenario provides:
- reproducible environment
- known ground truth
- observable symptoms
- multiple ticket/report variants
- objective detection/localisation/root-cause targets
- recovery validation

**What would come next?**

Scale the same pipeline to:
- additional sites/topologies
- more routing protocols
- more fault types
- multiple user-report variants
- repeated runs
- agent scoring for detection, localisation and root-cause accuracy
