#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_empty_map > redteam/shortcut_empty_map/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_empty_map/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_empty_map/scores_test.json
