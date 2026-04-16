"""Compute marginal & MAP accuracy for LLM-only and LLM+CSP experiments.

Usage:
    python compute_llm_metrics.py dataset_llm dataset_processed csp_metrics

Outputs:
  <output_prefix>.json  -- list of records {cond,method,view,marginal_accuracy,map_accuracy}
  <output_prefix>.csv   -- same as CSV
"""
import json
import csv
import sys
import re
from pathlib import Path
from collections import defaultdict

def load_ground_truth(processed_dir):
    """
    Load constraints JSON to get true roles per game.
    Returns dict[(cond, game_stem)] = {player: true_role, ...}
    """
    gt = {}
    for cond in ("Truth", "Lie"):
        for f in (processed_dir/cond).glob("*_constraints.json"):
            stem = f.stem.replace("_constraints", "")
            data = json.loads(f.read_text(encoding="utf-8"))
            role_of = {p["name"]: p["role"] for p in data["players"]}
            gt[(cond, stem)] = role_of
    return gt

def parse_filename(fp: Path):
    """
    Given a filename like:
      stem_llm_global_assassin_3.json
      stem_llm_csp_Strict_global_merlin_2.json
    return (stem, mode, setting, chat, view, quest_idx)
    setting is None for llm-only
    """
    base = fp.stem
    parts = base.split("_")
    stem = parts[0]
    mode = parts[1]
    if parts[1] == "llm" and parts[2] == "csp":
        # llm_csp
        mode = "llm_csp"
        setting = parts[3]
        chat    = parts[4]
        view    = parts[5]
        qid     = int(parts[6])
    else:
        # llm-only
        setting = None
        chat    = parts[2]
        view    = parts[3]
        qid     = int(parts[4])
    method = setting and f"CSP+LLM-{setting}" or f"LLM-{chat}"
    return stem, mode, setting, chat, view, qid, method

def load_output(fp: Path):
    """
    Load one experiment JSON (posterior & best).
    """
    data = json.loads(fp.read_text(encoding="utf-8"))
    posterior = data.get("posterior", {})
    best      = data.get("best", {})
    return posterior, best

def compute_metrics(dataset_llm_dir, dataset_processed_dir):
    gt_map = load_ground_truth(Path(dataset_processed_dir))
    stats = defaultdict(lambda: {"marg_sum":0.0, "map_sum":0.0, "count":0})

    for cond in ("Truth","Lie"):
        for fp in (Path(dataset_llm_dir)/cond).glob("*.json"):
            stem, mode, setting, chat, view, qid, method = parse_filename(fp)
            role_of = gt_map.get((cond, stem))
            if role_of is None:
                print(f"[WARN] no GT for {cond}/{stem}")
                continue

            players  = list(role_of.keys())
            posterior, best = load_output(fp)

            # Marginal accuracy for this quest
            P = len(players)
            marg = sum(
                posterior.get(p, {}).get(role_of[p], 0.0)
                for p in players
            ) / P

            # MAP‐Accuracy for this quest: fraction of correctly assigned players
            correct = sum(
                1 for p in players
                if best.get(p) == role_of[p]
            )
            map_acc = correct / P

            # accumulate
            key = (cond, method, view)
            rec = stats[key]
            rec["marg_sum"] += marg
            rec["map_sum"]  += map_acc
            rec["count"]    += 1

    # aggregate final results
    results = []
    for (cond, method, view), rec in stats.items():
        results.append({
            "cond": cond,
            "method": method,
            "view": view,
            "marginal_accuracy": rec["marg_sum"] / rec["count"],
            "map_accuracy":      rec["map_sum"]  / rec["count"]
        })
    return results


if __name__=="__main__":
    if len(sys.argv)!=4:
        print("Usage: python compute_llm_metrics.py <dataset_llm_dir> <dataset_processed_dir> <output_prefix>")
        sys.exit(1)

    llm_dir = sys.argv[1]
    proc_dir = sys.argv[2]
    out_pref = sys.argv[3]

    metrics = compute_metrics(llm_dir, proc_dir)

    # write JSON
    json_path = f"{out_pref}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    # write CSV
    csv_path = f"{out_pref}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "cond","method","view","marginal_accuracy","map_accuracy"])
        writer.writeheader()
        for rec in metrics:
            writer.writerow(rec)

    print(f"Metrics written to {json_path} and {csv_path}")
