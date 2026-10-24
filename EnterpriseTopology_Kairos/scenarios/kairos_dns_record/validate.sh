#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/../.."

mkdir -p "$DIR/evidence"

NEEDS_REPAIR=0

cleanup() {
    result=$?
    trap - EXIT
    if [ "$NEEDS_REPAIR" -eq 1 ]; then
        echo "Attempting DNS recovery after interruption..."
        "$DIR/repair.sh" || true
    fi
    exit "$result"
}
trap cleanup EXIT

check_dns() {
    expected="$1"
    result=$(python3 lab.py exec office getent ahostsv4 app.enterprise.test)
    echo "$result"
    echo "$result" | awk -v ip="$expected" \
        '$1 == ip {found=1} END {exit !found}'
}

check_http() {
    url="$1"
    expected="$2"

    result=$(python3 lab.py exec office curl \
        --connect-timeout 3 --max-time 6 \
        -s -o /dev/null \
        -w 'HTTP status: %{http_code}\n' \
        "$url" || true)

    echo "$url: $result"
    echo "$result" | grep -Fq "HTTP status: $expected"
}

healthy_phase() {
    echo "=== HEALTHY PHASE ==="
    check_dns "10.30.10.10"
    check_http "http://app.enterprise.test/" "200"
    check_http "http://10.30.10.10/" "200"
    echo "HEALTHY: PASS"
}

fault_phase() {
    echo "=== FAULT PHASE ==="
    check_dns "10.30.10.99"
    check_http "http://app.enterprise.test/" "000"
    check_http "http://10.30.10.10/" "200"
    echo "FAULT: PASS"
}

recovery_phase() {
    echo "=== RECOVERY PHASE ==="
    check_dns "10.30.10.10"
    check_http "http://app.enterprise.test/" "200"
    python3 lab.py check
    echo "RECOVERY: PASS"
}

echo "Starting DNS scenario validation..."

healthy_phase 2>&1 | tee "$DIR/evidence/healthy.txt"

NEEDS_REPAIR=1
"$DIR/inject.sh" 2>&1 | tee "$DIR/evidence/injection.txt"

fault_phase 2>&1 | tee "$DIR/evidence/fault.txt"

"$DIR/repair.sh" 2>&1 | tee "$DIR/evidence/repair.txt"
NEEDS_REPAIR=0

recovery_phase 2>&1 | tee "$DIR/evidence/recovery.txt"

echo "DNS SCENARIO VALIDATION: PASS"
