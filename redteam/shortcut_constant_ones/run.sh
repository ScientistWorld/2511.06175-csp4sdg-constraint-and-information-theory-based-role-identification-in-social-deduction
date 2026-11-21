#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_constant_ones > redteam/shortcut_constant_ones/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_constant_ones/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_constant_ones/scores_test.json
