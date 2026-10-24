#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Injecting SARAH-SVC-002: DHCP Service Down"

python3 -m kathara exec dhcp -- sh -c 'kill "$(cat /tmp/sarah-dhcp.pid)"'

echo "DHCP fault injection completed."
