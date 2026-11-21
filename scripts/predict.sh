#!/bin/bash
# Method interface used by both evaluators (scripts/evaluate_train.sh and
# scripts/evaluate_test.sh):
#
#   bash scripts/predict.sh <input_dir> <output_dir>
#
# Reads <input_dir>/instances.json and must write <output_dir>/predictions.json
# (format in briefing/evaluation.md). Every method name in predictions.json is
# scored. Replace the command below to submit a different method.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

python3 -m method.predict "$1" "$2"
