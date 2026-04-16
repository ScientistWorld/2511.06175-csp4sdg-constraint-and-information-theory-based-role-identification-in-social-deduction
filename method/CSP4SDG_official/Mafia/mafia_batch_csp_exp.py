"""
batch CSP inference for Mafia dataset
"""

import json, math, sys
from copy import deepcopy
from pathlib import Path
from sdg_framework import SDGModel
from mafia_board  import build_schema, role_is, role_not, mafia_at_least

# ---------- constants ----------
GOOD  = {"bystander"}
MAFIA = {"mafioso"}

def is_good(r):  return r in GOOD
def is_mafia(r): return r in MAFIA

# ---------- label normaliser ----------
def norm(role: str) -> str:
    """Map any spelling of 'mafia' → 'mafioso'."""
    return "mafioso" if role.lower() == "mafia" else role.lower()

# ---------- MAP ----------
def map_world(model: SDGModel):
    best, score = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s = sum(sa.weight for sa in model.add_soft if sa.func(w))
        val = m * math.log(model.A_base) + math.log(1 + s)
        if val > score:
            best, score = w, val
    return best

# ---------- constraint -> predicate ----------
def build_pred(c):
    t, a = c["type"], c["args"]
    if t == "role_is":
        return role_is(a["player"], norm(a["role"]))
    if t == "role_not":
        return role_not(a["player"], norm(a["role"]))
    if t in ("mafia_at_least", "evil_at_least"):
        k = a.get("min_fail", a.get("min"))
        return mafia_at_least(a["team"], k)
    raise ValueError(t)

# ---------- add hypothesis ----------
def add_hypo(model, c):
    a  = c["args"]
    w  = c.get("weight", 0.2)
    aw = c.get("auto_weight", False)

    tgt_set = norm(a["set"])
    tgt     = a["target"]

    pred = (lambda w, t=tgt: w[t] == "mafioso") if tgt_set == "mafioso" \
           else (lambda w, t=tgt: w[t] == "bystander")

    model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=aw)

# ---------- per-game ----------
def run_game(fp: Path, cond: str):
    data = json.loads(fp.read_text(encoding="utf-8"))

    # --- players & schema (labels unified) ---
    role_of = {p["name"]: norm(p["role"]) for p in data["players"]}
    players = list(role_of.keys())
    schema  = build_schema([{"name": n, "role": r} for n, r in role_of.items()])

    bys_players = [p for p, r in role_of.items() if r == "bystander"]
    maf_players = [p for p, r in role_of.items() if r == "mafioso"]

    record = {"file": fp.name, "cond": cond, "players": role_of, "days": {}}

    hard_acc, hypo_acc = [], []

    for day in sorted(data["days"], key=lambda d: d["day"]):
        idx = day["day"]
        hard_acc.extend(day["evidence"] + day["phenomenon"])
        hypo_acc.extend(day["hypotheses"])

        record["days"][idx] = {}

        # perspective extras
        persp = {"objective": []}

        if bys_players:
            p = bys_players[0]
            persp["BYS"] = [role_is(p, "bystander")]

        if maf_players:
            me   = maf_players[0]
            extra = [role_is(me, "mafioso")]
            extra += [role_is(o, "mafioso") for o in maf_players if o != me]
            persp["MAF"] = extra

        SETTINGS = [
            ("Strict",   False, False, False, False),
            ("+Assert",  True,  False, False, False),
            ("+HypIG",   True,  True,  True,  False),
            ("+HypM",    True,  True,  False, False),
            ("+TurnIG",  True,  True,  True,  True),
        ]

        for view, extras in persp.items():
            base = SDGModel(players, deepcopy(schema))
            for c in hard_acc:
                if c["type"] in {"role_is", "role_not", "mafia_at_least", "evil_at_least"}:
                    base.add_evidence(build_pred(c))
            for pr in extras:
                base.add_evidence(pr)

            record["days"][idx][view] = {}
            for title, ua, uh, auto, only_today in SETTINGS:
                model = deepcopy(base)

                if uh:
                    src = day["hypotheses"] if only_today else hypo_acc
                    for c in src:
                        add_hypo(model, c if auto else {**c, "auto_weight": False})

                post = {}
                try:
                    post, _, _ = model.evaluate_advanced() if uh else model.evaluate_hard_only()
                except Exception:
                    pass
                try:
                    best = map_world(model)
                except Exception:
                    best = {}

                record["days"][idx][view][title] = {"posterior": post, "best": best}

    return record

# ---------- batch driver ----------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python mafia_batch_csp_exp.py mafia_dataset_constraints/ results.jsonl")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    out  = Path(sys.argv[2]).resolve()

    with out.open("w", encoding="utf-8") as fout:
        for cond in ("Truth", "Lie"):
            for fp in (root / cond).glob("*_constraints.json"):
                print("[RUN]", fp.name)
                rec = run_game(fp, cond)
                fout.write(json.dumps(rec) + "\n")

    print("Done. Results →", out)
