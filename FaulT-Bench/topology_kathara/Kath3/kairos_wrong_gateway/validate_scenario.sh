#!/bin/bash

EVIDENCE_DIR="$(dirname "$0")/evidence"

HEALTHY="$EVIDENCE_DIR/01_healthy_raw.txt"
FAULT="$EVIDENCE_DIR/02_fault_raw.txt"
RECOVERY="$EVIDENCE_DIR/03_recovery_raw.txt"

PASS=0
FAIL=0

check() {
    if eval "$2"; then
        echo "[PASS] $1"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] $1"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo " Wrong Default Gateway Validator"
echo "========================================"

check "Healthy gateway is correct" \
    "grep -q 'default via 172.16.20.1 dev eth0' '$HEALTHY'"

check "Healthy local connectivity succeeds" \
    "[ \$(grep -c '0% packet loss' '$HEALTHY') -ge 2 ]"

check "Healthy remote connectivity succeeds" \
    "grep -A10 'Remote connectivity test' '$HEALTHY' | grep -q '0% packet loss'"

check "Wrong gateway was injected" \
    "grep -q 'default via 172.16.20.254 dev eth0' '$FAULT'"

check "Local network remains reachable during fault" \
    "grep -A10 'Local gateway test' '$FAULT' | grep -q '0% packet loss'"

check "Remote connectivity fails during fault" \
    "grep -A15 'Remote connectivity test' '$FAULT' | grep -q '100% packet loss'"

check "Correct gateway is restored" \
    "grep -q 'default via 172.16.20.1 dev eth0' '$RECOVERY'"

check "Remote connectivity is restored" \
    "grep -A10 'Remote connectivity test' '$RECOVERY' | grep -q '0% packet loss'"

echo
echo "$PASS checks passed"
echo "$FAIL checks failed"

if [ "$FAIL" -eq 0 ]; then
    echo "SCENARIO RESULT: PASS"
    exit 0
else
    echo "SCENARIO RESULT: FAIL"
    exit 1
fi
