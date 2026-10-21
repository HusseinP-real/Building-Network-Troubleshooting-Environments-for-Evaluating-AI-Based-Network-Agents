"""Load API keys from SADE-NetworkAgent's .env into the process environment.

Every entry point must call this before the first run: the runners abort with
"ANTHROPIC_API_KEY not set" otherwise -- and only AFTER the lab has already
been deployed, so the failure is needlessly expensive.
"""
from __future__ import annotations

import os
from pathlib import Path

from .paths import ENV_FILE


def load_env(env_path: Path = ENV_FILE) -> bool:
    """Read KEY=value lines into os.environ (existing values win).

    Returns False when the file does not exist, so callers can warn that they
    are relying on already-exported variables. Comment lines, blank lines and
    placeholder values (starting with ``<``) are skipped.
    """
    found = env_path.exists()
    if found:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v and not v.startswith("<"):
                os.environ.setdefault(k, v)
    # The cloud proxy reserves OPENAI_ secret target names. Accept an allowed
    # binding alias in memory; never write a credential into a repository file.
    alias = os.environ.get("FAULTBENCH_OPENAI_API_KEY", "").strip()
    if alias and not os.environ.get("OPENAI_API_KEY", "").strip():
        os.environ["OPENAI_API_KEY"] = alias
    return found
