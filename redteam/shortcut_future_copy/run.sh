#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_future_copy > redteam/shortcut_future_copy/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_future_copy/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_future_copy/scores_test.json
