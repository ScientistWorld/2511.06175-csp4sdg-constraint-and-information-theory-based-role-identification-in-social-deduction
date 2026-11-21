#!/bin/bash
# Score the simple role-count prior baseline (baseline/prior.py) through the
# train evaluator. Writes outputs/baseline_prior_train.json (not ranked).
#
#   bash scripts/baseline.sh [--limit-per-size N]
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p outputs

python3 eval/train/evaluate.py --predict-cmd "python3 baseline/prior.py" \
  --output outputs/baseline_prior_train.json "$@"
