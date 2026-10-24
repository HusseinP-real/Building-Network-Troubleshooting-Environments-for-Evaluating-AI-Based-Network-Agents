#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Recovering SARAH-ENT-004: Removing Firewall DROP Rule"

RULE=(-s 10.10.1.10 -d 10.10.3.10 -j DROP)

# Remove only the rule introduced by this scenario.
while python3 -m kathara exec r1 -- iptables -C FORWARD "${RULE[@]}" 2>/dev/null; do
    python3 -m kathara exec r1 -- iptables -D FORWARD "${RULE[@]}"
done

echo "R1 FORWARD rules after recovery:"
python3 -m kathara exec r1 -- iptables -L FORWARD -n -v
