#!/bin/bash
# Development evaluation: identical to scripts/evaluate_train.sh (visible
# games only) but writes scoring/scores.json. Ranking uses only
# scoring/scores_test.json, produced by scripts/evaluate_test.sh.
#
#   bash scripts/evaluate.sh [--limit-per-size N] [--predict-cmd CMD]
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

python3 eval/train/evaluate.py --output scoring/scores.json "$@"
