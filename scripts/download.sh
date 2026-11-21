#!/bin/bash
# Download all data needed for this environment.
#
# Estimated total download size: ~50 MB (AvalonLogs archive); ~25 MB on disk
# after extraction and filtering.
#
# Dataset: AvalonLogs public raw JSON game logs (WhoaWhoa 2022)
#   Source: https://github.com/WhoaWhoa/avalonlogs
#
# The visible games are already tracked under data/avalonlogs_raw/. This script
# only fetches when they are missing. Half of the games are the hidden test set:
# they are kept (encoded) only in eval/test/, and are dropped here from a fresh
# download using the hashed file names in eval/test/heldout_ids.txt. The archive
# itself is deleted after extraction.
#
# Avalon-NLU and Mafia-UCB need LLM-based constraint extraction and are not
# downloaded (their paper numbers are kept in scoring/reference.json only).

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RAW_DIR="data/avalonlogs_raw"
ARCHIVE="data/downloads/avalonlogs-master.zip"
EXTRACT_DIR="data/downloads/avalonlogs_extract"
MIN_EXPECTED_RAW_FILES=6000

mkdir -p data/downloads "$RAW_DIR"

raw_count="$(find "$RAW_DIR" -maxdepth 1 -type f 2>/dev/null | wc -l)"
if [ "$raw_count" -ge "$MIN_EXPECTED_RAW_FILES" ]; then
    echo "AvalonLogs visible games already present ($raw_count files); skipping network fetch."
    exit 0
fi

if [ ! -s "$ARCHIVE" ]; then
    echo "Fetching AvalonLogs archive from GitHub..."
    curl --fail -L \
        https://github.com/WhoaWhoa/avalonlogs/archive/refs/heads/master.zip \
        -o "$ARCHIVE"
fi

echo "Extracting AvalonLogs raw files (dropping hidden test games)..."
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
python3 - <<'PY'
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

archive = Path("data/downloads/avalonlogs-master.zip")
extract_dir = Path("data/downloads/avalonlogs_extract")
raw_dir = Path("data/avalonlogs_raw")
heldout = set()
ids = Path("eval/test/heldout_ids.txt")
if ids.exists():
    heldout = set(ids.read_text().split())

with zipfile.ZipFile(archive) as zf:
    zf.extractall(extract_dir)

root = next(extract_dir.glob("avalonlogs-*"))
copied = dropped = 0
for fp in root.rglob("*"):
    if not fp.is_file() or fp.name.startswith("."):
        continue
    try:
        payload = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(payload, dict) or not {"players", "missions", "outcome"}.issubset(payload):
        continue
    if hashlib.sha256(fp.name.encode()).hexdigest() in heldout:
        dropped += 1
        continue
    shutil.copy2(fp, raw_dir / fp.name)
    copied += 1
print(f"Copied {copied} visible game logs; dropped {dropped} hidden test games.")
PY
rm -rf "$EXTRACT_DIR" "$ARCHIVE"

echo "Download complete."
echo "  AvalonLogs visible games: $RAW_DIR/ ($(find "$RAW_DIR" -maxdepth 1 -type f | wc -l) files)"
