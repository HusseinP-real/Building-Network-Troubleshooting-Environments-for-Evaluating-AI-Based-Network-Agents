# Delivery scope and evidence boundaries

This delivery adds two topology definitions, their scenario files and shared
benchmark tooling. The active Ground Truth catalog covers these two labs only:
eight core faults, one compound case and two healthy controls.

Existing team topology configurations, datasets and unrelated documents are
outside this delivery. The original four delivery directories retain the integrity-checked file
contents and Git file modes.

Recorded cloud baseline, fault, recovery and regression evidence is retained
unchanged. Older aggregate report counts describe their recorded context;
they are not a current audit of the entire team checkout. No new network or
model evaluation was executed during Windows file transfer or catalog cleanup.

The 75-device source contains existing Markdown hard-break spaces and a few
blank-line formatting warnings in FRR files. These are preserved to retain
configuration and evidence hash identity. Check new supporting code separately.

Regenerate the active catalog in the prepared environment:

```sh
python tools/build_ground_truth_catalog.py --topology Kath5_Jiayuan_75Devices --topology NIKA_Clos_Jiayuan_92Devices
```
