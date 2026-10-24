#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "Injecting SARAH-SVC-003: Incorrect Default Gateway on Router3"

python3 -m kathara exec r3 -- ip route replace default via 10.20.1.99

echo "Fault injected successfully."
echo "Router3 default route:"
python3 -m kathara exec r3 -- ip route show default
