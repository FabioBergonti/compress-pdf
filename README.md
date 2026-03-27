# compress-pdf 📄

A simple GUI tool to **recursively compress PDF files** in a selected folder using [`Ghostscript`](https://www.ghostscript.com/).

Designed to be easy to run for non-technical users while remaining fully scriptable and reproducible via `conda`.

Tested on **Windows**, should work on **Linux** and **macOS** as well. 🤞

## ⚡ Quick setup (conda)

1. Install [`miniforge`](https://github.com/robotology/robotology-superbuild/blob/master/doc/install-miniforge.md)
2. Create the environment:
   ```bash
   conda env create -f environment.yml
    ```
3. Activate it:
   ```bash
   conda activate compress-pdf
   ```
4. (Later) Update the environment:
   ```bash
   conda env update -f environment.yml --prune
   ```

The [`environment.yml`](environment.yml) installs:
* Python
* Ghostscript
* the local package (via `pip`), so the `compress-pdf` console command is registered

## ▶️ Run

After activating the environment launch the GUI:

```bash
compress-pdf
```

## 🚀 Ready-to-use launcher scripts

Launcher scripts allow starting the app without manually activating the environment.

Generate launchers with:
```bash
conda activate compress-pdf
python scripts/make_launcher.py
```

### Windows

* Use `run_compress_pdf.cmd`
* Double-click or run from a terminal

### Linux / macOS

* Use `run_compress_pdf.sh`
* The generator marks it executable
* If needed:

```bash
chmod +x run_compress_pdf.sh
```

## 📦 Build a standalone executable (no conda needed for end users)

You can package the app into a self-contained `.exe` using PyInstaller.  
The Ghostscript binary is bundled automatically when the conda environment is active.

1. Activate the environment and install PyInstaller:
   ```bash
   conda activate compress-pdf
   pip install pyinstaller
   ```
2. Run the build script:
   ```bash
   python scripts/build_exe.py
   ```
   This creates `dist/compress-pdf/` containing `compress-pdf.exe` and all dependencies (including Ghostscript).

3. Share the **entire** `dist/compress-pdf/` folder with users — they just double-click `compress-pdf.exe`.

### Build options

| Flag | Effect |
|------|--------|
| *(none)* | **Recommended.** Folder bundle (`dist/compress-pdf/`). Fast startup, Ghostscript included. |
| `--onefile` | Single `.exe` (~50 MB). Slower first launch. Ghostscript embedded. |
| `--no-gs` | Skip bundling Ghostscript. Users must install it and select it via the GUI. |

> **Note:** A `--onedir` (default) bundle must be distributed as a folder; moving only the `.exe` out of it will break the app.

---

## ⚙️ Ghostscript notes

* **Windows**: expected executable is `gswin64c.exe`
* **Linux / macOS**: binary is usually `gs`

The conda environment installs `ghostscript` automatically.
Alternatively, a system installation can be used and selected from the GUI if needed.
