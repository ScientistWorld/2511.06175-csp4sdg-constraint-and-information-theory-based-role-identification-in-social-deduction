#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py weaker_no_hypotheses > redteam/weaker_no_hypotheses/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/weaker_no_hypotheses/test.log 2>&1
cp scoring/scores_test.json redteam/weaker_no_hypotheses/scores_test.json
