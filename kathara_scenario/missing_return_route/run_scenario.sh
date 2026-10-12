#!/bin/bash

set -e

echo "======================================"
echo "Starting Kathara fault scenario"
echo "Scenario: Missing Return Route"
echo "======================================"

echo ""
echo "[1] Cleaning previous Kathara lab..."
kathara lclean || true

echo ""
echo "[2] Starting Kathara lab..."
kathara lstart

echo ""
echo "Waiting for containers to initialise..."
sleep 5

echo ""
echo "======================================"
echo "[3] Testing local connectivity"
echo "======================================"

echo "Testing h1 -> r1..."
kathara exec h1 -- ping -c 2 10.0.1.1

echo ""
echo "Testing h1 -> h2..."
kathara exec h1 -- ping -c 2 10.0.1.20

echo ""
echo "Testing r1 -> r2..."
kathara exec r1 -- ping -c 2 10.0.12.2

echo ""
echo "Testing r2 -> h3..."
kathara exec r2 -- ping -c 2 10.0.2.10

echo ""
echo "======================================"
echo "[4] Testing injected fault"
echo "Expected: h1 cannot reach h3"
echo "======================================"

if kathara exec h1 -- ping -c 2 -W 1 10.0.2.10; then
    echo ""
    echo "ERROR: h1 reached h3."
    echo "The fault may not have been injected correctly."
    exit 1
else
    echo ""
    echo "PASS: h1 cannot reach h3 as expected."
    echo "The routing fault is successfully reproduced."
fi

echo ""
echo "======================================"
echo "[5] Inspecting r2 routing table"
echo "======================================"

kathara exec r2 -- ip route

echo ""
echo "Expected missing route:"
echo "10.0.1.0/24 via 10.0.12.1"

echo ""
echo "======================================"
echo "[6] Applying repair"
echo "======================================"

kathara exec r2 -- ip route add 10.0.1.0/24 via 10.0.12.1

echo ""
echo "Updated r2 routing table:"
kathara exec r2 -- ip route

echo ""
echo "======================================"
echo "[7] Testing connectivity after repair"
echo "======================================"

if kathara exec h1 -- ping -c 3 10.0.2.10; then
    echo ""
    echo "PASS: Connectivity restored."
    echo "The missing route was successfully repaired."
else
    echo ""
    echo "ERROR: Connectivity is still unavailable."
    exit 1
fi

echo ""
echo "======================================"
echo "Scenario completed successfully"
echo "======================================"

echo ""
echo "Cleaning Kathara environment..."
kathara lclean

echo ""
echo "Done."