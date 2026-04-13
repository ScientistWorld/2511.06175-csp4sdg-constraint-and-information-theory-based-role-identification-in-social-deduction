#!/bin/bash
# Solve remaining AvalonLogs games and update scores.
# ~4335 games remaining (8059 solved, 12394 total).
# Settings: Strict + HypIG (QUICK_SETTINGS).

set -e
cd /home/user

echo "=== CSP4SDG: Solve remaining games + update scores ==="
echo "Start: $(date)"

# --- Step 1: Solve remaining games ---
python3 << 'PYEOF'
import sys, json, time, re
sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS
from pathlib import Path

in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

files = list(in_dir.glob("*_constraints.json"))
print(f"Total constraint files: {len(files)}")

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
            remaining = len(files) - solved - skipped
            eta = remaining / rate if rate > 0 else 0
            print(f"  {solved} solved, {skipped} skip, {remaining} remaining, ETA: {eta/60:.0f}m")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0
print(f"Solve done. Solved: {solved}, Skipped: {skipped}, Errors: {errors} in {elapsed/60:.1f}m")
PYEOF

# --- Step 2: Update scores.json ---
python3 << 'PYEOF'
import json, re
from pathlib import Path
from collections import defaultdict

results_dir = Path("data/avalonlogs_solve")
score_path = Path("scoring/scores.json")

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

VALID_VIEWS = {"MRL", "PCV", "MRG", "LSV", "EVM"}
SIZE_TO_EXP = {5: "avalonlogs_5player", 6: "avalonlogs_6player",
               7: "avalonlogs_7player", 8: "avalonlogs_8player",
               9: "avalonlogs_9player", 10: "avalonlogs_10player"}

by_size = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for fp in sorted(results_dir.glob("*_solve.json")):
    try:
        game = json.loads(fp.read_text())
    except:
        continue
    truth = game.get("players", {})
    n_players = len(truth)
    if n_players == 0:
        continue
    for q_idx, quests in game.get("quests", {}).items():
        for view, settings in quests.items():
            cv = canon(view)
            if cv in ("unknown", "obj") and view.lower() != "objective":
                continue
            for setting, data in settings.items():
                post = data.get("posterior", {})
                if not post:
                    continue
                marg = sum(post.get(p, {}).get(r, 0.0) for p, r in truth.items()) / n_players
                by_size[n_players][setting][cv].append(marg)

# Build scores (no "type" field)
scores = {"experiments": {}, "metadata": {"dataset": "avalonlogs", "condition": "Truth"}}

for size, settings_data in sorted(by_size.items()):
    exp_name = SIZE_TO_EXP.get(size)
    if exp_name is None:
        continue
    scores["experiments"][exp_name] = {"results": {}}
    for setting, views_data in sorted(settings_data.items()):
        setting_clean = setting.replace("+", "")
        mname = f"CSP_{setting_clean}"
        scores["experiments"][exp_name]["results"][mname] = {}
        for view, vals in views_data.items():
            if view not in VALID_VIEWS or not vals:
                continue
            avg_marg = round(sum(vals) / len(vals), 4)
            scores["experiments"][exp_name]["results"][mname][f"{view}_marginal"] = avg_marg
        obj_marg = by_size[size].get("Strict", {}).get("Obj", [])
        if obj_marg:
            obj_avg = round(sum(obj_marg) / len(obj_marg), 4)
            scores["experiments"][exp_name]["results"][mname]["Obj_marginal"] = obj_avg

with open(score_path, "w") as f:
    json.dump(scores, f, indent=2)

print(f"Scores updated: {list(scores['experiments'].keys())}")
for exp, data in sorted(scores["experiments"].items()):
    for mname, vals in sorted(data["results"].items()):
        marginals = {k: round(v, 3) for k, v in vals.items() if k.endswith("_marginal")}
        print(f"  {exp} / {mname}: {marginals}")

# Print game counts
for size in sorted(SIZE_TO_EXP.keys()):
    count = len([fp for fp in results_dir.glob("*_solve.json")
                 if fp.stat().st_size > 0 and
                 len(json.loads(fp.read_text()).get("players", {})) == size])
    exp_name = SIZE_TO_EXP[size]
    if exp_name in scores["experiments"]:
        print(f"  {size}-player: {count} games solved")
PYEOF

echo "=== Complete at $(date) ==="
