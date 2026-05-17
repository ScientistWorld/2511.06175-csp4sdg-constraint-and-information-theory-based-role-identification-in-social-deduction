#!/bin/bash
# Score the ResearchGym train/test split over the existing final AvalonLogs
# method outputs. This is post-hoc scoring only; it does not retrain or rerun
# the method solver.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== ResearchGym split evaluation ==="
echo "Start: $(date)"

mkdir -p scoring logs

bash scripts/evaluate_train.sh avalonlogs data/avalonlogs_solve scoring/scores_train.json
bash scripts/evaluate_test.sh avalonlogs data/avalonlogs_solve scoring/scores_test.json

echo "Train/test split scoring complete"
echo "End: $(date)"
