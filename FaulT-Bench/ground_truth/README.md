# Ground Truth for the two delivered topologies

The active catalog contains 11 scenarios: eight core faults, one compound case
and two healthy controls. It covers only Kath5_Jiayuan_75Devices and
NIKA_Clos_Jiayuan_92Devices. Existing team datasets remain unchanged.

Scenario labels, source hashes and recorded evidence are retained. Catalog
filtering and directory integrity checks are not new network or model tests.
These evaluator records must never be included in agent input.

Regenerate in the prepared Linux environment:

```sh
python tools/build_ground_truth_catalog.py --topology Kath5_Jiayuan_75Devices --topology NIKA_Clos_Jiayuan_92Devices
```
