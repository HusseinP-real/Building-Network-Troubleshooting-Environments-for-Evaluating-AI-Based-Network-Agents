#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Recovering SARAH-ENT-002: Restoring Static Route on R1"

python3 -m kathara exec r1 -- \
  ip route replace 10.10.3.0/24 via 10.10.12.2 dev eth2

echo "R1 route after recovery:"
python3 -m kathara exec r1 -- ip route show 10.10.3.0/24
