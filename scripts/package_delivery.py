"""
Script to create a clean, reproducible delivery archive of the verified ROD project.
Excludes venvs, caches, temporary files, and node_modules.
Includes all source code, models, configs, tests, and documentation.
"""

import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = ROOT / "garuda_rod_verified_project.zip"

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".next",
    "__pycache__",
    ".pytest_cache",
    "outputs",
    "scratch",
    "runs",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".DS_Store",
    ".log",
}

def should_exclude(path: Path) -> bool:
    # Check parts
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.startswith("matplotlib-"):
            return True

    # Check extensions
    if path.suffix in EXCLUDE_EXTENSIONS:
        return True

    # Exclude temporary uploads
    if "data/uploads" in str(path) and path.name != ".gitkeep":
        return True

    # Exclude zip itself
    if path.name == "garuda_rod_verified_project.zip":
        return True

    return False

def package_project():
    print(f"Packaging verified project from {ROOT} to {OUTPUT_ZIP}...")
    file_count = 0
    total_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in ROOT.rglob("*"):
            if file_path.is_file() and not should_exclude(file_path):
                arcname = file_path.relative_to(ROOT)
                zf.write(file_path, arcname)
                file_count += 1
                total_bytes += file_path.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_bytes / (1024 * 1024)

    print(f"Archive successfully created: {OUTPUT_ZIP}")
    print(f"  Total Files Packaged: {file_count}")
    print(f"  Raw Size: {raw_size_mb:.2f} MB")
    print(f"  Compressed Zip Size: {zip_size_mb:.2f} MB")

    # Verify critical model files are in archive
    with zipfile.ZipFile(OUTPUT_ZIP, "r") as zf:
        namelist = set(zf.namelist())
        critical_files = [
            "ml_engine/models/runway_light_best.pt",
            "ml_engine/models/FOD_Karhtikeyan.pt",
            "ml_engine/models/navigation_best.pt",
            "ml_engine/models/model_manifest.yaml",
            "README.md",
            "backend/app/main.py",
            "frontend/package.json",
        ]
        print("\nVerifying critical archive contents:")
        for cf in critical_files:
            in_zip = cf in namelist
            print(f"  {'✓' if in_zip else '✗'} {cf}")
            assert in_zip, f"Critical file {cf} missing from archive!"

    print("\n[VERIFIED] Delivery archive integrity check passed 100%.")

if __name__ == "__main__":
    package_project()
