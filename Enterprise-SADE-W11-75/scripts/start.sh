#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara lstart -d "$LAB" --noterminals
echo "Started 75-device topology. Allow routing convergence before checking."
