#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

STARTUP="$ROOT_DIR/topology_kathara/Enterprise80/sydr1.startup"

echo "[RECOVERY] Recovering sydr1..."

CONTAINER="$(docker ps --format '{{.Names}}' | grep '_sydr1_' | head -1)"

if [ -z "$CONTAINER" ]; then

    echo "FAIL: sydr1 container is not running"

    exit 1

fi

echo "[1/3] Re-applying sydr1 configuration..."

docker exec -i "$CONTAINER" bash < "$STARTUP"

echo "[2/3] Waiting 30 seconds for OSPF convergence..."

sleep 30

echo "[3/3] Checking recovery..."

if ! docker exec "$CONTAINER" vtysh -c "show ip ospf neighbor" | grep -q "Full"; then

    echo "FAIL: OSPF adjacency did not recover"

    exit 1

fi

if ! docker exec "$CONTAINER" ping -c 3 -W 2 10.100.10.11 >/dev/null 2>&1; then

    echo "FAIL: DC connectivity did not recover"

    exit 1

fi

echo "PASS: recovery successful"

