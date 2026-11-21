#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py better_knowledge > redteam/better_knowledge/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/better_knowledge/test.log 2>&1
cp scoring/scores_test.json redteam/better_knowledge/scores_test.json
