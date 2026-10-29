# Shared topology explorer

`catalog.json` lists eleven imported topology snapshots with at least 75 real devices. Ten come from main; Jennie Enterprise comes from the pinned `JENNIE_REF` in the importer and is labelled candidate because it has not been merged or runtime-validated. The two existing enterprise options remain available, giving thirteen displayed topologies. The four newly added maps are P20Enterprise, Sarah Enterprise 75, Sarah Service 75 and Jennie Enterprise 75. All thirteen options now expose four generic endpoint faults plus a healthy control. Each topology/fault must pass its live validation cycle before automatic evaluation is enabled. The generic evaluator, diagnostic tools and recovery journal are scoped to the selected lab. See [the generic benchmark guide](../../docs/generic-fault-benchmark.md) for mappings, prerequisites and current validation coverage. Imported source-native fault catalogs remain archived in inventories; they are not the default UI list. Inventories below 75 real devices remain excluded.

Refresh after fetching main:

```sh
python3 EnterpriseTopology/tools/import_dashboard_topologies.py --ref origin/main
```

The importer reads a Git archive without switching branches or executing contributed scripts. Each snapshot records its source directory and exact commit. Kathara collision domains with more than two interfaces render as virtual shared LAN nodes; these nodes are excluded from device and switch totals. Their spokes are labelled drawn connections rather than physical link counts. Abilene connectivity comes from its SNDlib XML; XML link IDs are identifiers, not verified runtime Linux interface names. Saved imported health is unavailable; use a live baseline through an adapted manual control to check the selected environment.

Imported catalogs include healthy controls and optional compound cases, so catalog size is not a count of distinct fault mechanisms. Existing EnterpriseTopology health remains a historical snapshot scoped to that topology.
