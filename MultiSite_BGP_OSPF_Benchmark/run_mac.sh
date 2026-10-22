#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 tools/generate.py
python3 tools/create_tickets.py
python3 tools/validate_static.py
python3 -m unittest discover -s tests -v
if [[ "${1:-}" == "--start" ]]; then
  docker info >/dev/null
  kathara check
  python3 lab.py start
  echo 'Allow protocols to converge. Then run: python3 lab.py check'
else
  echo 'Static checks complete. To start the full lab: ./run_mac.sh --start'
fi
