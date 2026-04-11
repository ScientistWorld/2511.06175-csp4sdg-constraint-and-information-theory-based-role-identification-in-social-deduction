#!/bin/bash
# Job script for CSP4SDG reproduction
#
# This script evaluates already-solved AvalonLogs games and produces scores.json.
# Data conversion and CSP solving should have been done previously.
# Expected: data/avalonlogs_constraints/ and data/avalonlogs_solve/ populated.

set -e

cd /home/user

echo "=== CSP4SDG Evaluation ==="
echo "Start time: $(date)"

# Check what we have
N_CONSTRAINTS=$(ls data/avalonlogs_constraints/*_constraints.json 2>/dev/null | wc -l)
N_SOLVED=$(ls data/avalonlogs_solve/*_solve.json 2>/dev/null | wc -l)
echo "Constraint files: $N_CONSTRAINTS"
echo "Solved games: $N_SOLVED"

# Step 1: Evaluate all solved games and produce scores.json
echo "[1/1] Evaluating results..."
python3 -c "
import sys
sys.path.insert(0, '.')
from eval.evaluator import evaluate
from pathlib import Path

scores = evaluate(
    results_dir=Path('data/avalonlogs_solve'),
    output_path=Path('scoring/scores.json'),
    dataset='avalonlogs',
    condition='Truth',
)
print('Evaluation complete.')
for exp, data in scores['experiments'].items():
    print(f'  {exp}:')
    for method, vals in data['results'].items():
        marginals = {k: round(v,3) for k,v in vals.items() if k.endswith('_marginal')}
        print(f'    {method}: {marginals}')
"

echo "=== Job Complete at $(date) ==="
