#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara exec -d "$LAB" dist3 -- sh -c "/etc/init.d/frr stop"
