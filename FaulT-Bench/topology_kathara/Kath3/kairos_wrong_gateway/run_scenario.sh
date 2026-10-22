#!/bin/bash

set -u

CORRECT_GW="172.16.20.1"
WRONG_GW="172.16.20.254"
REMOTE_TARGET="192.168.100.1"
EVIDENCE_DIR="$(dirname "$0")/evidence"

mkdir -p "$EVIDENCE_DIR"

CONTAINER=$(docker ps --format '{{.ID}} {{.Names}}' \
    | grep 'laptop0' \
    | head -1 \
    | awk '{print $1}')

if [ -z "$CONTAINER" ]; then
    echo "[ERROR] laptop0 container not found."
    echo "Run: python -m kathara lstart"
    exit 1
fi

echo "========================================"
echo " Kairos Wrong Default Gateway Scenario"
echo "========================================"
echo "laptop0 container: $CONTAINER"
echo

echo "[1/3] HEALTHY STATE"

docker exec "$CONTAINER" sh -c "
ip route del default 2>/dev/null || true
ip route add default via $CORRECT_GW dev eth0

echo '=== HEALTHY STATE ==='
echo
echo '--- Routing table ---'
ip route
echo
echo '--- Local gateway test ---'
ping -c 4 $CORRECT_GW
echo
echo '--- Remote connectivity test ---'
ping -c 4 $REMOTE_TARGET
" | tee "$EVIDENCE_DIR/01_healthy_raw.txt"

echo
echo "[2/3] FAULT INJECTION"

docker exec "$CONTAINER" sh -c "
ip route del default
ip route add default via $WRONG_GW dev eth0

echo '=== FAULT STATE ==='
echo
echo '--- Routing table ---'
ip route
echo
echo '--- Local gateway test ---'
ping -c 4 $CORRECT_GW
echo
echo '--- Remote connectivity test ---'
ping -c 4 $REMOTE_TARGET || true
" | tee "$EVIDENCE_DIR/02_fault_raw.txt"

echo
echo "[3/3] RECOVERY"

docker exec "$CONTAINER" sh -c "
ip route del default
ip route add default via $CORRECT_GW dev eth0

echo '=== RECOVERY STATE ==='
echo
echo '--- Routing table ---'
ip route
echo
echo '--- Local gateway test ---'
ping -c 4 $CORRECT_GW
echo
echo '--- Remote connectivity test ---'
ping -c 4 $REMOTE_TARGET
" | tee "$EVIDENCE_DIR/03_recovery_raw.txt"

echo
echo "========================================"
echo " Scenario complete"
echo "========================================"
