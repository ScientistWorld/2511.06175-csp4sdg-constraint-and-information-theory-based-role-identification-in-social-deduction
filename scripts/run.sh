#!/bin/bash
# Job script for CSP4SDG reproduction
#
# Processes AvalonLogs, runs CSP solver, and evaluates results.
# Filters to 6-8 player games for reasonable compute time.
# Expects data to already be downloaded and converted.

set -e

cd /home/user

echo "=== CSP4SDG Reproduction Job ==="
echo "Start time: $(date)"

# Step 1: Ensure all constraint files are converted (fast - ~30s)
echo "[1/5] Verifying constraint files..."
python3 << 'PYEOF'
import sys, json, time
sys.path.insert(0, '.')
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from data.convert_avalonlogs import convert_file

raw_dir = Path("data/avalonlogs_raw")
out_dir = Path("data/avalonlogs_constraints")
out_dir.mkdir(parents=True, exist_ok=True)

files = [fp for fp in raw_dir.iterdir() if fp.is_file()]
existing = set(f.stem for f in out_dir.glob("*_constraints.json"))
to_convert = [fp for fp in files if fp.stem not in existing]
print(f"Need to convert: {len(to_convert)} files")

if to_convert:
    done = 0
    def do_conv(fp):
        return fp, convert_file(fp)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(do_conv, fp): fp for fp in to_convert}
        for fut in as_completed(futures):
            fp, result = fut.result()
            if result is not None:
                dst = out_dir / (fp.stem + "_constraints.json")
                dst.write_text(json.dumps(result), encoding="utf-8")
                done += 1
    print(f"Converted {done} files in {time.time()-t0:.1f}s")

total = len(list(out_dir.glob("*_constraints.json")))
print(f"Total constraint files: {total}")
PYEOF

# Step 2: Identify 6-8 player games that need solving
echo "[2/5] Identifying 6-8 player games to solve..."
python3 << 'PYEOF'
import sys, json
sys.path.insert(0, '.')
from pathlib import Path

in_dir = Path("data/avalonlogs_constraints")
solve_dir = Path("data/avalonlogs_solve")
solve_dir.mkdir(parents=True, exist_ok=True)

already_solved = set(f.stem.replace("_solve", "") for f in solve_dir.glob("*_solve.json"))
queue = []
for fp in in_dir.glob("*_constraints.json"):
    if fp.stem in already_solved:
        continue
    try:
        with open(fp) as f:
            game = json.load(f)
        n = len(game.get("players", []))
        if 6 <= n <= 8:
            queue.append(str(fp.resolve()))
    except:
        pass

print(f"Games to solve: {len(queue)}")
with open("/tmp/solve_queue.txt", "w") as f:
    f.write("\n".join(queue))
PYEOF

# Step 3: Solve 6-8 player games (main compute step, ~4 hours)
echo "[3/5] Solving CSP for 6-8 player games..."
python3 << 'PYEOF'
import sys, json, time, math
sys.path.insert(0, '.')
from pathlib import Path
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

solve_dir = Path("data/avalonlogs_solve")
solve_dir.mkdir(parents=True, exist_ok=True)

with open("/tmp/solve_queue.txt") as f:
    queue = [Path(line.strip()) for line in f if line.strip()]

print(f"Solving {len(queue)} games with Strict and HypIG settings...")
t0 = time.time()
solved = 0
errors = 0
for fp in queue:
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
            eta = (len(queue) - solved) / rate if rate > 0 else 0
            print(f"  {solved}/{len(queue)} ({rate:.1f}/s, ETA: {eta/60:.0f}m)")
    except Exception as e:
        errors += 1
        if errors <= 3:
            print(f"  ERROR {fp.name}: {e}")

elapsed = time.time() - t0
print(f"Solved {solved} games in {elapsed/60:.1f}m ({solved/elapsed:.1f}/s), {errors} errors")
PYEOF

# Step 4: Evaluate and write scores.json
echo "[4/5] Evaluating results..."
python3 << 'PYEOF'
import sys, json
sys.path.insert(0, '.')
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

    truth = game.get("players", {})
    n_players = len(truth)

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

                cv = ROLE_MAP.get(view.lower(), view)
                by_size[n_players][setting][cv]["marg"].append(marg)
                by_size[n_players][setting][cv]["map"].append(map_acc)

# Build scores matching reference.json structure
# reference.json uses: avalonlogs_6player, avalonlogs_9player
scores = {"experiments": {}}

# Map player size -> reference experiment name
SIZE_TO_EXP = {6: "avalonlogs_6player", 7: None, 8: None, 9: "avalonlogs_9player"}

for size, settings_data in sorted(by_size.items()):
    exp_name = SIZE_TO_EXP.get(size)
    if exp_name is None:
        continue  # Skip 7-player for now

    scores["experiments"][exp_name] = {"description": f"AvalonLogs {size}-player CSP results", "results": {}}

    for setting, views_data in settings_data.items():
        mname = f"CSP_{setting}"
        scores["experiments"][exp_name]["results"][mname] = {}

        for view, m in views_data.items():
            if not m["marg"]:
                continue
            marg = round(sum(m["marg"]) / len(m["marg"]), 4)
            map_acc = round(sum(m["map"]) / len(m["map"]), 4)
            scores["experiments"][exp_name]["results"][mname][f"{view}_marginal"] = marg
            scores["experiments"][exp_name]["results"][mname][f"{view}_map"] = map_acc
            scores["experiments"][exp_name]["results"][mname]["n_games"] = len(m["marg"])
            break  # marg/map have same count

out_file.write_text(json.dumps(scores, indent=2), ensure_ascii=False)
print(f"Scores written to {out_file}")
print(f"Experiments: {list(scores['experiments'].keys())}")
PYEOF

# Step 5: Compare with reference
echo "[5/5] Comparing with reference..."
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
    if exp_name not in ref["experiments"]:
        continue
    ref_exp = ref["experiments"][exp_name]
    print(f"\n{exp_name}:")
    for method, vals in exp.get("results", {}).items():
        ref_vals = ref_exp["results"].get(method, {})
        primary = ref_exp.get("primary_metric", "")
        if primary and primary in vals and primary in ref_vals:
            rep = vals[primary]
            pap = ref_vals[primary]
            diff = rep - pap
            print(f"  {method}: rep={rep:.3f} paper={pap:.3f} diff={diff:+.3f}")
PYEOF

echo "=== Job Complete at $(date) ==="
