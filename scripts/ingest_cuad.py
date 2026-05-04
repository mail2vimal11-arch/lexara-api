#!/usr/bin/env python3
"""
ingest_cuad.py — Compute peer-frequency statistics from the CUAD dataset.

CUAD (Contract Understanding Atticus Dataset) is a public-domain corpus of
510 commercial contracts with 13K+ expert annotations across 41 clause-type
categories. For Lexara's Dark Obligation Detector we don't ingest the raw
annotations — we compute the *frequency* of each category across the 510
contracts (e.g. "Governing Law: 99%") so the detector can compare a SOW
against measured peer norms instead of hand-curated estimates.

Output: app/services/cuad_frequencies.json — a small (~2 KB) JSON file
containing {"_meta": {...}, "frequencies": {category: fraction, ...}} for
all 41 CUAD categories.

Stdlib only. No new deps. Idempotent — skips download if zip is cached and
skips extraction if the CSV is already on disk.

Usage:
    python scripts/ingest_cuad.py
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "cuad"
ZIP_PATH = DATA_DIR / "CUAD_v1.zip"
CSV_PATH = DATA_DIR / "CUAD_v1" / "master_clauses.csv"
OUT_PATH = REPO_ROOT / "app" / "services" / "cuad_frequencies.json"

CUAD_URL = "https://zenodo.org/records/4595826/files/CUAD_v1.zip"

# The CSV's first column is "Filename"; everything else is a clause category.
# Many categories have an "<Category>-Answer" Yes/No companion column. We
# treat the *text* column (the one without "-Answer") as the source of truth:
# non-empty cell ⇒ that clause is present in that contract.
# Answer-companion columns can end in "-Answer" or (due to a CSV typo for one
# category) "- Answer" with a space. Match both.
ANSWER_SUFFIXES = ("-Answer", "- Answer")
NON_CATEGORY_COLUMNS = {"Filename"}


# ── Steps ───────────────────────────────────────────────────────────────────


def _download_zip() -> None:
    """Download the CUAD zip if it's not already cached."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 0:
        print(f"[cache] {ZIP_PATH} already exists ({ZIP_PATH.stat().st_size} bytes), skipping download.")
        return

    print(f"[download] {CUAD_URL} -> {ZIP_PATH}")
    try:
        # urlretrieve doesn't follow some progress-friendly hooks, so we stream manually.
        req = urllib.request.Request(
            CUAD_URL,
            headers={"User-Agent": "lexara-cuad-ingest/1.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            written = 0
            with open(ZIP_PATH, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    f.write(chunk)
                    written += len(chunk)
                    if total:
                        pct = (written / total) * 100
                        print(f"\r[download] {written/1e6:.1f} / {total/1e6:.1f} MB ({pct:.1f}%)", end="", flush=True)
            print()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        # Clean up a partial file so reruns try again.
        try:
            if ZIP_PATH.exists():
                ZIP_PATH.unlink()
        except OSError:
            pass
        print(f"[error] CUAD download failed: {e}", file=sys.stderr)
        print(
            "[error] CUAD ingestion aborted. The dataset is required to compute "
            "real peer-frequency statistics; we will NOT fall back to fabricated "
            "numbers. Re-run this script when network is available.",
            file=sys.stderr,
        )
        sys.exit(1)


def _extract_csv() -> None:
    """Extract master_clauses.csv from the zip if not already on disk."""
    if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
        print(f"[cache] {CSV_PATH} already exists, skipping extraction.")
        return

    print(f"[extract] master_clauses.csv from {ZIP_PATH}")
    try:
        with zipfile.ZipFile(ZIP_PATH) as zf:
            # Find the master_clauses.csv member regardless of casing/path nesting.
            target = None
            for name in zf.namelist():
                if name.lower().endswith("master_clauses.csv"):
                    target = name
                    break
            if target is None:
                print(
                    f"[error] master_clauses.csv not found in {ZIP_PATH}. Members: {zf.namelist()[:5]}...",
                    file=sys.stderr,
                )
                sys.exit(1)

            CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(target) as src, open(CSV_PATH, "wb") as dst:
                dst.write(src.read())
    except zipfile.BadZipFile as e:
        print(f"[error] CUAD zip is corrupt: {e}", file=sys.stderr)
        try:
            ZIP_PATH.unlink()
        except OSError:
            pass
        sys.exit(1)


def _compute_frequencies() -> dict:
    """Read master_clauses.csv and return {category: fraction, ...}."""
    print(f"[compute] frequencies from {CSV_PATH}")
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Identify clause-text columns: skip Filename and any "-Answer" companions.
        category_cols: list[tuple[int, str]] = []
        for i, col in enumerate(header):
            col_clean = col.strip()
            if not col_clean:
                continue
            if col_clean in NON_CATEGORY_COLUMNS:
                continue
            if any(col_clean.endswith(s) for s in ANSWER_SUFFIXES):
                continue
            category_cols.append((i, col_clean))

        present_counts = {name: 0 for _, name in category_cols}
        n_rows = 0

        # In master_clauses.csv, an *absent* clause is encoded as the literal
        # JSON-array string "[]" (not an empty cell). Treat both empty and "[]"
        # as absent. Anything else — typically a JSON list of quoted excerpts —
        # is treated as present.
        ABSENT_VALUES = {"", "[]"}

        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            n_rows += 1
            for idx, name in category_cols:
                if idx >= len(row):
                    continue
                cell = row[idx].strip()
                if cell not in ABSENT_VALUES:
                    present_counts[name] += 1

    if n_rows == 0:
        print("[error] No data rows found in CSV", file=sys.stderr)
        sys.exit(1)

    frequencies = {
        name: round(count / n_rows, 4) for name, count in present_counts.items()
    }
    return {"frequencies": frequencies, "n_contracts": n_rows}


def _write_output(payload: dict) -> None:
    out = {
        "_meta": {
            "source": CUAD_URL,
            "downloaded_at": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "n_contracts": payload["n_contracts"],
            "n_categories": len(payload["frequencies"]),
            "csv_filename": "master_clauses.csv",
            "notes": (
                "Frequency = fraction of CUAD contracts where the clause-text "
                "column is non-empty. Computed once at ingest time; not updated "
                "automatically. Re-run scripts/ingest_cuad.py to refresh."
            ),
        },
        "frequencies": payload["frequencies"],
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"[write] {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


def _print_summary(frequencies: dict, n_contracts: int) -> None:
    print()
    print(f"=== CUAD frequency summary (n={n_contracts} contracts, {len(frequencies)} categories) ===")
    print(f"{'Frequency':>10}  Category")
    print(f"{'-'*10:>10}  {'-'*40}")
    for name, freq in sorted(frequencies.items(), key=lambda kv: -kv[1]):
        print(f"{freq*100:>9.1f}%  {name}")


# ── Entry point ─────────────────────────────────────────────────────────────


def main() -> int:
    _download_zip()
    _extract_csv()
    result = _compute_frequencies()
    _write_output(result)
    _print_summary(result["frequencies"], result["n_contracts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
