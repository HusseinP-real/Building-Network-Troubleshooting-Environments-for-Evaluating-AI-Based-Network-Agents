#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara exec -d "$LAB" srv01 -- sh -c "dnsmasq --no-daemon --bind-interfaces --listen-address=10.20.9.10 --address=/web.corp.test/10.20.9.11 --address=/dns.corp.test/10.20.9.10 >/tmp/dns.log 2>&1 &"
