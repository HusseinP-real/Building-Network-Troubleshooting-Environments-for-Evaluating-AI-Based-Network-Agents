"""Run an upstream diagnostic server with explicit custom-lab inventory."""
import runpy
import sys
from pathlib import Path
from .inventory import install_inventory_adapter
from .paths import SADE_REPO

if __name__ == '__main__':
    target = Path(sys.argv[1]).resolve()
    allowed = SADE_REPO / 'src/nika/service/mcp_server'
    if target.parent != allowed.resolve() or not target.is_file():
        raise SystemExit('Only installed SADE diagnostic servers may be launched')
    install_inventory_adapter()
    sys.argv = [str(target)]
    runpy.run_path(str(target), run_name='__main__')
