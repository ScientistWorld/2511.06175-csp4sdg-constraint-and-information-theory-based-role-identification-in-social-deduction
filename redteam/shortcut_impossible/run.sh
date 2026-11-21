#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_impossible > redteam/shortcut_impossible/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_impossible/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_impossible/scores_test.json
