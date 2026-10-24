#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

fault_started=0

cleanup() {
    status=$?
    trap - EXIT

    if [ "$fault_started" -eq 1 ]; then
        echo "[CLEANUP] Restoring R1 static route..."
        if ! ./scripts/recover_ENT_002.sh; then
            echo "ERROR: Static route recovery failed"
            status=1
        fi
    fi

    exit "$status"
}

trap cleanup EXIT

echo "=== SARAH-ENT-002 Automated Validation ==="

echo "[1/6] Checking healthy Server connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10

echo "[2/6] Checking healthy Finance connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10

echo "[3/6] Injecting static route blackhole..."
fault_started=1
./scripts/inject_ENT_002.sh

echo "[4/6] Verifying blackhole route..."
python3 -m kathara exec r1 -- ip route show 10.10.3.0/24 \
    | grep -q 'blackhole 10.10.3.0/24'

echo "[5/6] Checking selective connectivity failure..."

result=$(python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10 2>&1) || true
echo "$result"

if ! echo "$result" | grep -q '100% packet loss'; then
    echo "FAIL: Server connectivity did not fail as expected"
    exit 1
fi

echo "PASS: Server unreachable as expected"

python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10
echo "PASS: Finance connectivity maintained"

echo "[6/6] Recovering static route..."
./scripts/recover_ENT_002.sh

python3 -m kathara exec r1 -- ip route show 10.10.3.0/24 \
    | grep -q 'via 10.10.12.2 dev eth2'

python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10

fault_started=0

echo "=== SARAH-ENT-002: PASS ==="
