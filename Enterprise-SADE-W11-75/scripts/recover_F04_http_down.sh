#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara exec -d "$LAB" srv02 -- sh -c "cd /tmp/www; python3 -m http.server 8000 --bind 10.20.9.11 >/tmp/http.log 2>&1 & echo $! >/tmp/http.pid"
