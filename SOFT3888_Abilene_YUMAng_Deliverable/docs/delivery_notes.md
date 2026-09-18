# Delivery Notes

## Already demonstrated

- Original Abilene healthy baseline.
- Source-level topology extension.
- New YUMAng router and pc_yumang host.
- Healthy IS-IS adjacency and end-to-end communication.
- Controlled IS-IS interface fault.
- Route withdrawal and connectivity loss.
- IS-IS adjacency and routing-table recovery observed during diagnosis.

## Final evidence still recommended

Run:

```bash
./scripts/04_recover_and_verify.sh <SESSION_ID>
```

Then copy the generated:

`04_recovery_final.txt`

into:

`evidence/04_recovery_final.txt`

This produces a clean final artifact where recovery is declared only after both adjacency and routing state converge.

## Repository hygiene before handoff

Recommended:

```bash
git status
git diff -- src/nika/net_env/isp/sndlib/abilene/network.xml
```

Commit only the intended topology extension and delivery scripts/docs. Do not commit local session IDs, Docker/Kathara runtime state, `.nika_cache`, or environment-specific files unless required by the team.
