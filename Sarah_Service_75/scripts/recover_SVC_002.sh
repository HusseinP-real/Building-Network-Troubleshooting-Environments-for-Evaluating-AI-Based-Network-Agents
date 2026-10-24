#!/bin/bash
set -e
cd "$(dirname "$0")/.."

echo "Recovering SARAH-SVC-002: DHCP Service Down"

python3 -m kathara exec dhcp -- dnsmasq \
  --conf-file=/etc/sarah-dhcp.conf \
  --pid-file=/tmp/sarah-dhcp.pid

echo "DHCP recovery command completed."
