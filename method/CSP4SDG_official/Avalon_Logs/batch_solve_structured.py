"""
Run the single‑game CSP solver over every *_constraints.json file in <in_dir>
and write per‑game results JSON to <out_dir>/<stem>_solve.json.

Perspectives:
  • objective
  • one perspective for every player, named by role with an index
    (e.g. evil_minion1, evil_minion2, loyal_follower1, …).

Role knowledge
--------------
Each player knows their own role (hard).
evil_minion : knows all evil_minion / mordred / morgana are evil.
mordred     : knows evil_minion and morgana are evil.
morgana     : knows evil_minion and mordred are evil.
merlin      : knows evil_minion / oberon / morgana are evil.
percival    : knows exactly two players are {merlin,morgana}.
oberon, loyal_follower : no extra knowledge beyond self.

Usage
-----
    python batch_solve_structured.py avalon_logs avalon_logs_csp_results
"""

import json, math, sys
from pathlib import Path
from copy import deepcopy
from typing import Dict, List
import random
import sdg_framework
from sdg_framework import SDGModel
import generic_board as gb   # must be in PYTHONPATH
sys.setrecursionlimit(100000)

# ---------- global role sets ----------
GOOD_ROLES = {"merlin", "percival", "loyal_follower", "servant"}
EVIL_ROLES = {"evil_minion", "assassin", "morgana", "mordred", "oberon"}

def is_good(r: str) -> bool: return r in GOOD_ROLES
def is_evil(r: str) -> bool: return r in EVIL_ROLES

# ---------- predicate factories ----------
def evil_pred_factory(target: str):
    def pred(world: Dict[str,str]):
        return world[target] in EVIL_ROLES
    return pred

def good_pred_factory(target: str):
    def pred(world: Dict[str,str]):
        return world[target] in GOOD_ROLES
    return pred

def percival_mm_pred(c1: str, c2: str):
    """Exactly {c1,c2} are {merlin,morgana}."""
    def _pred(w: Dict[str,str]):
        roles = {w[c1], w[c2]}
        if roles != {"merlin", "morgana"}:
            return False
        for p, r in w.items():
            if p not in (c1, c2) and r in {"merlin", "morgana"}:
                return False
        return True
    return _pred

# ---------- MAP helper ----------
def compute_map(model: SDGModel):
    best, score = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s = sum(sa.weight for sa in model.add_soft if sa.func(w))
        val = m * math.log(model.A_base) + math.log(1 + s)
        if val > score:
            best, score = w, val
    return best

# ---------- evidence builders ----------
def build_pred(schema, ev):
    if ev["type"] == "evil_at_least":
        return gb.evil_at_least(schema, **ev["args"])
    raise ValueError(ev["type"])

def add_assert(model: SDGModel, c: Dict, schema):
    t, a = c["type"], c["args"]
    if t == "assert_team_good":
        model.add_assertion(a["speaker"], gb.team_all_good(schema, a["team"]))
    elif t == "assert_role_is":
        model.add_assertion(a["speaker"], gb.role_is(a["speaker"], a["role"]))
    elif t == "assert_role_in":
        if a["set"] == "evil":
            pred = evil_pred_factory(a["target"])
        else:
            pred = good_pred_factory(a["target"])
        model.add_assertion(a["speaker"], pred)

def add_hypo(model: SDGModel, c: Dict, schema):
    t, a = c["type"], c["args"]
    w = c.get("weight", 0.2)
    aw = c.get("auto_weight", False)
    if t == "hypo_team_good":
        model.add_hypothesis(a["speaker"], gb.team_all_good(schema, a["team"]),
                             weight=w, auto_weight=aw)
    elif t == "hypo_role_in":
        if a["set"] == "evil":
            pred = evil_pred_factory(a["target"])
        else:
            pred = good_pred_factory(a["target"])
        model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=aw)

# ---------- CSP stage settings ----------
STAGES = [
    ("Strict",   False, False, False, False),
    ("+Assert",  True,  False, False, False),
    ("+HypIG",   True,  True,  True,  False),
    ("+HypM",    True,  True,  False, False),
    ("+TurnIG",  True,  True,  True,  True),
]

# ---------- main per‑file solver ----------
def solve_one(fp: Path) -> dict:
    game   = json.loads(fp.read_text(encoding="utf-8"))
    names  = [p["name"] for p in game["players"]]
    truth  = {p["name"]: p["role"] for p in game["players"]}
    schema = gb.build_schema(game["schema"])

    # group players by true role
    by_role: Dict[str, List[str]] = {}
    for n, r in truth.items():
        by_role.setdefault(r, []).append(n)

    # counters to disambiguate duplicates
    role_counters = {r: 0 for r in by_role}

    out = {"file": fp.name, "players": truth, "quests": {}}
    hard_acc, assert_acc, hypo_acc = [], [], {}

    for q in game["quests"]:
        idx = q["quest"]
        hard_acc.extend(q["constraints"]["evidence"])
        assert_acc.extend(q["constraints"]["assertions"])
        hypo_acc[idx] = q["constraints"]["hypotheses"]
        out["quests"][str(idx)] = {}

        # build perspective constraints
        perspective = {"objective": []}
        for player in names:
            role = truth[player]
            role_counters[role] += 1
            view_name = (f"{role}{role_counters[role]}"
                         if len(by_role[role]) > 1 else role)
            extras = [gb.role_is(player, role)]  # self‑knowledge

            # role‑specific knowledge
            if role == "evil_minion":
                for r2 in ("evil_minion","mordred","morgana"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "mordred":
                for r2 in ("evil_minion","morgana"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "morgana":
                for r2 in ("evil_minion","mordred"):
                    for p2 in by_role.get(r2, []):
                        if p2 != player:
                            extras.append(evil_pred_factory(p2))
            elif role == "merlin":
                for r2 in ("evil_minion","oberon","morgana"):
                    for p2 in by_role.get(r2, []):
                        extras.append(evil_pred_factory(p2))
            elif role == "percival":
                mm = by_role.get("merlin", []) + by_role.get("morgana", [])
                if len(mm) == 2:
                    extras.append(percival_mm_pred(mm[0], mm[1]))
            # loyal_follower / oberon get no extra

            perspective[view_name] = extras

        # run each CSP stage for each perspective
        for view, extras in perspective.items():
            out["quests"][str(idx)][view] = {}

            # build base model
            base = SDGModel(names, deepcopy(schema))
            for ev in hard_acc:
                base.add_evidence(build_pred(schema, ev))
            for ex in extras:
                base.add_evidence(ex)

            for title, ua, uh, aw, only_today in STAGES:
                model = deepcopy(base)
                if ua:
                    for a in assert_acc:
                        add_assert(model, a, schema)
                if uh:
                    src = (hypo_acc[idx] if only_today
                           else [h for hs in hypo_acc.values() for h in hs])
                    for h in src:
                        if not aw:
                            h = {**h, "auto_weight": False}
                        add_hypo(model, h, schema)
                try:
                    post = (model.evaluate_hard_only()[0]
                            if (not ua and not uh)
                            else model.evaluate_advanced()[0])
                    best = compute_map(model)
                except ValueError:
                    post, best = {}, {}
                out["quests"][str(idx)][view][title] = {
                    "posterior": post,
                    "best": best
                }

    return out


# ---------- batch runner ----------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python batch_solve_structured.py <in_dir> <out_dir>")
        sys.exit(1)

    in_dir  = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for fp in in_dir.glob("*_constraints.json"):
        dst = out_dir / (fp.stem + "_solve.json")
        if dst.exists():
            print(f"[SKIP] {fp.name} (already exists)")
            continue
        print("[RUN]", fp.name)
        try:
            result = solve_one(fp)
            if result is None:
                print(f"[SKIP] {fp.name} (returned None)")
                continue
            dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print("  ->", dst.name)
        except BaseException as e:
            print(f"[ERROR] {fp.name}: {type(e).__name__}: {e}")
            import traceback;

            traceback.print_exc()
            continue

    print("✓ Batch solving finished.")
