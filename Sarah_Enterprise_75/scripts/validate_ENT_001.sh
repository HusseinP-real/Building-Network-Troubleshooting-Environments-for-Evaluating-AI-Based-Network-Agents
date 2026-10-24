#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

fault_injected=0

cleanup() {
    status=$?
    trap - EXIT

    if [ "$fault_injected" -eq 1 ]; then
        echo "[CLEANUP] Restoring PC1 gateway..."
        if ! ./scripts/recover_ENT_001.sh; then
            echo "ERROR: Gateway recovery failed"
            status=1
        fi
    fi

    exit "$status"
}

trap cleanup EXIT

ping_success() {
    python3 -m kathara exec pc1 -- ping -c 3 -W 2 "$1"
}

echo "=== SARAH-ENT-001 Automated Validation ==="

echo "[1/6] Checking healthy Finance connectivity..."
ping_success 10.10.2.10

echo "[2/6] Checking healthy Server connectivity..."
ping_success 10.10.3.10

echo "[3/6] Injecting incorrect gateway..."
fault_injected=1
./scripts/inject_ENT_001.sh

echo "[4/6] Checking HR local connectivity..."
ping_success 10.10.1.11

echo "[5/6] Checking remote connectivity failure..."
for target in 10.10.2.10 10.10.3.10; do
    result=$(python3 -m kathara exec pc1 -- ping -c 3 -W 2 "$target" 2>&1) && {
        echo "FAIL: $target unexpectedly reachable"
        exit 1
    }

    echo "$result"

    if ! echo "$result" | grep -q "100% packet loss"; then
        echo "FAIL: Expected packet loss not confirmed for $target"
        exit 1
    fi

    echo "PASS: $target unreachable as expected"
done

echo "[6/6] Recovering and checking connectivity..."
./scripts/recover_ENT_001.sh

ping_success 10.10.2.10
ping_success 10.10.3.10

echo "=== SARAH-ENT-001: PASS ==="
