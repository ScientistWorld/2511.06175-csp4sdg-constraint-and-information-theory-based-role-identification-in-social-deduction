#!/bin/bash
# Solve all remaining AvalonLogs games — focus on completing 9-player games,
# then expand evaluation to 5, 7, 8, 10-player sizes for broader coverage.

set -e

cd /home/user

echo "=== CSP4SDG: Solve remaining games ==="
echo "Start time: $(date)"

# Check what we have
N_SOLVED=$(ls data/avalonlogs_solve/*_solve.json 2>/dev/null | wc -l)
N_CONSTRAINTS=$(ls data/avalonlogs_constraints/*_constraints.json 2>/dev/null | wc -l)
echo "Already solved: $N_SOLVED"
echo "Constraint files: $N_CONSTRAINTS"

# Count by player size from existing solved files
echo ""
echo "=== Existing solved distribution ==="
for size in 5 6 7 8 9 10; do
    count=$(ls data/avalonlogs_solve/*_solve.json 2>/dev/null | wc -l)
    # Count from constraints by player size (sample)
done

# Solve ALL remaining unsolved games with quick settings (Strict + HypIG)
# This covers all player sizes
echo ""
echo "[1/2] Solving all remaining games with quick settings..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS
from pathlib import Path
import json

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

files = list(in_dir.glob("*_constraints.json"))
print(f"Total constraint files: {len(files)}")

# Count by player size
from collections import Counter
size_counts = Counter()
for fp in files:
    try:
        game = json.loads(fp.read_text(encoding="utf-8"))
        size = len(game.get("players", []))
        size_counts[size] += 1
    except:
        size_counts[0] += 1

print("Games by player count:")
for size in sorted(size_counts.keys()):
    if size > 0:
        print(f"  {size}-player: {size_counts[size]}")

solved = 0
skipped = 0
errors = 0
import time
t0 = time.time()

for fp in files:
    dst = out_dir / (fp.stem + "_solve.json")
    if dst.exists():
        skipped += 1
        continue
    try:
        result = solve_one(fp, settings=QUICK_SETTINGS, verbose=False)
        dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
        solved += 1
        if solved % 500 == 0:
            elapsed = time.time() - t0
            rate = solved / elapsed if elapsed > 0 else 0
            remaining = len(files) - solved - skipped
            eta = remaining / rate if rate > 0 else 0
            print(f"  Solved {solved}/{len(files)} (rate: {rate:.1f}/s, ETA: {eta/60:.0f}m)")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  ERROR {fp.name}: {type(e).__name__}: {e}")

elapsed = time.time() - t0
print(f"\nSolved {solved} new games, {skipped} skipped, {errors} errors in {elapsed/60:.1f}m")
print(f"Solved {solved/elapsed:.1f}/s" if elapsed > 0 else "Done")
PYEOF

# Step 2: Update scores.json with all available sizes
echo ""
echo "[2/2] Updating scores with all player sizes..."
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/home/user')
from eval.evaluator import evaluate
from pathlib import Path

# Evaluate all solved games
scores = evaluate(
    results_dir=Path('data/avalonlogs_solve'),
    output_path=Path('scoring/scores.json'),
    dataset='avalonlogs',
    condition='Truth',
)
print("Evaluation complete.")
for exp, data in scores['experiments'].items():
    n_games = sum(1 for fp in Path('data/avalonlogs_solve').glob('*_solve.json')
                  if exp.replace('avalonlogs_','') in fp.name or
                     len(json.loads(fp.read_text())['players']) == int(exp.replace('avalonlogs_','')))
    print(f"  {exp}: {list(data['results'].keys())}")
PYEOF

# Also update the experiment mapping to include all sizes
python3 << 'PYEOF'
import json
import re
from pathlib import Path
from collections import defaultdict

results_dir = Path('data/avalonlogs_solve')
score_path = Path('scoring/scores.json')

# Load current scores
with open(score_path) as f:
    scores = json.load(f)

# Collect per-game metrics, keyed by (player_count, setting, view)
by_size = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for fp in sorted(results_dir.glob("*_solve.json")):
    try:
        with open(fp, encoding="utf-8") as f:
            game = json.load(f)
    except Exception:
        continue

    truth = game.get("players", {})
    n_players = len(truth)

    def canonicalize(v):
        v2 = v.lower()
        stripped = re.sub(r'\d+$', '', v2)
        if stripped in ("merlin",): return "MRL"
        if stripped in ("percival",): return "PCV"
        if stripped in ("morgana",): return "MRG"
        if stripped in ("servant", "loyal_follower", "loyal_servant"): return "LSV"
        if stripped in ("assassin",): return "ASN"
        if stripped in ("evil_minion", "evil-minion", "mordred", "oberon"): return "EVM"
        if stripped in ("objective",): return "Obj"
        return stripped

    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            cv = canonicalize(view)
            if cv == "unknown" or cv == "obj":
                continue

            for setting, data in settings.items():
                post = data.get("posterior", {})
                if not post:
                    continue
                P = len(truth)
                marg = sum(post.get(p, {}).get(r, 0.0) for p, r in truth.items()) / P
                best = data.get("best", {})
                correct = sum(1 for p, r in truth.items() if best.get(p) == r)
                map_acc = correct / P
                by_size[n_players][setting][cv].append((marg, map_acc))

# Map player sizes to experiment names
VALID_SIZES = {5: "avalonlogs_5player", 6: "avalonlogs_6player",
               7: "avalonlogs_7player", 8: "avalonlogs_8player",
               9: "avalonlogs_9player", 10: "avalonlogs_10player"}

VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM"}

for size, settings_data in sorted(by_size.items()):
    exp_name = VALID_SIZES.get(size)
    if exp_name is None:
        continue

    scores["experiments"][exp_name] = {"description": f"AvalonLogs {size}-player CSP results", "results": {}}

    for setting, views_data in settings_data.items():
        setting_clean = setting.replace("+", "")
        mname = f"CSP_{setting_clean}"

        scores["experiments"][exp_name]["results"][mname] = {}

        for view, vals in views_data.items():
            if view not in VALID_VIEWS:
                continue
            if not vals:
                continue
            margs = [v[0] for v in vals]
            avg_marg = round(sum(margs) / len(margs), 4)
            scores["experiments"][exp_name]["results"][mname][f"{view}_marginal"] = avg_marg

        # Add Obj_marginal
        obj_marg = by_size[size].get("Strict", {}).get("Obj", [])
        if obj_marg:
            obj_avg = round(sum(v[0] for v in obj_marg) / len(obj_marg), 4)
            scores["experiments"][exp_name]["results"][mname]["Obj_marginal"] = obj_avg

with open(score_path, "w") as f:
    json.dump(scores, f, indent=2)

print(f"Scores updated with all player sizes: {list(scores['experiments'].keys())}")

# Print summary
for exp, data in scores["experiments"].items():
    n_results = len(data["results"])
    print(f"  {exp}: {n_results} methods")
    for mname, vals in data["results"].items():
        marginals = {k: round(v, 3) for k, v in vals.items() if k.endswith("_marginal")}
        print(f"    {mname}: {marginals}")
PYEOF

echo "=== Complete at $(date) ==="
