#!/bin/bash
# Solve remaining AvalonLogs games + update scores.
# Processing order: smallest games first (fastest).
# Uses ALL_SETTINGS (5 CSP settings) for complete evaluation.

set -e
cd /home/user

echo "=== CSP4SDG: Solve remaining games + update scores ==="
echo "Start: $(date)"

# --- Step 1: Solve remaining games ---
python3 << 'PYEOF'
import sys, json, time
from pathlib import Path
import multiprocessing as mp

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, ALL_SETTINGS

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

all_files = sorted(in_dir.glob("*_constraints.json"))
dst_stems = {f.stem for f in out_dir.glob("*_constraints_solve.json")}
unsolved = [f for f in all_files if f.stem not in dst_stems]

print(f"Total: {len(all_files)} files, {len(dst_stems)} done, {len(unsolved)} to solve")

# Sort by player count (smallest first = fastest)
def get_n_players(fp):
    try:
        return len(json.loads(fp.read_text()).get('players', []))
    except:
        return 99

unsolved.sort(key=get_n_players)
print(f"Sorted by size (smallest first)")

# Time estimate
def estimate_time(fps):
    if not fps: return 0
    sample = fps[:min(10, len(fps))]
    total = 0
    for fp in sample:
        t0 = time.time()
        try:
            solve_one(fp, settings=ALL_SETTINGS[:2])
            total += time.time() - t0
        except:
            pass
    if not total: return 0
    avg = total / len(sample)
    return avg * len(fps)

if unsolved:
    est = estimate_time(unsolved)
    print(f"Estimated time: {est/60:.0f} min for remaining games")

# Time budget: run for up to 50 minutes
TIME_BUDGET = 50 * 60  # 50 minutes

t0_total = time.time()
solved = errors = 0
for fp in unsolved:
    elapsed = time.time() - t0_total
    if elapsed > TIME_BUDGET:
        print(f"Time budget exhausted ({elapsed/60:.0f}m), stopping")
        break

    dst = out_dir / (fp.stem + "_constraints_solve.json")
    if dst.exists():
        solved += 1
        continue

    try:
        result = solve_one(fp, settings=ALL_SETTINGS)
        # Write compact (no indentation) for speed
        dst.write_text(json.dumps(result), encoding="utf-8")
        solved += 1
        elapsed = time.time() - t0_total
        rate = solved / elapsed if elapsed > 0 else 0
        if solved % 100 == 0:
            remaining = len(unsolved) - solved
            eta = remaining / rate / 60 if rate > 0 else 0
            print(f"  {solved}/{len(unsolved)} ({rate:.1f}/s, ETA: {eta:.0f}m, elapsed: {elapsed/60:.0f}m)")
    except Exception as e:
        errors += 1
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

echo "=== Complete at \$(date) ==="
