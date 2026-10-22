# Shared topology explorer

`catalog.json` lists four teammate topology snapshots with at least 75 real devices imported from main. The two existing enterprise options remain available. Inventories below 75 real devices are excluded on import; virtual shared LAN nodes do not count toward this minimum. Only Enterprise Topology is connected to the current SADE runner; imported entries expose topology exploration and scenario names, not deployment or evaluation.

Refresh after fetching main:

```sh
python3 EnterpriseTopology/tools/import_dashboard_topologies.py --ref origin/main
```

The importer reads a Git archive without switching branches or executing contributed scripts. Each snapshot records its source directory and exact commit. Kathara collision domains with more than two interfaces render as virtual shared LAN nodes; these nodes are excluded from device and switch totals. Their spokes are labelled drawn connections rather than physical link counts. Abilene connectivity comes from its SNDlib XML; XML link IDs are identifiers, not verified runtime Linux interface names. Imported health is unavailable until a compatible runtime adapter is added.

Imported catalogs include healthy controls and optional compound cases, so catalog size is not a count of distinct fault mechanisms. Existing EnterpriseTopology health remains a historical snapshot scoped to that topology.
