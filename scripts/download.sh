#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: ~50 MB
# Estimated disk usage after extraction: ~50 MB raw logs, plus generated
# constraints/solver outputs created by scripts/method.sh.
#
# Datasets:
#   1. AvalonLogs: public raw JSON logs (~12,400 game files)
#      Source: https://github.com/WhoaWhoa/avalonlogs
#
# Note: Avalon-NLU and Mafia-UCB require LLM-based constraint extraction
# and API keys — they are NOT downloaded here. The CSP solver is tested
# on AvalonLogs which has programmatic constraint extraction.

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_DIR="data/downloads/avalonlogs_raw"
ARCHIVE="data/downloads/avalonlogs-master.zip"
EXTRACT_DIR="data/downloads/avalonlogs_extract"

mkdir -p data/downloads "$RAW_DIR"

if [ -n "$(find "$RAW_DIR" -maxdepth 1 -type f -print -quit 2>/dev/null)" ]; then
    echo "AvalonLogs raw data already present; skipping network fetch."
    echo "Download complete."
    echo "Data locations:"
    echo "  AvalonLogs raw: $RAW_DIR/ ($(find "$RAW_DIR" -maxdepth 1 -type f | wc -l) files)"
    exit 0
fi

if [ ! -s "$ARCHIVE" ]; then
    echo "Fetching AvalonLogs archive from GitHub..."
    curl --fail -L \
        https://github.com/WhoaWhoa/avalonlogs/archive/refs/heads/master.zip \
        -o "$ARCHIVE"
fi

if [ -z "$(ls -A "$RAW_DIR" 2>/dev/null)" ]; then
    echo "Extracting AvalonLogs raw files..."
    rm -rf "$EXTRACT_DIR"
    mkdir -p "$EXTRACT_DIR"
    python3 - <<'PY'
import shutil
import zipfile
from pathlib import Path

archive = Path("data/downloads/avalonlogs-master.zip")
extract_dir = Path("data/downloads/avalonlogs_extract")
raw_dir = Path("data/downloads/avalonlogs_raw")
raw_dir.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(archive) as zf:
    zf.extractall(extract_dir)

root = next(extract_dir.glob("avalonlogs-*"))
copied = 0
for fp in root.rglob("*"):
    if not fp.is_file():
        continue
    if fp.name.startswith("."):
        continue
    # AvalonLogs game files are extensionless timestamp/id JSON files.
    if fp.suffix:
        continue
    shutil.copy2(fp, raw_dir / fp.name)
    copied += 1
print(f"Copied {copied} raw log files.")
PY
fi

echo "Download complete."
echo "Data locations:"
echo "  AvalonLogs raw: $RAW_DIR/ ($(ls "$RAW_DIR" 2>/dev/null | wc -l) files)"
