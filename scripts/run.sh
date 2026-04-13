#!/bin/bash
# Solve all remaining AvalonLogs games and update scores.
# Data: ~7741 already solved, ~4653 to solve.
# Quick settings (Strict + HypIG) cover all 6 player sizes.

set -e
cd /home/user

echo "=== CSP4SDG: Full Dataset Solve ==="
echo "Start: $(date)"

# Count what's already done
ALREADY=$(ls data/avalonlogs_solve/*_solve.json 2>/dev/null | wc -l)
CONSTRAINTS=$(ls data/avalonlogs_constraints/*_constraints.json 2>/dev/null | wc -l)
echo "Already solved: $ALREADY / $CONSTRAINTS constraints"

# Solve all remaining with quick settings (Strict + HypIG)
python3 << 'PYEOF'
import sys, json, time
sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS
from pathlib import Path

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

files = list(in_dir.glob("*_constraints.json"))
print(f"Total: {len(files)} constraint files")

solved = skipped = errors = 0
t0 = time.time()
for fp in files:
    dst = out_dir / (fp.stem + "_solve.json")
    if dst.exists():
        skipped += 1
        continue
    try:
        result = solve_one(fp, settings=QUICK_SETTINGS)
        dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
        solved += 1
        if solved % 1000 == 0:
            elapsed = time.time() - t0
            rate = solved / elapsed if elapsed > 0 else 0
            eta = (len(files) - solved - skipped) / rate if rate > 0 else 0
            print(f"  {solved} solved, {skipped} skip, ETA: {eta/60:.0f}m")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0
print(f"Done. Solved: {solved}, Skipped: {skipped}, Errors: {errors} in {elapsed/60:.1f}m")
PYEOF

# Evaluate all solved games
echo "=== Evaluating all solved games ==="
python3 << 'PYEOF'
import sys, json, re
from pathlib import Path
from collections import defaultdict

results_dir = Path('data/avalonlogs_solve')
score_path = Path('scoring/scores.json')

# Collect per-game metrics
by_size = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for fp in sorted(results_dir.glob("*_solve.json")):
    try:
        with open(fp, encoding="utf-8") as f:
            game = json.load(f)
    except Exception:
        continue

    truth = game.get("players", {})
    n_players = len(truth)
    if n_players == 0:
        continue

    def canon(v):
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
            cv = canon(view)
            if cv in ("unknown", "obj") and view.lower() != "objective":
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

# Build scores structure
VALID_SIZES = {5: "avalonlogs_5player", 6: "avalonlogs_6player",
               7: "avalonlogs_7player", 8: "avalonlogs_8player",
               9: "avalonlogs_9player", 10: "avalonlogs_10player"}
VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM"}

scores = {"experiments": {}, "metadata": {"dataset": "avalonlogs", "condition": "Truth"}}

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

        obj_marg = by_size[size].get("Strict", {}).get("Obj", [])
        if obj_marg:
            obj_avg = round(sum(v[0] for v in obj_marg) / len(obj_marg), 4)
            scores["experiments"][exp_name]["results"][mname]["Obj_marginal"] = obj_avg

with open(score_path, "w") as f:
    json.dump(scores, f, indent=2)

print(f"Scores written: {list(scores['experiments'].keys())}")
for exp, data in scores["experiments"].items():
    n_games = sum(len(list(results_dir.glob("*_solve.json"))) for _ in [1])
    for mname, vals in data["results"].items():
        marginals = {k: round(v, 3) for k, v in vals.items() if k.endswith("_marginal")}
        print(f"  {exp} / {mname}: {marginals}")
PYEOF

echo "=== Complete at $(date) ==="
