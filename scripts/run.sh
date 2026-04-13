#!/bin/bash
# Solve all AvalonLogs games using pre-partitioned batch workers.
# Each worker process solves its chunk sequentially — zero IPC overhead per game.
# With 0.6 games/s sequential rate and 40 workers: ~12394/40/0.6 ≈ 8-10 min total.

set -e
cd /home/user

echo "=== CSP4SDG: Batch-parallel solve all games + update scores ==="
echo "Start: $(date)"

# --- Step 1: Solve all games in parallel batches ---
python3 << 'PYEOF'
import json, sys, time, os
from pathlib import Path
from multiprocessing import Process, Queue

sys.path.insert(0, '/home/user')
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

N_WORKERS = 40
in_dir = Path("data/avalonlogs_constraints")
out_dir = Path("data/avalonlogs_solve")
out_dir.mkdir(parents=True, exist_ok=True)

all_files = sorted(in_dir.glob("*_constraints.json"))
print(f"Total constraint files: {len(all_files)}")

chunk_size = (len(all_files) + N_WORKERS - 1) // N_WORKERS
batches = []
for i in range(N_WORKERS):
    start = i * chunk_size
    end = min(start + chunk_size, len(all_files))
    batches.append(all_files[start:end])

print(f"Partitioned into {N_WORKERS} batches (~{chunk_size} files each)")

def worker(worker_id, files, out_dir):
    t0 = time.time()
    solved = errors = 0
    for fp in files:
        dst = out_dir / (fp.stem + "_solve.json")
        try:
            result = solve_one(fp, settings=QUICK_SETTINGS)
            dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
            solved += 1
        except Exception as e:
            errors += 1
            print(f"Worker {worker_id} ERROR {fp.name}: {e}", flush=True)
    elapsed = time.time() - t0
    rate = solved / elapsed if elapsed > 0 else 0
    print(f"Worker {worker_id}: done. {solved} solved, {errors} errors in {elapsed:.0f}s ({rate:.1f}/s)", flush=True)

# Launch all workers
procs = []
t0 = time.time()
for i, batch in enumerate(batches):
    p = Process(target=worker, args=(i, batch, out_dir))
    p.start()
    procs.append(p)

# Wait for all
for p in procs:
    p.join()

elapsed = time.time() - t0
print(f"All workers finished in {elapsed:.0f}s")

n_solved = len(list(out_dir.glob("*_solve.json")))
print(f"Total solved files: {n_solved}")
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
PYEOF

echo "=== Complete at $(date) ==="
