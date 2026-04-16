"""
Run CSP inference for every processed game file under
dataset_processed/{Truth,Lie}/  and produce results JSONL.

Usage:
    python avalon_batch_csp_exp.py dataset_processed/ csp_results.jsonl
"""

import json, math, sys, os
from pathlib import Path
from copy import deepcopy
from sdg_framework import SDGModel
from avalon_board import SCHEMA, role_is, role_not, evil_at_least, team_all_good

# ---------- helper: role sets ----------
GOOD_ROLES = {"merlin", "percival", "loyal_follower", "servant"}
EVIL_ROLES = {"assassin", "morgana", "minion", "mordred"}

def is_good(role: str) -> bool: return role in GOOD_ROLES
def is_evil(role: str) -> bool: return role in EVIL_ROLES

# ---------- helper: Percival hard predicate ----------
def percival_mm_pred(cand1, cand2):
    """
    Exactly {cand1,cand2} are {merlin,morgana} in some order.
    No other player may be merlin/morgana.
    """
    def _pred(world):
        roles = {world[cand1], world[cand2]}
        if roles != {"merlin", "morgana"}:  # must be those two
            return False
        for p, r in world.items():
            if p not in (cand1, cand2) and r in {"merlin", "morgana"}:
                return False
        return True
    return _pred

# ---------- MAP helper ----------
def map_assignment(model: SDGModel):
    best, score = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s = sum(sa.weight for sa in model.add_soft if sa.func(w))
        logF = m * math.log(model.A_base) + math.log(1 + s)
        if logF > score:
            best, score = w, logF
    return best

# ---------- main processing ----------
def run_game(constraints_path: Path, cond_label: str):
    game = json.loads(constraints_path.read_text())
    players = [p["name"] for p in game["players"]]
    role_of = {p["name"]: p["role"].lower().replace(" ", "_")
               for p in game["players"]}

    for player, raw in role_of.items():
        if raw == "loyal_follower" or raw.startswith("servant"):
            role_of[player] = "servant"

    # Collect which players have each role
    players_by_role = {}
    for name, role in role_of.items():
        players_by_role.setdefault(role, []).append(name)

    record = {
        "file":   constraints_path.name,
        "cond":   cond_label,
        "players": role_of,
        "quests": {}
    }

    # Global accumulators
    hard_acc, assert_acc, hypo_acc = [], [], []

    for q in sorted(game["quests"], key=lambda q: q["quest"]):
        idx = q["quest"]
        ev  = q["constraints"]["evidence"] + q["constraints"]["phenomenon"]
        ass = q["constraints"]["assertions"]
        hyp = q["constraints"]["hypotheses"]

        hard_acc.extend(ev)
        assert_acc.extend(ass)
        hypo_acc.extend(hyp)

        record["quests"][idx] = {}

        # ---------- build perspective evidence per ROLE type ----------
        # "objective" perspective has only global evidence
        perspective_evidence = {"objective": []}

        for role, holders in players_by_role.items():
            extras = []
            # 1) knows own role: pick one holder (if multiple, all identical for that role)
            for p in holders:
                extras.append(role_is(p, role))

            # 2) special-role knowledge:
            if role == "percival":
                # Percival knows the two Merlin/Morgana candidates
                mm = players_by_role.get("merlin", []) + players_by_role.get("morgana", [])
                if len(mm) == 2:
                    extras.append(percival_mm_pred(mm[0], mm[1]))

            if role == "merlin":
                # Merlin knows all evil
                for evil_role in EVIL_ROLES:
                    for p in players_by_role.get(evil_role, []):
                        extras.append(lambda w, t=p: is_evil(w[t]))

            # Evil roles know their fellow evil players
            if role in EVIL_ROLES:
                for p in players_by_role.get(role, []):
                    for evil_role in EVIL_ROLES:
                        for q in players_by_role.get(evil_role, []):
                            if q != p:
                                extras.append(lambda w, t=q: is_evil(w[t]))

            perspective_evidence[role] = extras

        # ---------- run settings for each perspective ----------
        SETTINGS = [
            ("Strict",    False, False, False, False),
            ("+Assert",   True,  False, False, False),
            ("+HypIG",    True,  True,  True,  False),
            ("+HypM",     True,  True,  False, False),
            ("+TurnIG",   True,  True,  True,  True),
        ]

        for view, extras in perspective_evidence.items():
            record["quests"][idx][view] = {}
            # build base model for this view
            base_model = SDGModel(players, deepcopy(SCHEMA))
            # add global hard + perspective extras
            EVIDENCE_TYPES = {"role_is", "role_not", "evil_at_least"}

            hard_preds = []
            for c in hard_acc:
                if c["type"] in EVIDENCE_TYPES:
                    hard_preds.append(build_pred(c))
            # now add perspective extras
            hard_preds += extras

            for pred in hard_preds:
                base_model.add_evidence(pred)

            cumulative_asserts = list(assert_acc)
            cumulative_hypos   = list(hypo_acc)

            for title, use_assert, use_hyp, auto_w, only_today in SETTINGS:
                model = deepcopy(base_model)
                if use_assert:
                    for c in cumulative_asserts:
                        add_assert(model, c)
                if use_hyp:
                    source = hyp if only_today else cumulative_hypos
                    for c in source:
                        if not auto_w:
                            c = {**c, "auto_weight": False}
                        add_hypo(model, c)

                # robust evaluation
                try:
                    if not use_assert and not use_hyp:
                        post, ent, _ = model.evaluate_hard_only()
                    else:
                        post, ent, _ = model.evaluate_advanced()
                except ValueError:
                    post, ent = {}, {}

                # robust MAP
                try:
                    best = map_assignment(model)
                except ValueError:
                    best = {}

                record["quests"][idx][view][title] = {
                    "posterior": post,
                    "best": best
                }

    return record

# ---------- small helpers reused from earlier solver ----------
def build_pred(c):
    t, a = c["type"], c["args"]
    if t == "role_is":       return role_is(a["player"], a["role"])
    if t == "role_not":      return role_not(a["player"], a["role"])
    if t == "evil_at_least":
        m = a.get("min_fail", a.get("min"))
        return evil_at_least(a["team"], m)
    if t == "team_all_good": return team_all_good(a["team"])
    raise ValueError(t)

def add_assert(model, c):
    t, a = c["type"], c["args"]
    if t == "assert_role_is":
        model.add_assertion(a["speaker"], role_is(a["speaker"], a["role"]))
    elif t == "assert_team_good":
        model.add_assertion(a["speaker"], team_all_good(a["team"]))
    elif t == "assert_role_in":
        tgt_set = a["set"]
        if tgt_set == "evil":
            pred = lambda w, t=a["target"]: is_evil(w[t])
        else:
            pred = lambda w, t=a["target"]: is_good(w[t])
        model.add_assertion(a["speaker"], pred)

def add_hypo(model, c):
    t, a = c["type"], c["args"]
    w  = c.get("weight", 0.2)
    aw = c.get("auto_weight", False)
    if t == "hypo_role_in":
        tgt_set = a["set"]
        if tgt_set == "evil":
            pred = lambda w, t=a["target"]: is_evil(w[t])
        else:
            pred = lambda w, t=a["target"]: is_good(w[t])
        model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=aw)
    elif t == "hypo_team_good":
        model.add_hypothesis(a["speaker"], team_all_good(a["team"]),
                             weight=w, auto_weight=aw)

# ---------- entry ----------
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python avalon_batch_csp_exp.py dataset_processed/ results.jsonl")
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    out  = Path(sys.argv[2]).resolve()

    with out.open("w", encoding="utf-8") as fout:
        for cond in ("Truth", "Lie"):
            subdir = root / cond
            if not subdir.exists():
                continue
            for fp in subdir.glob("*_constraints.json"):
                rec = run_game(fp, cond)
                fout.write(json.dumps(rec) + "\n")
                print(f"[Done] {fp.name}")
    print("All games processed. Results written to", out)
