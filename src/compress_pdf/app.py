#!/usr/bin/env python3
"""
PDF Batch Compressor (GUI) - Ghostscript

- Select input folder (PDF) or a single PDF
- Option: include subfolders
- Select output folder
- Compress each PDF with Ghostscript, e.g.:
    gswin64c -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook ...

Requirements:
- Python 3.x
- Ghostscript installed (Windows: gswin64c.exe). If it is not on PATH, choose it via the GUI.
"""

import os
import sys
import shutil
import subprocess
import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


GS_CANDIDATES = ["gswin64c", "gswin64c.exe", "gs", "gs.exe"]
PDF_PRESETS = [
    ("Very light (/screen)", "/screen"),
    ("Light (/ebook)", "/ebook"),
    ("Balanced (/printer)", "/printer"),
    ("High quality (/prepress)", "/prepress"),
    ("Default (/default)", "/default"),
]


def find_ghostscript():
    for name in GS_CANDIDATES:
        p = shutil.which(name)
        if p:
            return p
    return None


def list_pdfs(input_dir: Path, recursive: bool):
    if recursive:
        for root, _, files in os.walk(input_dir):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    yield Path(root) / fn
    else:
        for fn in input_dir.iterdir():
            if fn.is_file() and fn.suffix.lower() == ".pdf":
                yield fn


def safe_output_path(output_root: Path, input_root: Path, pdf_path: Path):
    """Keep subfolder structure, return the output path."""
    rel = pdf_path.relative_to(input_root)
    out_path = output_root / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def compress_pdf(gs_exe: str, in_pdf: Path, out_pdf: Path, pdf_setting: str):
    # Example command:
    # gswin64c -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH -sOutputFile=... ...
    cmd = [
        gs_exe,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_setting}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={str(out_pdf)}",
        str(in_pdf),
    ]
    # Run command
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Compressor (Ghostscript)")
        self.geometry("780x520")
        self.minsize(760, 500)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.recursive = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=True)
        self.gs_path = tk.StringVar(value="")
        self.preset_choice = tk.StringVar(value=PDF_PRESETS[1][0])
        self.preset_map = dict(PDF_PRESETS)

        self.log_q = queue.Queue()
        self.worker_thread = None
        self.stop_flag = threading.Event()

        self._build_ui()
        self._autodetect_gs()
        self.after(100, self._poll_log_queue)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        # Input path (folder or single PDF)
        row1 = ttk.Frame(frm)
        row1.pack(fill="x", **pad)
        ttk.Label(row1, text="Input (folder or PDF):", width=22).pack(side="left")
        ttk.Entry(row1, textvariable=self.input_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row1, text="Choose...", command=self.choose_input).pack(side="left")

        # Output directory
        row2 = ttk.Frame(frm)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="OUTPUT folder:", width=22).pack(side="left")
        ttk.Entry(row2, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row2, text="Choose...", command=self.choose_output).pack(side="left")

        # Options
        row3 = ttk.Frame(frm)
        row3.pack(fill="x", **pad)
        ttk.Checkbutton(row3, text="Process subfolders", variable=self.recursive).pack(side="left")
        ttk.Checkbutton(row3, text="Overwrite if exists", variable=self.overwrite).pack(side="left", padx=18)

        # Compression level
        row3b = ttk.Frame(frm)
        row3b.pack(fill="x", **pad)
        ttk.Label(row3b, text="Compression level:", width=22).pack(side="left")
        ttk.Combobox(
            row3b,
            textvariable=self.preset_choice,
            values=[label for label, _ in PDF_PRESETS],
            state="readonly",
            width=30,
        ).pack(side="left", padx=8)

        # Ghostscript path
        row4 = ttk.Frame(frm)
        row4.pack(fill="x", **pad)
        ttk.Label(row4, text="Ghostscript (gs):", width=22).pack(side="left")
        ttk.Entry(row4, textvariable=self.gs_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(row4, text="Change...", command=self.choose_gs).pack(side="left")

        # Buttons
        row5 = ttk.Frame(frm)
        row5.pack(fill="x", **pad)
        self.btn_start = ttk.Button(row5, text="Start compression", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(row5, text="Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=10)

        # Progress
        row6 = ttk.Frame(frm)
        row6.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(row6, mode="determinate")
        self.progress.pack(fill="x", expand=True)

        # Log area
        ttk.Label(frm, text="Log:").pack(anchor="w", padx=10, pady=(8, 0))
        self.txt = tk.Text(frm, height=18, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.configure(state="disabled")

    def _autodetect_gs(self):
        gs = find_ghostscript()
        if gs:
            self.gs_path.set(gs)
            self._log(f"Ghostscript found: {gs}")
        else:
            self._log("Ghostscript not found on PATH. Select gswin64c.exe (Windows) or gs (Linux/macOS).")

    def choose_input(self):
        choice = messagebox.askyesnocancel(
            "Input type",
            "Process a SINGLE PDF file?\nYes = choose file\nNo = choose folder",
        )
        if choice is None:
            return
        if choice:
            f = filedialog.askopenfilename(
                title="Select PDF",
                filetypes=[("PDF", "*.pdf"), ("All files", "*.*")],
            )
            if f:
                self.input_dir.set(f)
                self.recursive.set(False)
        else:
            d = filedialog.askdirectory(title="Select INPUT folder")
            if d:
                self.input_dir.set(d)

    def choose_output(self):
        d = filedialog.askdirectory(title="Select OUTPUT folder")
        if d:
            self.output_dir.set(d)

    def choose_gs(self):
        f = filedialog.askopenfilename(
            title="Select Ghostscript executable",
            filetypes=[("Executables", "*.exe"), ("All files", "*.*")],
        )
        if f:
            self.gs_path.set(f)
            self._log(f"Ghostscript set to: {f}")

    def _validate(self):
        in_path = Path(self.input_dir.get().strip())
        out_dir = Path(self.output_dir.get().strip())
        gs = self.gs_path.get().strip()

        if not in_path.exists():
            messagebox.showerror("Error", "Select a valid INPUT path (folder or PDF).")
            return None

        is_file = in_path.is_file()
        if is_file and in_path.suffix.lower() != ".pdf":
            messagebox.showerror("Error", "The selected file is not a PDF.")
            return None
        if not is_file and not in_path.is_dir():
            messagebox.showerror("Error", "Select a valid folder or PDF file.")
            return None
        if not out_dir.is_dir():
            messagebox.showerror("Error", "Select a valid OUTPUT folder.")
            return None
        if not gs or not Path(gs).exists():
            # try autodetect again
            gs2 = find_ghostscript()
            if gs2:
                self.gs_path.set(gs2)
                gs = gs2
            else:
                messagebox.showerror("Error", "Ghostscript not found. Select gswin64c.exe / gs.")
                return None

        # Avoid input=output which might overwrite sources
        try:
            comp_target = in_path if not is_file else in_path.parent
            if comp_target.resolve() == out_dir.resolve():
                out_dir = comp_target / "_compressed"
                out_dir.mkdir(parents=True, exist_ok=True)
                self.output_dir.set(str(out_dir))
                self._log(f"OUTPUT equals INPUT: using {out_dir} to avoid overwrites.")
        except Exception:
            pass

        return in_path, out_dir, gs, is_file

    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        validated = self._validate()
        if not validated:
            return
        input_path, out_dir, gs, is_file = validated

        pdfs = [input_path] if is_file else list(list_pdfs(input_path, self.recursive.get()))
        if not pdfs:
            messagebox.showinfo("No PDF", "No PDF found in the selected folder.")
            return

        self.stop_flag.clear()
        self.progress["value"] = 0
        self.progress["maximum"] = len(pdfs)

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        preset_value = self.preset_map.get(self.preset_choice.get(), "/ebook")

        self._log(f"PDF to process: {len(pdfs)}")
        if is_file:
            self._log("Single-file mode")
        self._log(f"Recursive: {self.recursive.get()} | Overwrite: {self.overwrite.get()}")
        self._log(f"Preset: -dCompatibilityLevel=1.4 -dPDFSETTINGS={preset_value}")

        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(input_path.parent if is_file else input_path, out_dir, gs, pdfs, preset_value),
            daemon=True,
        )
        self.worker_thread.start()

    def stop(self):
        self.stop_flag.set()
        self._log("STOP requested... (finishes after current file)")

    def _worker(self, in_root: Path, out_dir: Path, gs: str, pdfs: list[Path], preset: str):
        ok = 0
        skipped = 0
        failed = 0
        total_in_bytes = 0
        total_out_bytes = 0

        for i, pdf in enumerate(pdfs, start=1):
            if self.stop_flag.is_set():
                break

            out_pdf = safe_output_path(out_dir, in_root, pdf)

            if out_pdf.exists() and not self.overwrite.get():
                skipped += 1
                self.log_q.put(("progress", i))
                self._log_q(f"[SKIP] {pdf.name} (already exists)")
                continue

            # If output exists and overwrite=True, write to a temp file then replace
            tmp_out = out_pdf.with_suffix(".tmp.pdf")
            if tmp_out.exists():
                try:
                    tmp_out.unlink()
                except Exception:
                    pass

            rc, _, err = compress_pdf(gs, pdf, tmp_out, preset)
            if rc == 0 and tmp_out.exists() and tmp_out.stat().st_size > 0:
                try:
                    in_size = pdf.stat().st_size
                    out_tmp_size = tmp_out.stat().st_size

                    total_in_bytes += in_size

                    if out_tmp_size >= in_size and in_size > 0:
                        if out_pdf.exists():
                            out_pdf.unlink()
                        shutil.copy2(pdf, out_pdf)
                        tmp_out.unlink()
                        ratio = (out_tmp_size / in_size) if in_size else 1.0
                        total_out_bytes += in_size
                        self._log_q(
                            f"[COPY] {pdf.relative_to(in_root)} compression not beneficial: "
                            f"{out_tmp_size/1e6:.2f}MB >= {in_size/1e6:.2f}MB ({ratio:.2%}). Original copied."
                        )
                        ok += 1
                    else:
                        # Replace atomically when possible
                        if out_pdf.exists():
                            out_pdf.unlink()
                        tmp_out.rename(out_pdf)

                        out_size = out_pdf.stat().st_size
                        ratio = (out_size / in_size) if in_size else 1.0
                        total_out_bytes += out_size
                        self._log_q(
                            f"[OK] {pdf.relative_to(in_root)}  {in_size/1e6:.2f}MB -> {out_size/1e6:.2f}MB  ({ratio:.2%})"
                        )
                        ok += 1
                except Exception as e:
                    failed += 1
                    self._log_q(f"[FAIL] {pdf.name} (rename/write): {e}")
                    try:
                        if tmp_out.exists():
                            tmp_out.unlink()
                    except Exception:
                        pass
            else:
                failed += 1
                self._log_q(f"[FAIL] {pdf.name} (Ghostscript rc={rc})")
                if err:
                    self._log_q(f"       stderr: {err.strip()[:500]}")
                try:
                    if tmp_out.exists():
                        tmp_out.unlink()
                except Exception:
                    pass

            self.log_q.put(("progress", i))

        total_saved = max(total_in_bytes - total_out_bytes, 0)
        self.log_q.put(("done", (ok, skipped, failed, len(pdfs), total_saved, total_in_bytes)))

    def _log(self, msg: str):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _log_q(self, msg: str):
        self.log_q.put(("log", msg))

    def _poll_log_queue(self):
        try:
            while True:
                kind, payload = self.log_q.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "progress":
                    self.progress["value"] = payload
                elif kind == "done":
                    ok, skipped, failed, total, saved, total_in = payload
                    self._log(f"\nDONE. OK={ok}  SKIP={skipped}  FAIL={failed}  TOT={total}")
                    if total_in > 0:
                        saved_mb = saved / 1e6
                        saved_pct = (saved / total_in) if total_in else 0
                        self._log(f"Space saved: {saved_mb:.2f} MB ({saved_pct:.2%})")
                    else:
                        self._log("Space saved: n/a")
                    self.btn_start.configure(state="normal")
                    self.btn_stop.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)


def main():
    # On Windows, slightly improve window DPI rendering (optional)
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
