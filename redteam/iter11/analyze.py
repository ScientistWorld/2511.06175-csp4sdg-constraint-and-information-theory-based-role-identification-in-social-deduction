#!/usr/bin/env python3
"""Analyse the iteration-11 audit runs.

python3 redteam/iter11/analyze.py pick-tau     # print the train-chosen temperature
python3 redteam/iter11/analyze.py summarize    # write summary.json / summary.md

Conventions
  W   experiment-weighted mean Brier over the six viewpoints (lower is better);
      a readable aggregate, not the ranking formula.
  MA  same aggregate for the paper's marginal accuracy (not ranked).
  R   the ranking formula: sum_e weight_e * sum_m |coef_m| * improvement_m / sd_m,
      improvement taken in the better direction (reference minus attempt for
      Brier), sd_m the population SD of metric m across this audit cohort.
      R_valid uses SDs across valid (non-failed) attempts only.
  se  paired standard error of the W difference against the reference, from
      per-instance Brier differences on identical held-out instances.
"""
import json
import math
import sys
from pathlib import Path

A = Path(__file__).resolve().parent
ROOT = A.parents[1]
RUNS = A / "attempts"
REF = json.loads((ROOT / "scoring" / "reference.json").read_text())["experiments"]
VIEWS = ["Obj", "MRL", "PCV", "MRG", "LSV", "EVM"]
EXPS = sorted(REF, key=lambda e: int(e.split("_")[1].replace("player", "")))
W = {e: REF[e]["weight"] for e in EXPS}
COEF = {(e, m): abs(REF[e]["metrics"][m]["coefficient"]) for e in EXPS for m in REF[e]["metrics"]}
HIB = {(e, m): REF[e]["metrics"][m]["higher_is_better"] for e in EXPS for m in REF[e]["metrics"]}
RANKED = [(e, m) for e in EXPS for m in REF[e]["metrics"] if COEF[(e, m)] > 0]


def load(path):
    return json.loads(Path(path).read_text())


def agg(entry, metric="brier"):
    return sum(W[e] * sum(entry[e][f"{v}_{metric}"] for v in VIEWS) / len(VIEWS) for e in EXPS)


def entries(scores):
    out = {}
    for e in EXPS:
        for m, vals in scores["experiments"][e]["results"].items():
            out.setdefault(m, {})[e] = vals
    return out


def pick_tau():
    best = None
    for d in sorted(RUNS.glob("learned_votes_t*")):
        f = d / "scores_train.json"
        if not f.exists():
            continue
        ent = entries(load(f)).get("CSP_HypIG")
        if not ent:
            continue
        w = agg(ent)
        tau = d.name.split("_t", 1)[1]
        if best is None or w < best[0]:
            best = (w, tau)
    print(best[1] if best else "1.0")


def paired_se(var_pi, ref_pi):
    """SE of the weighted-Brier difference from per-instance values."""
    if not var_pi or not ref_pi:
        return None
    inst = load(ROOT / "redteam" / "iter11" / "attempts" / "reference" / "instance_cells.json")
    cells = {}
    for iid, cell in inst.items():
        if iid in var_pi and iid in ref_pi:
            cells.setdefault(tuple(cell), []).append(var_pi[iid]["brier"] - ref_pi[iid]["brier"])
    var = 0.0
    for (e, v), ds in cells.items():
        if len(ds) < 2:
            continue
        m = sum(ds) / len(ds)
        s2 = sum((d - m) ** 2 for d in ds) / (len(ds) - 1)
        var += (W[e] / len(VIEWS)) ** 2 * s2 / len(ds)
    return math.sqrt(var)


def main_entry(name, ents):
    if "CSP_HypIG" in ents:
        return "CSP_HypIG"
    return sorted(ents)[0]


def summarize():
    runs = {}
    for d in sorted(RUNS.iterdir()):
        f = d / "scores_test.json"
        if f.exists():
            runs[d.name] = load(f)
    ref_scores = runs["reference"]
    ref_ents = entries(ref_scores)
    ref = ref_ents["CSP_HypIG"]

    # Instance -> cell map (needs the per-instance file + held-out cells): rebuild from per-instance keys.
    cell_file = RUNS / "reference" / "instance_cells.json"
    if not cell_file.exists():
        sys.path.insert(0, str(ROOT))
        import importlib.util
        spec = importlib.util.spec_from_file_location("t_eval", ROOT / "eval" / "test" / "evaluate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        insts = mod.decode_section(mod.read_heldout(), "inputs")["instances"]
        cell_file.write_text(json.dumps({i["instance_id"]: [f"avalonlogs_{i['n_players']}player",
                                                            mod.VIEW_KEY[i["view"]["perspective"]]] for i in insts}))

    cohort = {}
    for name, sc in runs.items():
        ents = entries(sc)
        status = sc.get("metadata", {}).get("method_status", {})
        for m, ent in ents.items():
            key = name if m == main_entry(name, ents) else f"{name}:{m}"
            if name in ("reference",) and m != "CSP_HypIG":
                key = f"reference:{m}"
            cohort[key] = {"entry": ent, "status": status.get(m, "?"), "run": name, "method": m}

    def sds(keys):
        out = {}
        for (e, m) in RANKED:
            xs = [cohort[k]["entry"][e][m] for k in keys]
            mu = sum(xs) / len(xs)
            out[(e, m)] = math.sqrt(sum((x - mu) ** 2 for x in xs) / len(xs)) or 1.0
        return out

    all_keys = list(cohort)
    valid_keys = [k for k in cohort if cohort[k]["status"] == "ok"]
    sd_all, sd_valid = sds(all_keys), sds(valid_keys)

    def rank(ent, sd):
        r = 0.0
        for (e, m) in RANKED:
            imp = (ent[e][m] - ref[e][m]) if HIB[(e, m)] else (ref[e][m] - ent[e][m])
            r += W[e] * COEF[(e, m)] * imp / sd[(e, m)]
        return r

    ref_pi_all = load(RUNS / "reference" / "per_instance.json") if (RUNS / "reference" / "per_instance.json").exists() else {}
    ref_pi = ref_pi_all.get("CSP_HypIG", {})
    rows = []
    for k in all_keys:
        c = cohort[k]
        ent = c["entry"]
        better = sum(1 for (e, m) in RANKED if ent[e][m] < ref[e][m] - 1e-12)
        worse = sum(1 for (e, m) in RANKED if ent[e][m] > ref[e][m] + 1e-12)
        pi_path = RUNS / c["run"] / "per_instance.json"
        se = None
        if pi_path.exists() and c["status"] == "ok":
            se = paired_se(load(pi_path).get(c["method"], {}), ref_pi)
        rows.append({
            "attempt": k, "status": c["status"], "W": agg(ent), "dW": agg(ent) - agg(ref),
            "dW_paired_se": se, "MA": agg(ent, "marginal"), "dMA": agg(ent, "marginal") - agg(ref, "marginal"),
            "R": rank(ent, sd_all), "R_valid": rank(ent, sd_valid) if k in valid_keys else None,
            "ranked_metrics_better": better, "ranked_metrics_worse": worse,
        })

    # Seed sensitivity versus the paper's HypIG-vs-Strict effect.
    seeds = [entries(runs[n])["CSP_HypIG"] for n in ("reference", "reference_seed1", "reference_seed2", "reference_seed3") if n in runs]
    strict = ref_ents["CSP_Strict"]
    seed_rng = {f"{e}.{m}": max(s[e][m] for s in seeds) - min(s[e][m] for s in seeds) for (e, m) in RANKED}
    effect = {f"{e}.{m}": strict[e][m] - ref[e][m] for (e, m) in RANKED}
    seed_W = [agg(s) for s in seeds]
    strict_se = paired_se(ref_pi_all.get("CSP_Strict", {}), ref_pi)
    per_exp = {}
    for e in EXPS:
        per_exp[e] = {
            "HypIG_Obj_brier": ref[e]["Obj_brier"], "Strict_Obj_brier": strict[e]["Obj_brier"],
            "HypIG_Obj_marginal": ref[e]["Obj_marginal"], "Strict_Obj_marginal": strict[e]["Obj_marginal"],
            "HypIG_mean_brier": sum(ref[e][f"{v}_brier"] for v in VIEWS) / 6,
            "Strict_mean_brier": sum(strict[e][f"{v}_brier"] for v in VIEWS) / 6,
            "views_HypIG_better_brier": sum(ref[e][f"{v}_brier"] < strict[e][f"{v}_brier"] for v in VIEWS),
        }
        for name in ("better_knowledge", "learned_votes", "combined", "prior", "sharpen_onehot"):
            if name in runs:
                ent = entries(runs[name]).get("CSP_HypIG")
                if ent:
                    per_exp[e][f"{name}_mean_brier"] = sum(ent[e][f"{v}_brier"] for v in VIEWS) / 6
    summary = {
        "reference_W": agg(ref), "reference_MA": agg(ref, "marginal"),
        "strict_W": agg(strict), "hypig_vs_strict_dW": agg(strict) - agg(ref), "hypig_vs_strict_paired_se": strict_se,
        "seed_W": seed_W, "seed_W_range": max(seed_W) - min(seed_W),
        "seed_max_metric_range": max(seed_rng.values()), "hypig_effect_by_metric": effect,
        "seed_range_by_metric": seed_rng, "per_experiment": per_exp, "attempts": rows,
        "chosen_tau": (A / "chosen_tau.txt").read_text().strip() if (A / "chosen_tau.txt").exists() else None,
        "enumeration_check": load(A / "enumeration_check.json") if (A / "enumeration_check.json").exists() else None,
        "read_heldout_probe": (A / "read_heldout_probe.txt").read_text().strip() if (A / "read_heldout_probe.txt").exists() else None,
    }
    (A / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["| attempt | status | W (Brier) | dW vs ref | paired se | MA | dMA | R | R_valid | better/worse of 36 |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in sorted(rows, key=lambda r: -r["R"]):
        se = f"{r['dW_paired_se']:.4f}" if r["dW_paired_se"] is not None else "-"
        rv = f"{r['R_valid']:+.3f}" if r["R_valid"] is not None else "-"
        lines.append(f"| {r['attempt']} | {r['status'][:40]} | {r['W']:.4f} | {r['dW']:+.4f} | {se} | {r['MA']:.4f} | "
                     f"{r['dMA']:+.4f} | {r['R']:+.3f} | {rv} | {r['ranked_metrics_better']}/{r['ranked_metrics_worse']} |")
    lines += ["", f"HypIG vs Strict: dW {summary['hypig_vs_strict_dW']:+.5f} (paired se {strict_se}); "
              f"seed W range {summary['seed_W_range']:.6f}; max per-metric seed range {summary['seed_max_metric_range']:.6f}",
              "", "| experiment | Strict Obj Brier | HypIG Obj Brier | Strict Obj MA | HypIG Obj MA | views HypIG better |",
              "|---|---:|---:|---:|---:|---:|"]
    for e, d in per_exp.items():
        lines.append(f"| {e} | {d['Strict_Obj_brier']:.4f} | {d['HypIG_Obj_brier']:.4f} | {d['Strict_Obj_marginal']:.4f} | "
                     f"{d['HypIG_Obj_marginal']:.4f} | {d['views_HypIG_better_brier']}/6 |")
    (A / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    {"pick-tau": pick_tau, "summarize": summarize}[sys.argv[1]]()
