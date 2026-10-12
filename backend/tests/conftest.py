import sys
from pathlib import Path

# Add project root and backend to sys.path
test_dir = Path(__file__).resolve().parent
backend_dir = test_dir.parent
project_root = backend_dir.parent

for p in [str(project_root), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)
