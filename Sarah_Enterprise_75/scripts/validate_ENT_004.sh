#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

fault_started=0

cleanup() {
    status=$?
    trap - EXIT

    if [ "$fault_started" -eq 1 ]; then
        echo "[CLEANUP] Removing ENT-004 firewall rule..."
        if ! ./scripts/recover_ENT_004.sh; then
            echo "ERROR: Firewall recovery failed"
            status=1
        fi
    fi

    exit "$status"
}

trap cleanup EXIT

RULE=(-s 10.10.1.10 -d 10.10.3.10 -j DROP)

echo "=== SARAH-ENT-004 Automated Validation ==="

echo "[1/7] Checking healthy Server connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10

echo "[2/7] Checking healthy Finance connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10

echo "[3/7] Injecting Firewall DROP rule..."
fault_started=1
./scripts/inject_ENT_004.sh

echo "[4/7] Verifying firewall rule..."
python3 -m kathara exec r1 -- iptables -C FORWARD "${RULE[@]}"
echo "PASS: Firewall DROP rule present"

echo "[5/7] Checking selective connectivity failure..."

result=$(python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10 2>&1) || true
echo "$result"

if ! echo "$result" | grep -q '100% packet loss'; then
    echo "FAIL: Server connectivity did not fail as expected"
    exit 1
fi

echo "PASS: Server unreachable as expected"

python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.2.10
echo "PASS: Finance connectivity maintained"

echo "[6/7] Recovering Firewall configuration..."
./scripts/recover_ENT_004.sh

if python3 -m kathara exec r1 -- iptables -C FORWARD "${RULE[@]}" 2>/dev/null; then
    echo "FAIL: Firewall DROP rule still present"
    exit 1
fi

echo "PASS: Firewall DROP rule removed"

echo "[7/7] Checking recovered Server connectivity..."
python3 -m kathara exec pc1 -- ping -c 3 -W 2 10.10.3.10

fault_started=0

echo "=== SARAH-ENT-004: PASS ==="
