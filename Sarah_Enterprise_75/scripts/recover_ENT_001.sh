#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Recovering SARAH-ENT-001: Restoring PC1 Default Gateway"

python3 -m kathara exec pc1 -- ip route replace default via 10.10.1.1

echo "PC1 default route after recovery:"
python3 -m kathara exec pc1 -- ip route show default
