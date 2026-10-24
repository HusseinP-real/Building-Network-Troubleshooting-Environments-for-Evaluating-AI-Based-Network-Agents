# Sarah Enterprise Network

This six-device Kathará lab connects three PCs, two routers and one server. Its supplied scenario changes pc1's default gateway from `10.10.1.1` to `10.10.1.99`.

See [lab.conf](lab.conf) for interface bindings and [SARAH-ENT-001.json](ground_truth/SARAH-ENT-001.json) for the ticket, injection, recovery and supplied validation record. The recorded healthy → fault → recovery results were contributed with the topology; this integration did not rerun them.

From this directory, start the native lab with `kathara lstart -d . --noterminals`. Inspect or stop only this lab using Kathará's `-d .` option. Native execution requires Docker, Kathará and the images specified in `lab.conf`.

The shared Dashboard requires at least 75 real devices. This lab remains a standalone package and is excluded from its selector. No Dashboard runtime or automatic SADE adapter is enabled.
