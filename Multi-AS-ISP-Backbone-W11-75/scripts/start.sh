#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "$0")/../lab" && pwd)"
kathara lstart -d "$D" --noterminals
echo "Allow 30-90 seconds for IS-IS/OSPF/BGP convergence, then run baseline.sh"
