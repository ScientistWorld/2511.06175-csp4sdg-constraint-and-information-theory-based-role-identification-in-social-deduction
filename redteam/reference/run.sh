#!/bin/bash
set -euo pipefail
cd /home/user
trap 'python3 redteam/harness.py restore' EXIT
python3 redteam/harness.py reference > redteam/reference/install.log 2>&1
bash scripts/evaluate_test.sh > redteam/reference/test.log 2>&1
cp scoring/scores_test.json redteam/reference/scores_test.json
# The scientist initially receives no scoring/scores.json. Establish that the
# supplied Strict/HypIG scores do not rely on a comparison whitelist. Other
# cached settings can legitimately appear once the filter is removed.
rm scoring/scores.json
bash scripts/evaluate_test.sh > redteam/reference/test_without_whitelist.log 2>&1
cp scoring/scores_test.json redteam/reference/scores_test_without_whitelist.json
python3 redteam/check_visibility.py
