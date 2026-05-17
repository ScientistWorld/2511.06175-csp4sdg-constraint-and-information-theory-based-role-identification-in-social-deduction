#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script evaluates CSP solver results against the paper's reported numbers.
#
# Usage:
#   ./evaluate.sh [dataset] [results_dir] [output_path]
#
# Arguments (all optional, with defaults):
#   dataset     — "avalonlogs" (default), "avalonnlu", "mafia"
#   results_dir — Directory containing solver output JSON files (default: data/avalonlogs_solve)
#   output_path — Where to write scores.json (default: scoring/scores.json)
#
# Environment:
#   PYTHONPATH should include /home/user

set -e

cd /home/user

# Default paths
DATASET="${1:-avalonlogs}"
RESULTS_DIR="${2:-data/avalonlogs_solve}"
OUTPUT="${3:-scoring/scores.json}"

mkdir -p scoring

echo "Evaluating: dataset=$DATASET, results=$RESULTS_DIR, output=$OUTPUT"

python3 -c "
import sys
sys.path.insert(0, '/home/user')
from eval.evaluator import evaluate
from pathlib import Path

scores = evaluate(
    results_dir=Path('$RESULTS_DIR'),
    output_path=Path('$OUTPUT'),
    dataset='$DATASET',
    condition='Truth',
)
print('Evaluation complete.')
print('Experiments:', list(scores.get('experiments', {}).keys()))
"

echo "Scores written to $OUTPUT"
