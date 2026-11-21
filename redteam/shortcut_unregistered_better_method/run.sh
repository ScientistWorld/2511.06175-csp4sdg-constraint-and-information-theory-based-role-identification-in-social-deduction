#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_unregistered_better_method > redteam/shortcut_unregistered_better_method/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_unregistered_better_method/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_unregistered_better_method/scores_test.json
