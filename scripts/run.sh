#!/bin/bash
# Job script for CSP4SDG reproduction
#
# Processes AvalonLogs, runs CSP solver, and evaluates results.
# Filters to 6-8 player games for reasonable compute time.

set -e

cd /home/user

echo "=== CSP4SDG Reproduction Job ==="
echo "Start time: $(date)"

# Step 1: Convert all raw AvalonLogs to constraints
echo "[1/5] Converting raw data to CSP constraints..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
import json
import random
from pathlib import Path
from data.convert_avalonlogs import convert_file

raw_dir = Path("data/avalonlogs_raw")
out_dir = Path("data/avalonlogs_constraints")
out_dir.mkdir(parents=True, exist_ok=True)

files = [fp for fp in raw_dir.iterdir() if fp.is_file()]
print(f"Processing {len(files)} raw files...")

converted = 0
skipped = 0
for fp in files:
    dst = out_dir / (fp.stem + "_constraints.json")
    if dst.exists():
        skipped += 1
        continue
    result = convert_file(fp)
    if result is None:
        continue
    dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
    converted += 1
    if converted % 2000 == 0:
        print(f"  Converted {converted}...")

print(f"Converted {converted} new files ({skipped} already existed)")
PYEOF

# Step 2: Filter to 6-8 player games (fast to solve)
echo "[2/5] Identifying 6-8 player games..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
import json
from pathlib import Path

in_dir = Path("data/avalonlogs_constraints")
solve_dir = Path("data/avalonlogs_solve")
solve_dir.mkdir(parents=True, exist_ok=True)

six_eight = []
for fp in in_dir.glob("*_constraints.json"):
    if (solve_dir / (fp.stem + "_solve.json")).exists():
        continue
    try:
        with open(fp) as f:
            game = json.load(f)
        n_players = len(game.get("players", []))
        if 6 <= n_players <= 8:
            six_eight.append(str(fp))
    except Exception:
        pass

print(f"Found {len(six_eight)} unsolve 6-8-player games")
with open("/tmp/solve_queue.txt", "w") as f:
    f.write("\n".join(six_eight))
PYEOF

# Step 3: Solve 6-8 player games
echo "[3/5] Solving CSP for 6-8 player games..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
import json
import time
from pathlib import Path
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

solve_dir = Path("data/avalonlogs_solve")
solve_dir.mkdir(parents=True, exist_ok=True)

with open("/tmp/solve_queue.txt") as f:
    queue_files = [Path(line.strip()) for line in f if line.strip()]

print(f"Solving {len(queue_files)} games with {[s[0] for s in QUICK_SETTINGS]}...")
t0 = time.time()
solved = 0
errors = 0
for fp in queue_files:
    dst = solve_dir / (fp.stem + "_solve.json")
    if dst.exists():
        solved += 1
        continue
    try:
        result = solve_one(fp, settings=QUICK_SETTINGS)
        dst.write_text(json.dumps(result), encoding="utf-8")
        solved += 1
        if solved % 500 == 0:
            elapsed = time.time() - t0
            rate = solved / elapsed
            eta = (len(queue_files) - solved) / rate if rate > 0 else 0
            print(f"  Solved {solved}/{len(queue_files)} ({rate:.1f}/s, ETA: {eta/60:.1f}m)")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0
print(f"Solved {solved} games in {elapsed/60:.1f}m ({solved/elapsed:.2f}/s), {errors} errors")
PYEOF

# Step 4: Evaluate
echo "[4/5] Evaluating results..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
import json
from collections import defaultdict
from pathlib import Path

solve_dir = Path("data/avalonlogs_solve")
out_file = Path("scoring/scores.json")
out_file.parent.mkdir(parents=True, exist_ok=True)

ROLE_MAP = {
    "merlin": "MRL", "percival": "PCV", "morgana": "MRG",
    "servant": "LSV", "loyal_follower": "LSV", "loyal_servant": "LSV",
    "assassin": "ASN", "evil_minion": "EVM", "evil-minion": "EVM",
    "mordred": "EVM", "oberon": "EVM",
}

by_size = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

for fp in solve_dir.glob("*_solve.json"):
    try:
        with open(fp) as f:
            game = json.load(f)
    except Exception:
        continue

    n_players = len(game.get("players", {}))
    truth = game.get("players", {})

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            for setting, data in settings.items():
                post = data.get("posterior", {})
                best = data.get("best", {})
                if not post:
                    continue

                P = len(truth)
                marg = sum(post.get(p, {}).get(r, 0.0) for p, r in truth.items()) / P
                correct = sum(1 for p, r in truth.items() if best.get(p) == r)
                map_acc = correct / P

                canonical_view = ROLE_MAP.get(view.lower(), view)
                by_size[n_players][setting][canonical_view]["marg"].append(marg)
                by_size[n_players][setting][canonical_view]["map"].append(map_acc)

scores = {"experiments": {}}
for size, settings_data in sorted(by_size.items()):
    for setting, views_data in settings_data.items():
        exp_name = f"avalonlogs_{size}p_{setting.lower().replace('+', 'plus')}"
        scores["experiments"][exp_name] = {
            "description": f"AvalonLogs {size}-player CSP {setting}",
            "results": {}
        }
        method_name = f"CSP_{setting}"
        scores["experiments"][exp_name]["results"][method_name] = {}

        for view, m in views_data.items():
            if m["marg"]:
                scores["experiments"][exp_name]["results"][method_name][f"{view.lower()}_marginal"] = round(sum(m["marg"]) / len(m["marg"]), 4)
            if m["map"]:
                scores["experiments"][exp_name]["results"][method_name][f"{view.lower()}_map"] = round(sum(m["map"]) / len(m["map"]), 4)
            scores["experiments"][exp_name]["results"][method_name]["n_games"] = len(m["marg"])

out_file.write_text(json.dumps(scores, indent=2), ensure_ascii=False)
print(f"Scores written to {out_file}")
print(f"Experiments: {list(scores['experiments'].keys())}")
PYEOF

# Step 5: Compare with reference
echo "[5/5] Comparing with paper's reference..."
python3 << 'PYEOF'
import json
from pathlib import Path

ref_path = Path("scoring/reference.json")
score_path = Path("scoring/scores.json")

with open(ref_path) as f:
    ref = json.load(f)
with open(score_path) as f:
    scores = json.load(f)

print("\n=== Paper vs Reproduced (AvalonLogs) ===")
for exp_name, exp in scores.get("experiments", {}).items():
    for ref_name, ref_exp in ref["experiments"].items():
        if "avalonlogs" not in ref_name.lower():
            continue
        ref_methods = ref_exp.get("results", {})
        for method, vals in exp.get("results", {}).items():
            for ref_method, ref_vals in ref_methods.items():
                if "CSP" in method and "CSP" in ref_method:
                    primary = ref_exp.get("primary_metric", "")
                    if primary and primary in vals:
                        rep = vals[primary]
                        pap = ref_vals.get(primary)
                        if pap is not None:
                            diff = rep - pap
                            print(f"{exp_name} {method}: reproduced={rep:.4f} paper={pap:.4f} diff={diff:+.4f}")
                    break
                break
        break

print("\nDone at:", end=" ")
import datetime
print(datetime.datetime.now())
PYEOF

echo "=== Job Complete ==="
