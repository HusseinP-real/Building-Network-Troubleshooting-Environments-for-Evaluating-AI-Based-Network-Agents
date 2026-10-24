#!/bin/bash
set -e

echo "======================================"
echo " SARAH-ENT-001: Gateway Fault Injection"
echo "======================================"

echo "[1] Injecting incorrect default gateway on pc1..."

python3 -m kathara exec pc1 -- \
  ip route replace default via 10.10.1.99

echo "[2] Checking routing table..."

python3 -m kathara exec pc1 -- \
  ip route show default

echo "[3] Fault injection completed."
