# Alternative-agent comparison: archived evidence

Archived original dataset only. Not a new evaluation of Kath5_Jiayuan_75Devices or NIKA_Clos_Jiayuan_92Devices.

This reproduction calls no models. Group by experiment arm; do not pool persona rewrites into a new topology score.

| Arm | Agent | Runs / scored | Outcome | Agent cost/run USD | Lifecycle seconds/run |
|---|---|---|---|---|---|
| base80 | cc-baseline | 240 / 236 | 0.942 | 0.2627 | 327.3 |
| base80 | react-full | 240 / 237 | 0.941 | 0.0991 | 292.9 |
| base80 | sade | 240 / 230 | 0.912 | 0.3709 | 411.4 |
| cex120 | cc-baseline | 360 / 342 | 0.919 | 0.3658 | 375.7 |
| cex120 | react-full | 360 / 351 | 0.865 | 0.1110 | 283.6 |
| cex120 | sade | 360 / 354 | 0.818 | 0.4104 | 426.6 |

Archived wall_seconds includes lifecycle work; not isolated model investigation time.
Archived agent cost: SDK-reported Claude cost and pricing-derived GPT estimates; excludes judge billing.

The new SOFT3888 pipeline separately times agent investigation and lifecycle. Run both SADE and react-full on the same soft3888_evaluation.csv (8 faults +2 no-fault controls), with identical repeats/tools, before making new accuracy, speed or cost claims. Missing credentials block those new experiments.
