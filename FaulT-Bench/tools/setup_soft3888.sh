#!/usr/bin/env bash
# Reuse the existing checkout; preserve dependency source and local changes.
set -euo pipefail
soft3888_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$soft3888_root"
export UV_CACHE_DIR=${UV_CACHE_DIR:-"$soft3888_root/.cache/uv"}
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-"$soft3888_root/.cache"}
export MPLCONFIGDIR=${MPLCONFIGDIR:-"$XDG_CACHE_HOME/matplotlib"}
soft3888_venv=${SOFT3888_VENV:-"$soft3888_root/.venv"}
soft3888_pin=aa8488a09ddb3a57e08f8137afd04bc87886e734
if [ ! -d SADE-NetworkAgent ]; then
  git clone https://github.com/Overlxrd-uwu/SADE-NetworkAgent SADE-NetworkAgent
  git -C SADE-NetworkAgent checkout --detach "$soft3888_pin"
fi
if [ "$(git -C SADE-NetworkAgent rev-parse HEAD)" != "$soft3888_pin" ]; then
  echo 'SADE checkout differs from the required reference; preserve local work and review before continuing.' >&2
  exit 2
fi
uv venv --allow-existing --python 3.12 "$soft3888_venv"
uv pip install --python "$soft3888_venv/bin/python" -c requirements.txt -e faultbench -e SADE-NetworkAgent 'matplotlib==3.10.9'
if [ ! -e SADE-NetworkAgent/.venv ] && [ ! -L SADE-NetworkAgent/.venv ]; then
  ln -s "$soft3888_venv" SADE-NetworkAgent/.venv
fi
export BASE_DIR="$soft3888_root/SADE-NetworkAgent"
uv pip check --python "$soft3888_venv/bin/python"
"$soft3888_venv/bin/python" tools/build_soft3888_images.py
"$soft3888_venv/bin/python" tools/prepare_soft3888_runtime.py
"$soft3888_venv/bin/python" tools/check_soft3888_environment.py
