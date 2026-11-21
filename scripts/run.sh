#!/bin/bash
# Reproduce the reference end to end: run the reference method (scripts/predict.sh)
# through the train and hidden-test evaluators. No training is involved; the
# method is run on the evaluation instances by the evaluators themselves.
#
# The iteration-11 hardening audit (variants and shortcuts through the same
# evaluators) is reproduced by: bash redteam/iter11/audit.sh
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring logs

echo "=== CSP4SDG AvalonLogs reference run ($(date)) ==="
bash scripts/evaluate.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
echo "=== done ($(date)) ==="
