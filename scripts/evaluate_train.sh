#!/bin/bash
# Train evaluation on the visible games. Runs with no arguments:
#
#   bash scripts/evaluate_train.sh
#
# Builds instances from data/avalonlogs_raw (visible games only), runs the
# method on disk through scripts/predict.sh, and writes
# scoring/scores_train.json with exactly the same metrics as the hidden test.
# Optional flags go to eval/train/evaluate.py (--output, --predict-cmd,
# --limit-per-size N for quick development runs).
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

python3 eval/train/evaluate.py "$@"
