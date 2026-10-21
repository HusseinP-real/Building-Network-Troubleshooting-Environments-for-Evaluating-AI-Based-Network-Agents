# 75-device acceptance test cases

Do not interpret this specification as a PASS report. Actual results are
recorded under `docs/validation/soft3888/` with exact configuration hashes.

| Test | Procedure | Expected result |
|---|---|---|
| TC1 | Fresh API deployment | 75 running devices; 43 declared collision domains |
| TC2 | Branch A/F/G cross-zone traffic | Bidirectional representative pings |
| TC3 | Internal ↔ OSPF-side traffic | Requests and return paths succeed |
| TC4 | UDP and TCP Internal DNS, multiple zones | app.internal.test → 192.168.251.12 |
| TC5 | Internal HTTP and page content | HTTP 200 and SOFT3888 Internal Application marker |
| TC6 | DMZ DNS and HTTP | Existing records and web response remain working |
| TC7 | Management positive/negative access | mgmt1 allowed; a1 refused on TCP 9100 |
| TC8 | Syslog delivery and active health probes | r20 event visible; mgmt3 probes succeed |
| TC9 | R15 OSPF advertisement fault | Branch F remote failure; local gateway and other branch healthy |
| TC10 | R21 EIGRP AS mismatch | AS101 vs AS100, missing neighbor; local LAN and DMZ healthy |
| TC11 | Wrong application DNS record | Wrong A record; direct-IP HTTP and other DNS record healthy |
| TC12 | Application process stopped | DNS/ping work; HTTP refused; DMZ works |
| TC13 | Repeat each injection | Same controlled fault; no accumulated firewall rules/processes |
| TC14 | Repair each fault | Explicit recovery checks and whole baseline pass |
| TC15 | Fresh redeployment | All normal services return without manual device configuration |
| TC16 | Branch G individual uplink failure/recovery | Alternate path works; restored topology passes baseline |

Run the independent validator twice for fresh-deployment repeatability.
The four fault definitions live under `dataset/jiayuan75_Q/custom/`; their
machine-readable pre/fault/recovery checks are the executable specification.
The original 50-device historical results remain in the Extended directory.
