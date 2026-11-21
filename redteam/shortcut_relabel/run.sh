#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py shortcut_relabel > redteam/shortcut_relabel/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/shortcut_relabel/test.log 2>&1
cp scoring/scores_test.json redteam/shortcut_relabel/scores_test.json
