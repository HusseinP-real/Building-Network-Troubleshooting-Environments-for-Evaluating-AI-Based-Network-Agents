#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Injecting SARAH-ENT-002: Incorrect Static Route on R1"

python3 -m kathara exec r1 -- \
  ip route replace blackhole 10.10.3.0/24

echo "R1 route after injection:"
python3 -m kathara exec r1 -- ip route show 10.10.3.0/24
