#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_replace_method > redteam/shortcut_replace_method/install.log 2>&1
set +e
python3 method/avalon_logs_solver.py > redteam/shortcut_replace_method/shortcut_method_failure.log 2>&1
status=$?
set -e
printf '%s\n' "$status" > redteam/shortcut_replace_method/shortcut_method_exit_code.txt
bash scripts/evaluate_test.sh > redteam/shortcut_replace_method/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_replace_method/scores_test.json
