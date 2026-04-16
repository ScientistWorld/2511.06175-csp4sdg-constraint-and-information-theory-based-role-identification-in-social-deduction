#!/bin/bash
# Re-solve ALL AvalonLogs games with fixed IG computation (conditional predicates).
# The IG fix ensures hypothesis weights match the paper's formulation.
set -e
cd /home/user

echo "=== CSP4SDG: Re-solve ALL games with fixed IG computation ==="
echo "Start: $(date)"

# --- Step 1: Clear old solve results (IG weights were computed incorrectly) ---
echo "Clearing old solve results..."
rm -rf data/avalonlogs_solve/*
echo "Cleared."

# --- Step 2: Re-solve all games with the fixed solver ---
python3 << 'PYEOF'
import sys, json, time
from pathlib import Path

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, ALL_SETTINGS

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

all_files = sorted(in_dir.glob("*_constraints.json"))

# Sort by player count (smallest first = fastest)
def get_n_players(fp):
    try:
        return len(json.loads(fp.read_text()).get('players', []))
    except:
        return 99

all_files.sort(key=get_n_players)

from collections import Counter
sizes = Counter(get_n_players(f) for f in all_files)
for sz in sorted(sizes):
    print(f"  {sz}p: {sizes[sz]} games")
print(f"Total: {len(all_files)} games")

# Time budget: 20 hours (leaving margin)
TIME_BUDGET = 20 * 60 * 60

t0_total = time.time()
solved = errors = 0
for fp in all_files:
    elapsed = time.time() - t0_total
    if elapsed > TIME_BUDGET:
        print(f"Time budget exhausted ({elapsed/60:.0f}m), stopping")
        break

    dst = out_dir / (fp.stem + "_solve.json")
    if dst.exists():
        solved += 1
        continue

    try:
        result = solve_one(fp, settings=ALL_SETTINGS)
        dst.write_text(json.dumps(result), encoding="utf-8")
        solved += 1
        elapsed = time.time() - t0_total
        if solved % 100 == 0:
            rate = solved / elapsed if elapsed > 0 else 0
            remaining = len(all_files) - solved
            eta = remaining / rate / 60 if rate > 0 else 0
            print(f"  {solved}/{len(all_files)} ({rate:.1f}/s, ETA: {eta:.0f}m, elapsed: {elapsed/60:.0f}m)", flush=True)
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0_total
print(f"Solved {solved} games, {errors} errors in {elapsed/60:.1f}m")
PYEOF

echo "Solving complete. Updating scores..."

# --- Step 3: Update scores using evaluator ---
python3 -c "
import sys
sys.path.insert(0, '/home/user')
from eval.evaluator import evaluate
from pathlib import Path

scores = evaluate(
    results_dir=Path('data/avalonlogs_solve'),
    output_path=Path('scoring/scores.json'),
    dataset='avalonlogs',
    condition='Truth',
)
print('Scores updated.')
print('Experiments:', list(scores.get('experiments', {}).keys()))

# Print summary
for exp_name, exp_data in scores.get('experiments', {}).items():
    print(f'\n--- {exp_name} ---')
    for method, metrics in exp_data.get('results', {}).items():
        obj = metrics.get('Obj_marginal', 'N/A')
        mrl = metrics.get('MRL_marginal', 'N/A')
        print(f'  {method}: Obj={obj}, MRL={mrl}')
"

echo "=== Complete at $(date) ==="
