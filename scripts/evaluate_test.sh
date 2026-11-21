#!/bin/bash
# Hidden test evaluation. Runs with no arguments:
#
#   bash scripts/evaluate_test.sh
#
# Decodes the held-out AvalonLogs instances kept only in eval/test/, runs the
# method on disk through scripts/predict.sh, recomputes every score from the
# raw predictions and writes scoring/scores_test.json (one entry per method
# name the predictor emits). Optional flags are passed to eval/test/evaluate.py
# (--output, --predict-cmd); the hidden test uses the defaults.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

python3 eval/test/evaluate.py "$@"
