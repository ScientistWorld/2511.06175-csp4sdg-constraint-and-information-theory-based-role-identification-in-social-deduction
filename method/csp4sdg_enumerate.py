"""
Literal role-level enumeration of CSP4SDG for one AvalonLogs instance.

This is the slow, direct implementation on top of ``method/sdg_framework.py``
(SDGModel world enumeration, conditional hypotheses, IG weights on the
viewpoint's feasible worlds).  It exists to check that the grouped solver in
``method/csp4sdg_avalonlogs.py`` computes the same posteriors; it is not used
for scoring.
"""

from __future__ import annotations

import math
from copy import deepcopy

import method.generic_board as gb
from method.sdg_framework import SDGModel
from method.csp4sdg_avalonlogs import extract_constraints


def solve_instance_enumerate(inst: dict, settings=("CSP_Strict", "CSP_HypIG")) -> dict:
    names = list(inst["players"])
    counts = {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}
    schema = gb.build_schema({"role_counts": counts,
                              "good_roles": [r for r in inst["good_roles"] if r in counts]})
    evil_roles = set(counts) - set(schema.good_roles)
    hard, hyps = extract_constraints(inst)

    base = SDGModel(names, deepcopy(schema))
    for team, f in hard:
        base.add_evidence(gb.evil_at_least(schema, list(team), f))
    view = inst.get("view") or {}
    role, viewer = view.get("viewer_role"), view.get("viewer")
    if role and viewer:
        base.add_evidence(gb.role_is(viewer, role))
        if role == "percival":
            cands = view.get("merlin_candidates", [])
            if len(cands) == 2:
                c1, c2 = cands

                def mm(w, c1=c1, c2=c2):
                    if {w[c1], w[c2]} != {"merlin", "morgana"}:
                        return False
                    return all(r not in ("merlin", "morgana") for p, r in w.items() if p not in (c1, c2))
                base.add_evidence(mm)
        for p in view.get("sees_evil", []):
            base.add_evidence(lambda w, p=p: w[p] in evil_roles)

    worlds = base._worlds()
    out = {}
    for name in settings:
        model = deepcopy(base)
        if not name.endswith("Strict"):
            for kind, speaker, payload, _w in hyps:
                if kind == "team_good":
                    raw = gb.team_all_good(schema, list(payload))
                else:
                    raw = (lambda w, t=payload: w[t] in evil_roles)

                def cond(w, sp=speaker, pr=raw):
                    return (not schema.is_good(w[sp])) or pr(w)
                tot = len(worlds)
                true_cnt = sum(1 for w in worlds if cond(w))
                if true_cnt == 0 or true_cnt == tot:
                    wgt = 0.0
                else:
                    p = true_cnt / tot
                    wgt = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
                model.add_hypothesis(speaker, raw, weight=wgt, auto_weight=False)
            post = model.evaluate_advanced()[0]
        else:
            post = model.evaluate_hard_only()[0]
        out[name] = {"posterior": {p: dict(v) for p, v in post.items()}}
    return out
