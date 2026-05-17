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

cd /home/user

mkdir -p data/downloads data/avalonlogs_raw

if [ ! -s data/downloads/avalonlogs-master.zip ]; then
    echo "Fetching AvalonLogs archive from GitHub..."
    curl -L \
        https://github.com/WhoaWhoa/avalonlogs/archive/refs/heads/master.zip \
        -o data/downloads/avalonlogs-master.zip
fi

if [ -z "$(ls -A data/avalonlogs_raw 2>/dev/null)" ]; then
    echo "Extracting AvalonLogs raw files..."
    rm -rf data/downloads/avalonlogs_extract
    mkdir -p data/downloads/avalonlogs_extract
    python3 - <<'PY'
import shutil
import zipfile
from pathlib import Path

archive = Path("data/downloads/avalonlogs-master.zip")
extract_dir = Path("data/downloads/avalonlogs_extract")
raw_dir = Path("data/avalonlogs_raw")
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
echo "  AvalonLogs raw: data/avalonlogs_raw/ ($(ls data/avalonlogs_raw 2>/dev/null | wc -l) files)"
