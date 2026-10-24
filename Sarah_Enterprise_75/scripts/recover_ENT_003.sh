#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Recovering SARAH-ENT-003: Router1 Finance Interface"

python3 -m kathara exec r1 -- ip link set eth1 up

echo "R1 eth1 after recovery:"
python3 -m kathara exec r1 -- ip -br link show eth1
