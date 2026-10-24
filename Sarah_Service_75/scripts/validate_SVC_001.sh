#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

recover() {
    echo "[CLEANUP] Restoring DNS service..."
    ./scripts/recover_SVC_001.sh
}

cleanup() {
    status=$?
    trap - EXIT

    if [ "$status" -ne 0 ]; then
        recover || echo "WARNING: DNS recovery failed"
    fi

    exit "$status"
}

trap cleanup EXIT

echo "=== SARAH-SVC-001 Automated Validation ==="

echo "[1/5] Checking healthy DNS..."
python3 -m kathara exec pc1 -- nslookup -type=A app.sarah.test 10.20.3.10 | grep -q "10.20.3.20"
echo "PASS: Healthy DNS"

echo "[2/5] Injecting DNS fault..."
./scripts/inject_SVC_001.sh

echo "[3/5] Checking DNS failure..."
if python3 -m kathara exec pc1 -- nslookup -type=A -timeout=2 -retry=1 app.sarah.test 10.20.3.10 2>&1 | grep -q "Name:.*app.sarah.test"; then
    echo "FAIL: DNS unexpectedly succeeded"
    exit 1
else
    echo "PASS: DNS failed as expected"
fi

echo "[4/5] Checking IP connectivity during DNS fault..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.20.3.20
echo "PASS: IP connectivity maintained"

echo "[5/5] Recovering and checking DNS..."
./scripts/recover_SVC_001.sh
python3 -m kathara exec pc1 -- nslookup -type=A app.sarah.test 10.20.3.10 | grep -q "10.20.3.20"

echo "=== SARAH-SVC-001: PASS ==="
