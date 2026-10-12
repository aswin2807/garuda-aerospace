import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent

for _p in [str(_backend_dir), str(_project_root)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
