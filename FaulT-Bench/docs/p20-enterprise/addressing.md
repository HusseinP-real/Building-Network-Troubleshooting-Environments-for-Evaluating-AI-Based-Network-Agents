# P20Enterprise interface addresses

| Device | Interface | Segment | IPv4 address |
|---|---|---|---|
| r1 | eth0 | HQ | 10.10.10.1/24 |
| r1 | eth1 | TRANSIT12 | 10.255.12.1/30 |
| r2 | eth0 | TRANSIT12 | 10.255.12.2/30 |
| r2 | eth1 | TRANSIT23 | 10.255.23.1/30 |
| r2 | eth2 | SERVER_A | 10.30.30.1/24 |
| r3 | eth0 | TRANSIT23 | 10.255.23.2/30 |
| r3 | eth1 | BRANCH | 10.20.20.1/24 |
| r3 | eth2 | SERVER_B | 10.40.40.1/24 |
| pc1 | eth0 | HQ | 10.10.10.11/24 |
| pc2 | eth0 | HQ | 10.10.10.12/24 |
| pc3 | eth0 | BRANCH | 10.20.20.11/24 |
| pc4 | eth0 | BRANCH | 10.20.20.12/24 |
| server1 | eth0 | SERVER_A | 10.30.30.10/24 |
| server2 | eth0 | SERVER_B | 10.40.40.10/24 |

## Static routes

| Device | Destination | Next hop |
|---|---|---|
| r1 | 10.20.20.0/24 | 10.255.12.2 |
| r1 | 10.30.30.0/24 | 10.255.12.2 |
| r1 | 10.40.40.0/24 | 10.255.12.2 |
| r1 | 10.255.23.0/30 | 10.255.12.2 |
| r2 | 10.10.10.0/24 | 10.255.12.1 |
| r2 | 10.20.20.0/24 | 10.255.23.2 |
| r2 | 10.40.40.0/24 | 10.255.23.2 |
| r3 | 10.10.10.0/24 | 10.255.23.1 |
| r3 | 10.30.30.0/24 | 10.255.23.1 |
| r3 | 10.255.12.0/30 | 10.255.23.1 |
| pc1 | default | 10.10.10.1 |
| pc2 | default | 10.10.10.1 |
| pc3 | default | 10.20.20.1 |
| pc4 | default | 10.20.20.1 |
| server1 | default | 10.30.30.1 |
| server2 | default | 10.40.40.1 |
