# Sarah Enterprise Service Network

## Overview
This Kathara topology contains seven devices and demonstrates DNS and DHCP service failures for evaluating AI-based network troubleshooting agents.

## Network Devices
| Device | Role | IP Address |
|---|---|---|
| pc1 | Client | 10.20.1.10 |
| pc2 | DHCP Client | Dynamic (10.20.1.100-150) |
| r1 | Router | 10.20.1.1, 10.20.2.1, 10.20.12.1 |
| r2 | Router | 10.20.12.2, 10.20.3.1 |
| dhcp | DHCP Server | 10.20.2.10, 10.20.1.2 |
| dns | DNS Server | 10.20.3.10 |
| app | Application Host | 10.20.3.20 |

## Network Subnets
- CLIENT_LAN: 10.20.1.0/24
- DHCP_LAN: 10.20.2.0/24
- BACKBONE: 10.20.12.0/30
- SERVICE_LAN: 10.20.3.0/24

## Starting the Network
Run from this directory:

    python3 -m kathara lstart

DNS and DHCP services start automatically.

## DNS Validation
Run:

    python3 -m kathara exec pc1 -- nslookup -type=A app.sarah.test 10.20.3.10

Expected result: 10.20.3.20

## DHCP Validation
Run:

    python3 -m kathara exec pc2 -- sh -c "dhclient -r eth0 2>/dev/null; ip addr flush dev eth0; timeout 30 dhclient -1 -v eth0"

Expected result: PC2 receives an address in 10.20.1.100-150.

## Fault Scenario 1: SARAH-SVC-001
Fault: DNS Service Down

Injection:

    python3 -m kathara exec dns -- sh -c 'kill "$(cat /tmp/sarah-dnsmasq.pid)"'

Expected result: DNS resolution fails.

Recovery:

    python3 -m kathara exec dns -- dnsmasq --conf-file=/etc/sarah-dnsmasq.conf --pid-file=/tmp/sarah-dnsmasq.pid

## Fault Scenario 2: SARAH-SVC-002
Fault: DHCP Service Down

Injection:

    python3 -m kathara exec dhcp -- sh -c 'kill "$(cat /tmp/sarah-dhcp.pid)"'

Expected result: New DHCP address requests fail.

Recovery:

    python3 -m kathara exec dhcp -- dnsmasq --conf-file=/etc/sarah-dhcp.conf --pid-file=/tmp/sarah-dhcp.pid

Re-run the DHCP validation command to confirm recovery.

## Ground Truth
- ground_truth/SARAH-SVC-001.json
- ground_truth/SARAH-SVC-002.json

## Validation Results
| Test | Result |
|---|---|
| Network deployment | PASS |
| DNS resolution | PASS |
| DHCP address assignment | PASS |
| DNS fault injection and recovery | PASS |
| DHCP fault injection and recovery | PASS |
| Automatic DNS/DHCP startup | PASS |

## Limitations
This is a seven-device prototype. It does not independently meet the overall project target of 75-100 devices.
