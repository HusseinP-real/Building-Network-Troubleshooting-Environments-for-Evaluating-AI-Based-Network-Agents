#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Recovering SARAH-SVC-001: DNS Service Down"

python3 -m kathara exec dns -- dnsmasq \
  --conf-file=/etc/sarah-dnsmasq.conf \
  --pid-file=/tmp/sarah-dnsmasq.pid

echo "DNS recovery command completed."
