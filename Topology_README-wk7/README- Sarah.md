# Kathará Fault Demo

## Overview

This directory contains a Kathará-based network troubleshooting environment developed as part of the SOFT3888 project. The prototype provides a reproducible network topology where controlled network faults can be injected, observed, diagnosed, and recovered.

The initial topology was extended to include multiple hosts, routers, subnets, and a server. The environment is used to develop troubleshooting scenarios that can later be used for evaluating AI-based network troubleshooting agents.

## Network Topology

The current topology contains six devices:

- PC1
- PC2
- PC3
- R1
- R2
- Server1

The network is divided into multiple subnets. R1 and R2 provide connectivity between the different networks, while Server1 is located on the server subnet connected through R2.

## Devices and IP Addresses

| Device | IP Address | Description |
|--------|------------|-------------|
| PC1 | 10.0.0.2/24   | Client host |
| R1 | 10.0.0.1/24    | Gateway for PC1 network |
| R2 | 30.0.0.2/24    | Router connecting internal and server networks |
| PC2 | 20.0.0.2/24   | Internal host |
| PC3 | 20.0.0.3/24   | Internal host |
| Server1 | 40.0.0.2/24 | Server on the server subnet |

## Running the Network

Start Docker Desktop before running the Kathará environment.

From the `kathara-fault-demo` directory:

```bash
python3 -m kathara lstart