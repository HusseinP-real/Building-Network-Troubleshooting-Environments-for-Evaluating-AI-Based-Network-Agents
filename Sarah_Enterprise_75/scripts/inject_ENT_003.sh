#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Injecting SARAH-ENT-003: Router1 Finance Interface Down"

python3 -m kathara exec r1 -- ip link set eth1 down

echo "R1 eth1 after injection:"
python3 -m kathara exec r1 -- ip -br link show eth1
