#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py reference_seed_2 > redteam/reference_seed_2/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/reference_seed_2/test.log 2>&1
cp scoring/scores_test.json redteam/reference_seed_2/scores_test.json
