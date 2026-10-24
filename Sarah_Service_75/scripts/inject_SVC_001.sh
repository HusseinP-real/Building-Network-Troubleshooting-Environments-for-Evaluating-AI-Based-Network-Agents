#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Injecting SARAH-SVC-001: DNS Service Down"

python3 -m kathara exec dns -- sh -c 'kill "$(cat /tmp/sarah-dnsmasq.pid)"'

echo "DNS fault injection completed."
