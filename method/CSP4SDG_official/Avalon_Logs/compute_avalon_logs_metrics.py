#!/usr/bin/env python3
"""
compute_avalon_logs_metrics.py

Aggregate accuracy metrics for Avalon‑Logs experiments that now include
per‑player perspectives (e.g. loyal_follower1, loyal_follower2).

For each LLM run (file pattern
   <stem>_<view>_llm_Qk.json)

we locate
   • companion LLM+CSP file     (<stem>_<view>_llm_csp_Qk.json)
   • CSP solve file             (<stem>_constraints_solve.json)

and compute marginal / MAP accuracy:

   - CSP‑<setting>     (average over all matching suffixes)
   - LLM‑only
   - LLM + CSP (+IG)

Outputs:
   <prefix>.json / .csv              aggregated by (view,method)
   <prefix>_by_size.json / .csv      additionally bucketed by #players

Usage:
   python compute_avalon_logs_metrics.py \
       <llm_results_dir> <csp_solve_dir> <output_prefix>
"""

import json, csv, re, sys
from pathlib import Path
from collections import defaultdict

LLM_RE = re.compile(
    r'^(?P<stem>\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2})_'
    r'(?P<view>.+?)_'
    r'(?P<mode>llm(?:_csp)?)_'
    r'Q(?P<quest>\d+)\.json$'
)

def parse_llm_name(fp: Path):
    m = LLM_RE.match(fp.name)
    if not m:
        raise ValueError(fp.name)
    return m.group('stem'), m.group('view'), m.group('mode'), int(m.group('quest'))

# ---- accuracy helpers ------------------------------------------------------
def marg_acc(post, truth):
    return sum(post.get(p, {}).get(r, 0.0) for p, r in truth.items())/len(truth)

def map_acc(best, truth):
    return sum(best.get(p)==r for p,r in truth.items())/len(truth)

# ----------------------------------------------------------------------------
def compute(llm_dir: Path, csp_dir: Path, out_pref: str):
    agg   = defaultdict(lambda: {"m":0.0,"b":0.0,"n":0})
    aggSz = defaultdict(lambda: {"m":0.0,"b":0.0,"n":0})

    for fp in llm_dir.glob("*_llm_Q*.json"):
        try:
            stem, view, mode, qidx = parse_llm_name(fp)
        except ValueError:
            continue
        if mode != "llm":
            continue

        llm_csp_fp = llm_dir / f"{stem}_{view}_llm_csp_Q{qidx}.json"
        solve_fp   = csp_dir / f"{stem}_constraints_solve.json"
        if not llm_csp_fp.exists() or not solve_fp.exists():
            print(f"[WARN] missing companions for {fp.name}")
            continue

        solve = json.loads(solve_fp.read_text(encoding="utf-8"))
        truth = solve["players"]
        P     = len(truth)
        qkey  = str(qidx)

        all_views = [
            v for v in solve["quests"][qkey].keys()
            if v == view or (v.startswith(view) and v[len(view):].isdigit())
        ]
        if not all_views:
            print(f"[WARN] no CSP views matching '{view}' for {stem} quest {qkey}")
            continue

        available_settings = list(solve["quests"][qkey][all_views[0]].keys())

        # ----- CSP settings (average across all_views) -----
        for st in available_settings:
            ms, bs = [], []
            for vv in all_views:
                pack = solve["quests"][qkey][vv].get(st)
                if pack is None:
                    continue
                ms.append(marg_acc(pack["posterior"], truth))
                bs.append(map_acc(pack["best"], truth))
            if not ms:
                continue
            m = sum(ms)/len(ms)
            b = sum(bs)/len(bs)

            method = f"CSP-{st}"
            agg[(view, method)]["m"] += m
            agg[(view, method)]["b"] += b
            agg[(view, method)]["n"] += 1
            aggSz[(P, view, method)]["m"] += m
            aggSz[(P, view, method)]["b"] += b
            aggSz[(P, view, method)]["n"] += 1

        # ----- LLM‑only -----
        llm_data = json.loads(fp.read_text(encoding="utf-8"))
        m = marg_acc(llm_data["posterior"], truth)
        b = map_acc(llm_data["best"], truth)
        agg[(view, "LLM")]["m"] += m
        agg[(view, "LLM")]["b"] += b
        agg[(view, "LLM")]["n"] += 1
        aggSz[(P, view, "LLM")]["m"] += m
        aggSz[(P, view, "LLM")]["b"] += b
        aggSz[(P, view, "LLM")]["n"] += 1

        # ----- LLM+CSP (+IG) -----
        lc_data = json.loads(llm_csp_fp.read_text(encoding="utf-8"))
        m = marg_acc(lc_data["posterior"], truth)
        b = map_acc(lc_data["best"], truth)
        agg[(view, "LLM+CSP+IG")]["m"] += m
        agg[(view, "LLM+CSP+IG")]["b"] += b
        agg[(view, "LLM+CSP+IG")]["n"] += 1
        aggSz[(P, view, "LLM+CSP+IG")]["m"] += m
        aggSz[(P, view, "LLM+CSP+IG")]["b"] += b
        aggSz[(P, view, "LLM+CSP+IG")]["n"] += 1

    # ---------- dump helpers ----------
    def dump_csv(path, fields, rows):
        with open(path,"w",newline="",encoding="utf-8") as f:
            w = csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    rows = [
        {"view":v,"method":m,
         "marginal_accuracy":d["m"]/d["n"],
         "map_accuracy":      d["b"]/d["n"],
         "games":             d["n"]}
        for (v,m),d in agg.items() if d["n"]
    ]
    Path(f"{out_pref}.json").write_text(
        json.dumps(rows,indent=2,ensure_ascii=False),
        encoding="utf-8")
    dump_csv(f"{out_pref}.csv",
             ["view","method","marginal_accuracy","map_accuracy","games"],
             rows)

    rows_sz = [
        {"players":P,"view":v,"method":m,
         "marginal_accuracy":d["m"]/d["n"],
         "map_accuracy":      d["b"]/d["n"],
         "games":             d["n"]}
        for (P,v,m),d in aggSz.items() if d["n"]
    ]
    Path(f"{out_pref}_by_size.json").write_text(
        json.dumps(rows_sz,indent=2,ensure_ascii=False),
        encoding="utf-8")
    dump_csv(f"{out_pref}_by_size.csv",
             ["players","view","method","marginal_accuracy","map_accuracy","games"],
             rows_sz)

    print(f"✓ Metrics saved to {out_pref}.{{json,csv}} and _by_size variants.")

# ----------------------------------------------------------------------------
if __name__=="__main__":
    if len(sys.argv)!=4:
        print("Usage: python compute_avalon_logs_metrics.py "
              "<llm_dir> <csp_dir> <output_prefix>")
        sys.exit(1)
    compute(
        Path(sys.argv[1]).resolve(),
        Path(sys.argv[2]).resolve(),
        sys.argv[3]
    )
