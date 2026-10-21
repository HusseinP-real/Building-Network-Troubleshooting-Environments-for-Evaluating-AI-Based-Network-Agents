#!/usr/bin/env python3
"""Run SOFT3888 lab validation using the installed FaulT-Bench environment."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'faultbench/src'))
from faultbench.validation import main
if __name__ == '__main__':
    raise SystemExit(main())
