"""Build a portable Windows exe with PyInstaller.

The database and Excel exports are stored next to TimeTrack.exe, so the
folder can be copied to a USB drive or another PC without installation.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "TimeTrack",
        "--hidden-import",
        "openpyxl",
        "--collect-submodules",
        "openpyxl",
        "--collect-submodules",
        "timetrack",
        "--paths",
        str(ROOT),
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT),
        str(ROOT / "main.py"),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode == 0:
        print(f"\nPortable exe: {ROOT / 'dist' / 'TimeTrack.exe'}")
        print("Copy the entire dist folder, or just TimeTrack.exe.")
        print("A data/ folder is created next to the exe on first launch.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
