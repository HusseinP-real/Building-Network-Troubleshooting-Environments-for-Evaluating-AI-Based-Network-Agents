#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "$0")/../lab" && pwd)"
kathara lclean -d "$D"
