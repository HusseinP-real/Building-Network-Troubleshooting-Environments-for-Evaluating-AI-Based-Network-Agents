# P20Enterprise v2 addressing

| Device | Role | Interface | Segment | Address | OSPF area |
|---|---|---|---|---|---|
| r1 | core | eth0 | T01 | 10.255.1.1/30 | 0 |
| r1 | core | eth1 | T04 | 10.255.4.2/30 | 0 |
| r1 | core | eth2 | T05 | 10.255.5.1/30 | 0 |
| r1 | core | eth3 | T06 | 10.255.6.1/30 | 0 |
| r1 | core | eth4 | T19 | 10.255.19.1/30 | 0 |
| r2 | core | eth0 | T01 | 10.255.1.2/30 | 0 |
| r2 | core | eth1 | T02 | 10.255.2.1/30 | 0 |
| r2 | core | eth2 | T07 | 10.255.7.1/30 | 0 |
| r2 | core | eth3 | T10 | 10.255.10.1/30 | 0 |
| r3 | core | eth0 | T02 | 10.255.2.2/30 | 0 |
| r3 | core | eth1 | T03 | 10.255.3.1/30 | 0 |
| r3 | core | eth2 | T05 | 10.255.5.2/30 | 0 |
| r3 | core | eth3 | T11 | 10.255.11.1/30 | 0 |
| r3 | core | eth4 | T14 | 10.255.14.1/30 | 0 |
| r4 | core | eth0 | T03 | 10.255.3.2/30 | 0 |
| r4 | core | eth1 | T04 | 10.255.4.1/30 | 0 |
| r4 | core | eth2 | T15 | 10.255.15.1/30 | 0 |
| r4 | core | eth3 | T18 | 10.255.18.1/30 | 0 |
| r5 | abr | eth0 | T06 | 10.255.6.2/30 | 0 |
| r5 | abr | eth1 | T08 | 10.255.8.1/30 | 1 |
| r6 | abr | eth0 | T07 | 10.255.7.2/30 | 0 |
| r6 | abr | eth1 | T09 | 10.255.9.1/30 | 1 |
| r7 | abr | eth0 | T10 | 10.255.10.2/30 | 0 |
| r7 | abr | eth1 | T12 | 10.255.12.1/30 | 2 |
| r8 | abr | eth0 | T11 | 10.255.11.2/30 | 0 |
| r8 | abr | eth1 | T13 | 10.255.13.1/30 | 2 |
| r9 | abr | eth0 | T14 | 10.255.14.2/30 | 0 |
| r9 | abr | eth1 | T16 | 10.255.16.1/30 | 3 |
| r10 | abr | eth0 | T15 | 10.255.15.2/30 | 0 |
| r10 | abr | eth1 | T17 | 10.255.17.1/30 | 3 |
| r11 | abr | eth0 | T18 | 10.255.18.2/30 | 0 |
| r11 | abr | eth1 | T20 | 10.255.20.1/30 | 4 |
| r12 | abr | eth0 | T19 | 10.255.19.2/30 | 0 |
| r12 | abr | eth1 | T21 | 10.255.21.1/30 | 4 |
| r13 | site | eth0 | T08 | 10.255.8.2/30 | 1 |
| r13 | site | eth1 | T09 | 10.255.9.2/30 | 1 |
| r13 | site | eth2 | USERS1 | 10.10.1.1/24 | 1 |
| r13 | site | eth3 | SERVERS1 | 10.40.1.1/24 | 1 |
| r14 | site | eth0 | T12 | 10.255.12.2/30 | 2 |
| r14 | site | eth1 | T13 | 10.255.13.2/30 | 2 |
| r14 | site | eth2 | USERS2 | 10.10.2.1/24 | 2 |
| r14 | site | eth3 | SERVERS2 | 10.40.2.1/24 | 2 |
| r15 | site | eth0 | T16 | 10.255.16.2/30 | 3 |
| r15 | site | eth1 | T17 | 10.255.17.2/30 | 3 |
| r15 | site | eth2 | USERS3 | 10.10.3.1/24 | 3 |
| r15 | site | eth3 | SERVERS3 | 10.40.3.1/24 | 3 |
| r16 | site | eth0 | T20 | 10.255.20.2/30 | 4 |
| r16 | site | eth1 | T21 | 10.255.21.2/30 | 4 |
| r16 | site | eth2 | USERS4 | 10.10.4.1/24 | 4 |
| r16 | site | eth3 | SERVERS4 | 10.40.4.1/24 | 4 |
| pc1 | pc | eth0 | USERS1 | 10.10.1.11/24 | — |
| pc2 | pc | eth0 | USERS1 | 10.10.1.12/24 | — |
| pc3 | pc | eth0 | USERS1 | 10.10.1.13/24 | — |
| pc4 | pc | eth0 | USERS1 | 10.10.1.14/24 | — |
| server1 | server | eth0 | SERVERS1 | 10.40.1.11/24 | — |
| server2 | server | eth0 | SERVERS1 | 10.40.1.12/24 | — |
| pc5 | pc | eth0 | USERS2 | 10.10.2.11/24 | — |
| pc6 | pc | eth0 | USERS2 | 10.10.2.12/24 | — |
| pc7 | pc | eth0 | USERS2 | 10.10.2.13/24 | — |
| pc8 | pc | eth0 | USERS2 | 10.10.2.14/24 | — |
| server3 | server | eth0 | SERVERS2 | 10.40.2.11/24 | — |
| server4 | server | eth0 | SERVERS2 | 10.40.2.12/24 | — |
| pc9 | pc | eth0 | USERS3 | 10.10.3.11/24 | — |
| pc10 | pc | eth0 | USERS3 | 10.10.3.12/24 | — |
| pc11 | pc | eth0 | USERS3 | 10.10.3.13/24 | — |
| pc12 | pc | eth0 | USERS3 | 10.10.3.14/24 | — |
| server5 | server | eth0 | SERVERS3 | 10.40.3.11/24 | — |
| server6 | server | eth0 | SERVERS3 | 10.40.3.12/24 | — |
| pc13 | pc | eth0 | USERS4 | 10.10.4.11/24 | — |
| pc14 | pc | eth0 | USERS4 | 10.10.4.12/24 | — |
| pc15 | pc | eth0 | USERS4 | 10.10.4.13/24 | — |
| pc16 | pc | eth0 | USERS4 | 10.10.4.14/24 | — |
| server7 | server | eth0 | SERVERS4 | 10.40.4.11/24 | — |
| server8 | server | eth0 | SERVERS4 | 10.40.4.12/24 | — |

Routers learn remote LANs through OSPF; no static/default router routes mask withdrawals.
Hosts use .1 in their own /24 as the default gateway. 10.10.1.254 is deliberately unassigned.
The backbone is area 0. Four sites use areas 1–4. Transit networks use /30 prefixes.
R13–R16 use eth0 as primary (cost 10), eth1 as backup (cost 100), eth2 for users, and eth3 for servers.
