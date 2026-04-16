"""
Calculate marginal-accuracy / MAP-accuracy for the CSP results of Mafia dataset.

Input : results.jsonl   (from mafia_batch_csp_exp.py)
Output: metrics.json    (and metrics.csv)

Usage:
    python compute_mafia_csp_metrics.py results.jsonl csp_metrics.json
"""

import json, sys, csv
from collections import defaultdict

# -------- helpers -------- #
def each_game(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)

def per_game_stats(game):
    """
    Return dict keyed by (cond,view,setting) with sums & counts.
    """
    truth = game["players"]        # {player: true_role}
    P     = len(truth)
    out   = {}

    for day_idx, day_obj in game["days"].items():
        for view, view_obj in day_obj.items():
            for setting, payload in view_obj.items():
                post = payload["posterior"]
                best = payload["best"]

                marg = sum(
                    post.get(p, {}).get(r, 1.0)
                    for p, r in truth.items()
                ) / P

                map_acc = sum(
                    (best.get(p, r) == r)
                    for p, r in truth.items()
                ) / P

                key=(game["cond"], view, setting)
                rec=out.setdefault(key,{"marg_sum":0.0,"map_sum":0.0,"count":0})
                rec["marg_sum"]+=marg
                rec["map_sum"] +=map_acc
                rec["count"]   +=1
    # average within this game
    for rec in out.values():
        rec["marg_mean"]=rec["marg_sum"]/rec["count"]
        rec["map_mean"] =rec["map_sum"] /rec["count"]
    return out

def aggregate(per_game_dicts):
    agg=defaultdict(lambda:{"marg_sum":0.0,"map_sum":0.0,"count":0})
    for gdict in per_game_dicts:
        for k,rec in gdict.items():
            agg[k]["marg_sum"]+=rec["marg_mean"]
            agg[k]["map_sum"] +=rec["map_mean"]
            agg[k]["count"]   +=1
    final=[]
    for (cond,view,setting),rec in agg.items():
        final.append({
            "cond":cond,
            "view":view,
            "setting":setting,
            "marginal_accuracy":rec["marg_sum"]/rec["count"],
            "map_accuracy":     rec["map_sum"] /rec["count"]
        })
    return final

# -------- main -------- #
if __name__=="__main__":
    if len(sys.argv)!=3:
        print("Usage: python compute_mafia_csp_metrics.py mafia_csp_results.jsonl csp_metrics.json")
        sys.exit(1)
    res_path=sys.argv[1]; out_json=sys.argv[2]

    per_games=[per_game_stats(g) for g in each_game(res_path)]
    metrics = aggregate(per_games)

    # JSON
    with open(out_json,"w",encoding="utf-8") as f:
        json.dump(metrics,f,indent=2,ensure_ascii=False)

    # CSV
    csv_path=out_json.rsplit(".",1)[0]+".csv"
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["cond","view","setting","marginal_accuracy","map_accuracy"])
        w.writeheader(); w.writerows(metrics)

    print("Metrics saved to", out_json, "and", csv_path)
