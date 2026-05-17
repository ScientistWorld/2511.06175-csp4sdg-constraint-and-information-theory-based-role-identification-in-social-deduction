#!/bin/bash
# Evaluate the visible train slice of pre-generated method outputs.
#
# Usage:
#   ./evaluate_train.sh [dataset] [results_dir] [output_path]
#
# Arguments mirror scripts/evaluate.sh:
#   dataset     - "avalonlogs" (default), "avalonnlu", "mafia"
#   results_dir - Directory containing solver output JSON files (default: data/avalonlogs_solve)
#   output_path - Where to write scores_train.json (default: scoring/scores_train.json)

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DATASET="${1:-avalonlogs}"
RESULTS_DIR="${2:-data/avalonlogs_solve}"
OUTPUT="${3:-scoring/scores_train.json}"
CONDITION="${CONDITION:-Truth}"

mkdir -p scoring

echo "Evaluating train slice: dataset=$DATASET, results=$RESULTS_DIR, output=$OUTPUT"

python3 eval/train/evaluate.py \
  --dataset "$DATASET" \
  --condition "$CONDITION" \
  --results-dir "$RESULTS_DIR" \
  --output "$OUTPUT"

echo "Train scores written to $OUTPUT"
