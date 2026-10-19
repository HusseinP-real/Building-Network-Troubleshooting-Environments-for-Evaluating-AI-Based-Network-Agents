# Validation Notes

Validation date: 2026-10-19 (Australia/Sydney).

- Devices: 75 (10 routers, 25 switches, 40 endpoints).
- Links: 108 (21 routed, 47 trunk, 40 access), with 216 unique interfaces.
- Structural validation: all ports match the device inventory, all 75 nodes belong to one connected graph, and all 40 planned endpoint IP addresses are unique.
- All 75 startup scripts passed `bash -n`; Python source files passed AST syntax checks.
- `python3 lab.py validate` returned exit code 0. Kathara confirmed that `lab.conf file is correct`.
- The diagram reads every device and link from the same inventory. Its PNG rendering was visually inspected. The README embeds the image through a relative path and includes an SVG link for scalable viewing.

See [structural-validation.json](../results/structural-validation.json) for structural validation details.

## Runtime Validation

Images have not been built and the 75 devices have not been started for this standalone directory. OSPF, VRRP, STP, DHCP, and service behavior have therefore not been verified at runtime for this version.

Follow the README to build and start the lab, then run `python3 lab.py check` and `python3 tools/verify_faults.py`. Runtime results are written to this directory's `results` folder.

Historical reports from the adjacent original lab were not copied as evidence for this version.
