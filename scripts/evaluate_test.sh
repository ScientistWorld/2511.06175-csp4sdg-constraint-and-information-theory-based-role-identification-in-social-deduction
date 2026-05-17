#!/bin/bash
# Evaluate the held-out test slice of pre-generated method outputs.
#
# Usage:
#   ./evaluate_test.sh [dataset] [results_dir] [output_path]
#
# Arguments mirror scripts/evaluate.sh:
#   dataset     - "avalonlogs" (default), "avalonnlu", "mafia"
#   results_dir - Directory containing solver output JSON files (default: data/avalonlogs_solve)
#   output_path - Where to write scores_test.json (default: scoring/scores_test.json)
#
set -e

cd /home/user

DATASET="${1:-avalonlogs}"
RESULTS_DIR="${2:-data/avalonlogs_solve}"
OUTPUT="${3:-scoring/scores_test.json}"
CONDITION="${CONDITION:-Truth}"

mkdir -p scoring

echo "Evaluating test slice: dataset=$DATASET, results=$RESULTS_DIR, output=$OUTPUT"

python3 eval/test/evaluate.py \
  --dataset "$DATASET" \
  --condition "$CONDITION" \
  --results-dir "$RESULTS_DIR" \
  --output "$OUTPUT"

echo "Test scores written to $OUTPUT"
