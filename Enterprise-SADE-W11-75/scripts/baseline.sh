#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
echo 'Checking test hosts, routing, and service reachability' 
kathara exec -d "$LAB" pc01 -- ping -c 3 -W 2 10.20.8.20
kathara exec -d "$LAB" pc01 -- ping -c 3 -W 2 10.20.9.10
kathara exec -d "$LAB" pc01 -- ping -c 3 -W 2 198.51.100.1
kathara exec -d "$LAB" pc01 -- curl --max-time 8 -fsS http://10.20.9.11:8000/
kathara exec -d "$LAB" core1 -- vtysh -c 'show ip ospf neighbor'
kathara exec -d "$LAB" edge1 -- vtysh -c 'show ip bgp summary'
echo 'Verify DNS separately: kathara exec -d "$LAB" pc01 -- dig @10.20.9.10 web.corp.test'

