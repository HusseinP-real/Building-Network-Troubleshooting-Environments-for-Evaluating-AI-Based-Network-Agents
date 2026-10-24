#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Injecting SARAH-ENT-001: Incorrect Default Gateway on PC1"

python3 -m kathara exec pc1 -- ip route replace default via 10.10.1.99

echo "PC1 default route after injection:"
python3 -m kathara exec pc1 -- ip route show default
