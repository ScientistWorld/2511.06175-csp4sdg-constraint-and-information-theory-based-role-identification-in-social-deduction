#!/bin/bash
set -euo pipefail
cd /home/user
python3 redteam/harness.py restore
cp redteam/shortcut_unregistered_better_method/scores_test.json redteam/shortcut_unregistered_better_method/scores_test_before_visibility.json
bash redteam/reference/run.sh
bash redteam/shortcut_unregistered_better_method/run.sh
python3 - <<'PY'
import json
from pathlib import Path
p = Path('redteam/shortcut_unregistered_better_method')
a = json.loads((p/'scores_test_before_visibility.json').read_text())
b = json.loads((p/'scores_test.json').read_text())
assert a == b, 'Explicit visible whitelist changes shortcut result'
print('Explicit scientist-created whitelist reproduces the saved empty result.')
print(Path('redteam/reference/whitelist_visibility_check.json').read_text())
PY
python3 redteam/analyze.py
