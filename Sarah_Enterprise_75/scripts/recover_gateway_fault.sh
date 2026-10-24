#!/bin/bash
set -e

echo "======================================"
echo " SARAH-ENT-001: Gateway Fault Recovery"
echo "======================================"

echo "[1] Restoring correct default gateway on pc1..."

python3 -m kathara exec pc1 -- \
  ip route replace default via 10.10.1.1

echo "[2] Checking routing table..."

python3 -m kathara exec pc1 -- \
  ip route show default

echo "[3] Recovery completed."
