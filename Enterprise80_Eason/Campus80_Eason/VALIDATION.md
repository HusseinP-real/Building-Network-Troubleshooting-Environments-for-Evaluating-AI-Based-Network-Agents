# Validation Record

Documentation edition: 2026-10-23 (Australia/Sydney).

## Historical runtime evidence supplied in the archive

The uploaded archive contains the following successful checks. Times below are UTC, as recorded by the controller. These records were inspected for this documentation update; the live experiment was not rerun.

| Stage | Log file | Recorded completion (UTC) |
|---|---|---|
| Healthy baseline | `logs/20261021T105927.754044Z.log` | 2026-10-21 11:00:44 |
| Baseline before injection | `logs/20261021T110058.224182Z.log` | 2026-10-21 11:02:14 |
| Injection followed by expected fault checks | `logs/20261021T110058.224182Z.log` | 2026-10-21 11:03:22 |
| Separate fault verification | `logs/20261021T110332.132066Z.log` | 2026-10-21 11:03:58 |
| Recovery, healthy checks, and watchdog restored | `logs/20261021T110919.238343Z.log` | 2026-10-21 11:10:45 |
| Subsequent healthy verification | `logs/20261021T111100.250691Z.log` | 2026-10-21 11:12:16 |

These correspond to the evening of 2026-10-21 in Sydney (UTC+11). The injection log includes temporary adjacency mismatches during convergence before the fault checks pass. The recovery log similarly records incomplete adjacencies before successful convergence. These intermediate retry messages do not negate the final successful checks.

The historical records support the implemented checks for the supplied runtime. They do not establish universal behaviour across all FRR versions or host environments.

## Scope of the implemented checks

- Static inventory, interface, addressing, and OSPF network consistency.
- Connectivity of the remaining eleven-router backbone graph without r01.
- Healthy state: all 80 device addresses and administrative interface states; all twelve routers' expected FULL peers, ospfd/zebra processes, and IPv4 forwarding; 68 endpoint probes; r12's exact route to LAN01.
- Fault state: r01 interfaces preserved, ospfd/watchfrr absent, zebra present; remaining routers' expected peers and absence of the exact LAN01 route; affected-host, same-LAN, reverse-direction, and other-LAN probes.
- Recovery: FRR restart, healthy checks, and watchdog presence.

## Documentation-edition checks

- All retained text files scanned for Chinese characters; none remain.
- README and this validation record rewritten in English.
- PNG and SVG topology diagrams generated from the supplied manifest, with backbone attachments cross-checked against lab.conf.
- Executable code, startup scripts, network configurations, JSON metadata, scenario text, tests, and historical logs compared byte-for-byte with the uploaded archive and preserved.
- Only documentation was replaced and diagram assets added. Packaging excludes macOS metadata, empty R history, and generated Python bytecode caches.
- ZIP integrity and README local links checked.

## Limits

No live process was stopped or restarted during the documentation update. No HTTP/application verification, all-pairs connectivity sweep, performance benchmark, or external evaluation-runner integration is claimed. The original package's validation text predated the additional successful fault/recovery logs; this record supersedes that outdated status using the supplied evidence.
