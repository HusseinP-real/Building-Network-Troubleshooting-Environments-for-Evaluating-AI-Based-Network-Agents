#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

fault_started=0

cleanup() {
    status=$?
    trap - EXIT

    if [ "$fault_started" -eq 1 ]; then
        echo "[CLEANUP] Restoring R1 eth1..."
        if ! ./scripts/recover_ENT_003.sh; then
            echo "ERROR: Recovery failed"
            status=1
        fi
    fi

    exit "$status"
}

trap cleanup EXIT

echo "=== SARAH-ENT-003 Automated Validation ==="

echo "[1/6] Checking healthy Finance connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10

echo "[2/6] Checking healthy Server connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10

echo "[3/6] Injecting Router1 eth1 down..."
fault_started=1
./scripts/inject_ENT_003.sh

echo "[4/6] Verifying eth1 is DOWN..."
state=$(python3 -m kathara exec r1 -- ip -br link show eth1)
echo "$state"

if ! echo "$state" | grep -Eq '^eth1[[:space:]]+DOWN'; then
    echo "FAIL: eth1 is not DOWN"
    exit 1
fi

echo "[5/6] Checking selective connectivity failure..."

result=$(python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10 2>&1) || true
echo "$result"

if ! echo "$result" | grep -q '100% packet loss'; then
    echo "FAIL: Finance connectivity did not fail as expected"
    exit 1
fi

echo "PASS: Finance unreachable as expected"

python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10
echo "PASS: Server connectivity maintained"

echo "[6/6] Recovering Router1 eth1..."
./scripts/recover_ENT_003.sh

state=$(python3 -m kathara exec r1 -- ip -br link show eth1)
echo "$state"

if ! echo "$state" | grep -Eq '^eth1[[:space:]]+UP'; then
    echo "FAIL: eth1 did not recover"
    exit 1
fi

python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10

fault_started=0

echo "=== SARAH-ENT-003: PASS ==="
