#!/usr/bin/env python3
"""Generate the checked-in P20Enterprise v2 configuration from its explicit model."""
import argparse
from pathlib import Path
from p20_enterprise_model import rendered_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check for drift without writing')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    drift = []
    for name, content in rendered_files().items():
        path = root / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                drift.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if drift:
        parser.exit(1, 'Generated files differ:\n' + '\n'.join(drift) + '\n')
    print('PASS: generated files match' if args.check else 'Generated P20Enterprise v2 files')


if __name__ == '__main__':
    main()
