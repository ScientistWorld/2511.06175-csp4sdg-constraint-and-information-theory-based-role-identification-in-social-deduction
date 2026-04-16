#!/bin/bash
# Solve remaining AvalonLogs games using the original (correct) solver.
# Processes smallest games first for maximum coverage within time budget.
set -e
cd /home/user

echo "=== CSP4SDG: Solve remaining games + update scores ==="
echo "Start: $(date)"

# --- Step 1: Solve remaining games ---
python3 << 'PYEOF'
import sys, json, time
from pathlib import Path

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, ALL_SETTINGS

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

# Find unsolved files
all_files = sorted(in_dir.glob("*_constraints.json"))
# Output naming: fp.stem + "_solve.json" (matching original solver convention)
solved_stems = {f.stem.replace("_solve", "") for f in out_dir.glob("*_solve.json")}
unsolved = [f for f in all_files if f.stem not in solved_stems]

print(f"Total: {len(all_files)} files, {len(solved_stems)} done, {len(unsolved)} to solve")

# Sort by player count (smallest first = fastest)
def get_n_players(fp):
    try:
        return len(json.loads(fp.read_text()).get('players', []))
    except:
        return 99

unsolved.sort(key=get_n_players)

# Count by size
from collections import Counter
sizes = Counter(get_n_players(f) for f in unsolved)
for sz in sorted(sizes):
    print(f"  {sz}p: {sizes[sz]} games")

# Time budget: 50 minutes
TIME_BUDGET = 50 * 60

t0_total = time.time()
solved = errors = 0
for fp in unsolved:
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
        if solved % 50 == 0:
            rate = solved / elapsed if elapsed > 0 else 0
            remaining = len(unsolved) - solved
            eta = remaining / rate / 60 if rate > 0 else 0
            print(f"  {solved}/{len(unsolved)} ({rate:.1f}/s, ETA: {eta:.0f}m, elapsed: {elapsed/60:.0f}m)")
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0_total
print(f"Solved {solved} games, {errors} errors in {elapsed/60:.1f}m")
PYEOF

echo "Solving complete. Updating scores..."

# --- Step 2: Update scores using evaluator ---
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
"

echo "=== Complete at $(date) ==="
