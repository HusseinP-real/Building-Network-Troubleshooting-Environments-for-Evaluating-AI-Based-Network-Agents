#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="$ROOT/lab"
kathara exec -d "$LAB" edge1 -- sh -c "vtysh -c \"configure terminal\" -c \"router bgp 65001\" -c \"no neighbor 172.16.1.1 shutdown\""
