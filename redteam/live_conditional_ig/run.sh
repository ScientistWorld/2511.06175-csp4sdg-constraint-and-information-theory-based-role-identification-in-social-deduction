#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py live_conditional_ig > redteam/live_conditional_ig/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/live_conditional_ig/test.log 2>&1
cp scoring/scores_test.json redteam/live_conditional_ig/scores_test.json
