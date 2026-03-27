#!/usr/bin/env python3
"""Build a standalone Windows .exe for compress-pdf using PyInstaller.

Run this script with the compress-pdf conda environment active so that
both PyInstaller and Ghostscript are available on PATH.

Usage
-----
    python scripts/build_exe.py              # onedir bundle (recommended)
    python scripts/build_exe.py --onefile    # single .exe file
    python scripts/build_exe.py --no-gs      # skip bundling Ghostscript

Output
------
  onedir  -> dist/compress-pdf/   (share the whole folder with users)
  onefile -> dist/compress-pdf.exe

Ghostscript bundling
--------------------
The script searches for gswin64c.exe (Windows) or gs (Linux/macOS) on PATH.
If found, it copies the executable and its sibling gs*.dll files into the
output so that users do not need a separate Ghostscript installation.
For onefile builds the binaries are embedded via --add-binary and extracted
at runtime to sys._MEIPASS alongside the app.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINT = ROOT / "src" / "compress_pdf" / "app.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyinstaller"  # inside already-gitignored build/

GS_NAMES = ["gswin64c.exe", "gswin64c", "gs.exe", "gs"]


def find_gs_files() -> list[Path]:
    """Return the GS executable and its sibling gs*.dll files (if any)."""
    for name in GS_NAMES:
        gs = shutil.which(name)
        if gs:
            gs_path = Path(gs).resolve()
            files: list[Path] = [gs_path]
            for dll in sorted(gs_path.parent.glob("gs*.dll")):
                files.append(dll)
            return files
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a standalone compress-pdf executable with PyInstaller."
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Pack everything into a single .exe (slower startup, ~50 MB).",
    )
    parser.add_argument(
        "--no-gs",
        action="store_true",
        help="Do NOT bundle Ghostscript. Users will need to install it and locate it via the GUI.",
    )
    args = parser.parse_args()

    # --- check PyInstaller ---
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed.\nRun:  pip install pyinstaller")
        sys.exit(1)

    # --- locate Ghostscript ---
    gs_files: list[Path] = [] if args.no_gs else find_gs_files()
    if not args.no_gs:
        if gs_files:
            print(f"Ghostscript found : {gs_files[0]}")
            dlls = gs_files[1:]
            if dlls:
                print(f"  DLL(s) to bundle: {[f.name for f in dlls]}")
        else:
            print(
                "Warning: Ghostscript not found on PATH.\n"
                "  Activate the compress-pdf conda env, or install Ghostscript first.\n"
                "  The executable will still be built; users must locate gswin64c.exe via the GUI.\n"
            )

    # --- assemble PyInstaller command ---
    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        "compress-pdf",
        "--noconsole",  # hide the console window for this GUI app
        "--clean",
        "--noconfirm",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
    ]

    if args.onefile:
        cmd.append("--onefile")
        # Embed GS files into the bundle; they are extracted to sys._MEIPASS at runtime.
        for f in gs_files:
            cmd += ["--add-binary", f"{f};."]
    else:
        cmd.append("--onedir")

    cmd.append(str(ENTRY_POINT))

    # --- run PyInstaller ---
    print("\nRunning PyInstaller …")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("\nPyInstaller failed (see output above).")
        sys.exit(result.returncode)

    # --- onedir: copy GS files next to the exe ---
    if not args.onefile and gs_files:
        out_dir = DIST_DIR / "compress-pdf"
        for f in gs_files:
            dest = out_dir / f.name
            shutil.copy2(f, dest)
            print(f"Bundled into dist : {f.name}")

    # --- summary ---
    print()
    if args.onefile:
        exe = DIST_DIR / "compress-pdf.exe"
        print(f"Single-file exe  : {exe}")
        print("Ghostscript      :", "bundled" if gs_files else "NOT bundled – install separately")
    else:
        out_dir = DIST_DIR / "compress-pdf"
        print(f"Output folder    : {out_dir}")
        print("Share the entire folder with users (do not move the .exe out of it).")
        if gs_files:
            print("Ghostscript      : bundled – no separate installation needed")
        else:
            print("Ghostscript      : NOT bundled – users must install gswin64c.exe")

    print("\nDone.")


if __name__ == "__main__":
    main()
