#!/bin/bash
# Iteration-11 job: hardening audit, then the reference end to end.
# (After this job, run.sh goes back to the reference-only version.)
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring logs outputs

echo "=== iteration-11 audit ($(date)) nproc=$(nproc) user=$(id -u)"
bash redteam/iter11/audit.sh 2>&1 | tee redteam/iter11/audit.log
find redteam/iter11/runs -name 'per_instance*.json' -delete
rm -f redteam/iter11/runs/reference/instance_cells.json

echo "=== CSP4SDG AvalonLogs reference run ($(date))"
bash scripts/evaluate.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
bash scripts/baseline.sh
cp outputs/baseline_prior_train.json redteam/iter11/baseline_prior_train.json
python3 validate.py --post-design
echo "=== done ($(date))"
