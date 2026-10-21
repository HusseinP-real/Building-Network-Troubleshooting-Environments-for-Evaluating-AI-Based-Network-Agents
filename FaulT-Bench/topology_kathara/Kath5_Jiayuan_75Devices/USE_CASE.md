# 75-device use cases

These replace the copied 50-device use cases. Expected behavior below is a
specification; executed results are the hash-linked JSON validation reports.

| ID | Actor and goal | Representative path | Acceptance |
|---|---|---|---|
| UC1 | Branch user accesses Internal Application | a1/g1 → intapp1 | Correct DNS answer and HTTP 200/content |
| UC2 | Internal host accesses remote branch | intapp1 → a1 | Ping succeeds in both directions |
| UC3 | User accesses DMZ services | a1 → dmzdns1/dmzweb1 | Correct DNS answer; HTTP 200 |
| UC4 | Branch F remains reachable | a1 ↔ f1 | Healthy OSPF routes and traffic |
| UC5 | Branch G survives one upstream link outage | g1 ↔ a1 via r16 | Traffic recovers over remaining path; both links restored |
| UC6 | Operator receives network events | r20 → mgmt2; mgmt1 reads /events | Tagged syslog event received and returned |
| UC7 | Management access respects its boundary | mgmt1 vs a1 → mgmt2:9100 | Management allowed; ordinary branch refused |
| UC8 | Operator checks service health | mgmt3 active probes | DNS and both service-zone HTTP checks succeed |
| UC9 | Agent diagnoses controlled faults | Four custom scenarios | Fault is verified before agent; proposed fix matches evidence |

UC5 requires explicit failover evidence beyond ordinary baseline ping checks.
UC9's live-agent evaluation requires credentials and is separate from the
no-LLM validator. See `../../docs/soft3888-development.md`.
