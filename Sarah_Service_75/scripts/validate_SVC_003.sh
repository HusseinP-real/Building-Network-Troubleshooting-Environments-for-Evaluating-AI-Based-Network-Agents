#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

recover() {
    echo "[CLEANUP] Restoring Router3 gateway..."
    ./scripts/recover_SVC_003.sh
}

trap recover EXIT

echo "=== SARAH-SVC-003 Automated Validation ==="

echo "[1/5] Checking healthy connectivity..."
python3 -m kathara exec pc3 -- ping -c 3 -W 2 10.20.3.10
echo "PASS: Healthy connectivity"

echo "[2/5] Injecting gateway fault..."
./scripts/inject_SVC_003.sh

echo "[3/5] Checking expected connectivity failure..."
if python3 -m kathara exec pc3 -- ping -c 3 -W 2 10.20.3.10; then
    echo "FAIL: Connectivity unexpectedly succeeded"
    exit 1
else
    echo "PASS: Connectivity failed as expected"
fi

echo "[4/5] Recovering gateway..."
./scripts/recover_SVC_003.sh

echo "[5/5] Checking recovered connectivity..."
python3 -m kathara exec pc3 -- ping -c 3 -W 2 10.20.3.10

echo "=== SARAH-SVC-003: PASS ==="
