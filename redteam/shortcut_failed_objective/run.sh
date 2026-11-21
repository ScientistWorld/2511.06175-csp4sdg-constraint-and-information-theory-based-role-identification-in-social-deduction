#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_failed_objective > redteam/shortcut_failed_objective/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_failed_objective/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_failed_objective/scores_test.json
