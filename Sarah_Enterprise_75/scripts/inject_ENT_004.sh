#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Injecting SARAH-ENT-004: Firewall Misconfiguration"

RULE=(-s 10.10.1.10 -d 10.10.3.10 -j DROP)

# Avoid adding duplicate rules.
if ! python3 -m kathara exec r1 -- iptables -C FORWARD "${RULE[@]}" 2>/dev/null; then
    python3 -m kathara exec r1 -- iptables -I FORWARD 1 "${RULE[@]}"
fi

echo "R1 FORWARD rules after injection:"
python3 -m kathara exec r1 -- iptables -L FORWARD -n -v
