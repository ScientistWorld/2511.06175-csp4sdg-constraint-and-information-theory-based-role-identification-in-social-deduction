"""
Aggregate marginal-accuracy & MAP-accuracy for LLM-only / LLM+CSP
experiments on the Mafia dataset.

Usage
-----
    python compute_mafia_llm_metrics.py mafia_dataset_llm/  mafia_dataset_constraints/ mafia_llm_metrics
Outputs
-------
  mafia_llm_metrics.json
  mafia_llm_metrics.csv
"""

import json, csv, sys, re
from pathlib import Path
from collections import defaultdict

# --------------------------------------------------------------------------- #
# 1.  Ground-truth loader  (reads *_constraints.json produced by CSP extractor)
# --------------------------------------------------------------------------- #
def load_gt(constraints_root: Path):
    """
    Returns {(cond, game_id): {player: true_role}}
    """
    gt = {}
    for cond in ("Truth", "Lie"):
        for fp in (constraints_root/cond).glob("*_constraints.json"):
            game_id = fp.stem.replace("_constraints", "")
            data = json.loads(fp.read_text(encoding="utf-8"))
            roles = {p["name"]: p["role"] for p in data["players"]}
            gt[(cond, game_id)] = roles
    return gt

# --------------------------------------------------------------------------- #
# 2.  File-name parser (matches mafia_llm_exp.py convention)
# --------------------------------------------------------------------------- #
def parse_fname(fp: Path):
    """
    Return tuple:
      stem, mode, setting, chat, view, day_idx, method_name
    """
    parts = fp.stem.split("_")
    stem  = parts[0]

    if parts[1] == "llm" and parts[2] == "csp":
        # llm_csp_<Setting>_<chat>_<view>_<day>
        mode     = "llm_csp"
        setting  = parts[3]
        chat     = parts[4]
        view     = parts[5]
        day      = int(parts[6])
        method   = f"CSP+LLM-{setting}"
    else:
        # llm_<chat>_<view>_<day>
        mode     = "llm"
        setting  = None
        chat     = parts[2]
        view     = parts[3]
        day      = int(parts[4])
        method   = f"LLM-{chat}"
    return stem, mode, setting, chat, view, day, method

# --------------------------------------------------------------------------- #
# 3.  Helpers for each output JSON
# --------------------------------------------------------------------------- #
def load_run(fp: Path):
    d = json.loads(fp.read_text(encoding="utf-8"))
    return d.get("posterior", {}), d.get("best", {})

# --------------------------------------------------------------------------- #
# 4.  Metric computation across all runs
# --------------------------------------------------------------------------- #
def compute_metrics(llm_root: Path, constraints_root: Path):
    gt = load_gt(constraints_root)

    stats = defaultdict(lambda: {"marg_sum":0.0, "map_sum":0.0, "cnt":0})

    for cond in ("Truth", "Lie"):
        for fp in (llm_root/cond).glob("*.json"):
            stem, _, _, _, view, _, method = parse_fname(fp)

            true_roles = gt.get((cond, stem))
            if true_roles is None:
                print(f"[WARN] GT not found for {cond}/{stem}")
                continue

            posterior, best = load_run(fp)
            players = list(true_roles.keys())
            P = len(players)

            marg = sum(
                posterior.get(p, {}).get(true_roles[p], 1.0)
                for p in players) / P

            map_acc = sum(
                (best.get(p, true_roles[p]) == true_roles[p])
                for p in players) / P

            key = (cond, method, view)
            rec = stats[key]
            rec["marg_sum"] += marg
            rec["map_sum"]  += map_acc
            rec["cnt"]      += 1

    # aggregate
    out=[]
    for (cond, method, view), rec in stats.items():
        out.append({
            "cond": cond,
            "method": method,
            "view": view,
            "marginal_accuracy": rec["marg_sum"]/rec["cnt"],
            "map_accuracy":      rec["map_sum"] /rec["cnt"]
        })
    return out

# --------------------------------------------------------------------------- #
# 5.  CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    if len(sys.argv)!=4:
        print("Usage: python compute_mafia_llm_metrics.py "
              "<mafia_llm_dir> <mafia_constraints_dir> <output_prefix>")
        sys.exit(1)

    llm_dir  = Path(sys.argv[1]).resolve()
    constr   = Path(sys.argv[2]).resolve()
    out_pref = sys.argv[3]

    res = compute_metrics(llm_dir, constr)

    # JSON
    json_path = f"{out_pref}.json"
    with open(json_path,"w",encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)

    # CSV
    csv_path = f"{out_pref}.csv"
    with open(csv_path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=[
            "cond","method","view","marginal_accuracy","map_accuracy"])
        w.writeheader(); w.writerows(res)

    print("Metrics saved to", json_path, "and", csv_path)
