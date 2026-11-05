#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara exec -d "$LAB" srv02 -- sh -c "kill $(cat /tmp/http.pid)"
