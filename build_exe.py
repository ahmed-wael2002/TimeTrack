"""Build a portable Windows exe with PyInstaller.

The database and Excel exports are stored next to TimeTrack.exe, so the
folder can be copied to a USB drive or another PC without installation.
"""

from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ICON_PNG = ROOT / "assets" / "icon.png"
ICON_ICO = ROOT / "assets" / "icon.ico"


def png_to_ico(png_path: Path, ico_path: Path) -> None:
    """Wrap a PNG in an ICO container (Vista+), used as the Windows exe icon."""
    data = png_path.read_bytes()
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 22)
    ico_path.write_bytes(header + entry + data)


def main() -> int:
    if ICON_PNG.exists():
        png_to_ico(ICON_PNG, ICON_ICO)
    sep = ";" if sys.platform == "win32" else ":"
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
        "--add-data",
        f"{ICON_PNG}{sep}assets",
        "--add-data",
        f"{ICON_ICO}{sep}assets",
        "--icon",
        str(ICON_ICO if ICON_ICO.exists() else ICON_PNG),
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
