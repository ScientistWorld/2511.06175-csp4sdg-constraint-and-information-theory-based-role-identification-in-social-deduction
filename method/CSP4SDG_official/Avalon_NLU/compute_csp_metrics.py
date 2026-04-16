"""
Compute weighted marginal accuracy and MAP assignment accuracy
from results.jsonl produced by avalon_batch_csp.py.

Usage:
    python compute_csp_metrics.py csp_results.jsonl csp_metrics.json
"""

import json
import sys
import csv
from collections import defaultdict

def load_results(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def compute_game_metrics(game_rec):
    """
    For a single game record, compute per-(cond,view,setting) two metrics:
      - marginal accuracy averaged over quests
      - map accuracy averaged over quests
    Return dict[(cond,view,setting)] = {marg_sum, map_sum, count, marg_mean, map_mean}
    """
    truth = game_rec["players"]            # name->role_key
    P = len(truth)
    out = {}
    for q_idx, quests in game_rec["quests"].items():
        for view, settings in quests.items():
            for setting, data in settings.items():
                posterior = data["posterior"]  # {player:{role:prob}}
                best      = data["best"]       # {player:role}
                # marginal accuracy this quest
                marg = sum(posterior.get(p, {}).get(true_r, 0.0)
                           for p, true_r in truth.items()) / P

                # map accuracy this quest: fraction of correctly assigned players
                correct = sum(1 for p, true_r in truth.items()
                              if best.get(p) == true_r)
                map_acc = correct / P

                key = (game_rec["cond"], view, setting)
                rec = out.setdefault(key, {"marg_sum":0.0,
                                           "map_sum":0.0,
                                           "count":0})
                rec["marg_sum"] += marg
                rec["map_sum"]  += map_acc
                rec["count"]    += 1

    # normalize per game
    for rec in out.values():
        rec["marg_mean"] = rec["marg_sum"] / rec["count"]
        rec["map_mean"]  = rec["map_sum"]  / rec["count"]
    return out


def aggregate(all_game_metrics):
    """
    Input: list of per-game dicts from compute_game_metrics.
    Aggregate across games to final means.
    """
    agg = defaultdict(lambda: {"marg_sum":0.0, "map_sum":0.0, "count":0})
    for gm in all_game_metrics:
        for k, rec in gm.items():
            agg[k]["marg_sum"] += rec["marg_mean"]
            agg[k]["map_sum"]  += rec["map_mean"]
            agg[k]["count"]    += 1
    # final
    out = {}
    for k, rec in agg.items():
        cond, view, setting = k
        out[k] = {
            "cond": cond,
            "view": view,
            "setting": setting,
            "marginal_accuracy": rec["marg_sum"]/rec["count"],
            "map_accuracy":      rec["map_sum"] /rec["count"]
        }
    return out

if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Usage: python compute_csp_metrics.py results.jsonl output_metrics.json")
        sys.exit(1)

    results_path = sys.argv[1]
    out_path     = sys.argv[2]

    all_metrics = []
    for game in load_results(results_path):
        gm = compute_game_metrics(game)
        all_metrics.append(gm)

    final = aggregate(all_metrics)

    # write JSON
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(list(final.values()), f, indent=2, ensure_ascii=False)

    # also write CSV
    csv_path = out_path.rsplit(".",1)[0]+".csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "cond","view","setting","marginal_accuracy","map_accuracy"])
        writer.writeheader()
        for rec in final.values():
            writer.writerow(rec)

    print(f"Metrics written to {out_path} and {csv_path}")
