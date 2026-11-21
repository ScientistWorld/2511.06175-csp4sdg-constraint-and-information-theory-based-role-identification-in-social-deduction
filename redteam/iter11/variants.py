#!/usr/bin/env python3
"""Hardening audit predictors (iteration 11).

Usage: python3 redteam/iter11/variants.py <variant> <input_dir> <output_dir>

Each variant reads <input_dir>/instances.json and writes
<output_dir>/predictions.json in the gym's prediction format, exactly like
scripts/predict.sh.  The audit runs every variant through the unchanged
evaluators by swapping the predictor command.  None of these is the reference.

Honest variants
  reference         the reference predictor (CSP_Strict, CSP_HypIG)
  better_knowledge  CSP4SDG using each viewpoint's complete private knowledge
                    (Merlin also knows who is NOT a visible evil, evil roles who
                    is NOT a teammate, Percival with no Morgana knows Merlin)
  learned_votes     exact posterior under a vote / team-choice / quest-card
                    likelihood fitted on the visible training games
  combined          learned_votes + better_knowledge
  prior             role-count prior only (simple weaker baseline)
  strict_only       CSP_Strict renamed to CSP_HypIG (hypotheses removed)
Shortcuts
  sharpen_onehot    reference posterior replaced by its max-expected-accuracy
                    complete assignment (one-hot)
  sharpen_power     reference posterior raised to power POWER (default 3),
                    re-projected onto the role totals (Sinkhorn)
  constant_ones     probability 1 for every role (not normalised)
  impossible        probability 10 for every role
  empty             empty posterior / best
  malformed         one unknown player
  pool              drop the hardest half of the instances
  empty_map         reference posterior with best = {}
  crash             writes the reference predictions, then exits 1
  arbitrary_world   one-hot on an arbitrary legal world (relabel analogue)
  lookup_visible    looks each instance up in the visible raw logs by its
                    public history and copies the labelled roles when found
  rename            reference predictions under a new method name plus the
                    better_knowledge predictions under another new name
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from method.csp4sdg_avalonlogs import (  # noqa: E402
    Knowledge, extract_constraints, robust_groups, solve_instance,
    posterior_from_scores, _clean,
)

GOOD = {"loyal_follower", "merlin", "percival", "servant"}


# ---------------------------------------------------------------- helpers
def counts_of(inst):
    return {r: int(c) for r, c in inst["role_counts"].items() if int(c) > 0}


def best_assignment(inst, post):
    """Complete legal world maximising sum_p post[p][role] (DP over role counts)."""
    players = list(inst["players"])
    counts = counts_of(inst)
    roles = sorted(counts)
    memo = {}

    def rec(i, rem):
        if i == len(players):
            return 0.0, ()
        key = (i, rem)
        if key in memo:
            return memo[key]
        best = (-1.0, ())
        for j, r in enumerate(roles):
            if rem[j] == 0:
                continue
            nrem = rem[:j] + (rem[j] - 1,) + rem[j + 1:]
            v, rest = rec(i + 1, nrem)
            v += post.get(players[i], {}).get(r, 0.0)
            if v > best[0]:
                best = (v, (r,) + rest)
        memo[key] = best
        return best

    _, assign = rec(0, tuple(counts[r] for r in roles))
    return dict(zip(players, assign))


def sinkhorn(inst, mat, iters=500):
    counts = counts_of(inst)
    players = list(inst["players"])
    m = {p: {r: max(mat.get(p, {}).get(r, 0.0), 1e-300) for r in counts} for p in players}
    for _ in range(iters):
        for p in players:
            s = sum(m[p].values())
            for r in counts:
                m[p][r] /= s
        for r in counts:
            s = sum(m[p][r] for p in players)
            for p in players:
                m[p][r] *= counts[r] / s
    for p in players:
        s = sum(m[p].values())
        for r in counts:
            m[p][r] /= s
    return m


def one_hot(world):
    return {p: {r: 1.0} for p, r in world.items()}


# ------------------------------------------------------- learned likelihood
LIK_PATH = Path(os.environ.get("LEARNED_CACHE", ROOT / "redteam" / "iter11" / "_learned_votes.json"))


def _canon(role):
    return role.strip().lower().replace(" ", "_")


def fit_likelihood(raw_dir: Path):
    """Count statistics from labelled visible games (training only)."""
    vote = defaultdict(lambda: [1.0, 1.0])     # key -> [approve, reject] (Laplace)
    team = defaultdict(lambda: defaultdict(lambda: 1.0))  # (align, n, t) -> {(j, l): count}
    card = defaultdict(lambda: defaultdict(lambda: 1.0))  # (j, req) -> {fails: count}
    exclude = set()
    if os.environ.get("LEARNED_EXCLUDE"):
        exclude = set(Path(os.environ["LEARNED_EXCLUDE"]).read_text().split())
    for fp in sorted(raw_dir.iterdir()):
        if fp.name in exclude:
            continue
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
            names = [p["name"] for p in raw["players"]]
            roles = {r["name"]: _canon(r["role"]) for r in raw["outcome"]["roles"]}
        except Exception:
            continue
        if set(roles) != set(names):
            continue
        n = len(names)
        evil = {p for p, r in roles.items() if r not in GOOD}
        for m in raw["missions"]:
            if m.get("state") not in ("SUCCESS", "FAIL"):
                break
            props = m.get("proposals", [])
            for pi, pr in enumerate(props):
                t = list(pr["team"])
                if not t:
                    continue
                j = len(evil & set(t))
                L = pr["proposer"]
                team[(int(L in evil), n, len(t))][(j, int(L in t))] += 1
                appr = set(pr["votes"])
                hammer = int(pi == 4)
                for v in names:
                    key = (int(v in evil), min(j, 2), int(v in t), hammer, int(L in evil and v in evil))
                    vote[key][0 if v in appr else 1] += 1
            j = len(evil & set(m["team"]))
            card[(j, int(m["failsRequired"]))][int(m["numFails"])] += 1
    out = {
        "vote": {",".join(map(str, k)): v for k, v in vote.items()},
        "team": {",".join(map(str, k)): {f"{a},{b}": c for (a, b), c in d.items()} for k, d in team.items()},
        "card": {",".join(map(str, k)): {str(f): c for f, c in d.items()} for k, d in card.items()},
    }
    return out


def _load_lik():
    if not LIK_PATH.exists():
        LIK_PATH.write_text(json.dumps(fit_likelihood(ROOT / "data" / "avalonlogs_raw")))
    return json.loads(LIK_PATH.read_text())


def _comb(a, b):
    return math.comb(a, b) if 0 <= b <= a else 0


def learned_log_lik(inst, mask, ix, lik):
    n = len(inst["players"])
    k = sum(c for r, c in counts_of(inst).items() if r not in set(inst["good_roles"]))
    ll = 0.0
    for m in inst["missions"]:
        for pi, pr in enumerate(m["proposals"]):
            t = pr["team"]
            if not t:
                continue
            tmask = sum(1 << ix[p] for p in t)
            j = (mask & tmask).bit_count()
            Lb = 1 << ix[pr["proposer"]]
            Le = int(bool(mask & Lb))
            l_in = int(bool(tmask & Lb))
            # team choice: P(j, l | align(L)) / #teams with (j, l) given the evil set
            d = lik["team"].get(f"{Le},{n},{len(t)}")
            if d:
                tot = sum(d.values())
                pjl = d.get(f"{j},{l_in}", 1.0) / tot
                ke = k - Le
                kg = (n - k) - (1 - Le)
                rest = len(t) - l_in
                jj = j - (Le if l_in else 0)
                ways = _comb(ke, jj) * _comb(kg, rest - jj)
                if ways > 0:
                    ll += math.log(pjl) - math.log(ways)
            hammer = int(pi == 4)
            appr = set(pr["approve"])
            for v in inst["players"]:
                vb = 1 << ix[v]
                ve = int(bool(mask & vb))
                key = f"{ve},{min(j, 2)},{int(bool(tmask & vb))},{hammer},{int(Le and ve)}"
                a, r = lik["vote"].get(key, [1.0, 1.0])
                ll += math.log((a if v in appr else r) / (a + r))
        tm = sum(1 << ix[p] for p in m["team"])
        j = (mask & tm).bit_count()
        d = lik["card"].get(f"{j},{int(m['fails_required'])}")
        if d:
            ll += math.log(d.get(str(int(m["num_fails"])), 1e-6) / sum(d.values()))
    return ll


def learned_solve(inst, mode="paper"):
    lik = _load_lik()
    hard, _ = extract_constraints(inst)
    groups, _ = robust_groups(inst, Knowledge(inst, mode), hard)
    ix = {p: i for i, p in enumerate(inst["players"])}
    lls = [learned_log_lik(inst, g["mask"], ix, lik) for g in groups]
    mx = max(lls)
    tau = float(os.environ.get("LEARNED_TEMP", "1.0"))  # chosen on the train slice only
    scores = [math.exp(tau * (x - mx)) for x in lls]
    post, best = posterior_from_scores(inst["players"], groups, scores)
    return {"posterior": _clean(post), "best": best}


# ------------------------------------------------------------- variants
def predict(args):
    variant, inst = args
    iid = inst["instance_id"]
    if variant in ("reference", "crash"):
        return iid, solve_instance(inst)
    if variant == "better_knowledge":
        return iid, solve_instance(inst, knowledge_mode="full")
    if variant == "learned_votes":
        return iid, {"CSP_HypIG": learned_solve(inst, "paper")}
    if variant == "combined":
        return iid, {"CSP_HypIG": learned_solve(inst, "full")}
    if variant == "strict_only":
        ref = solve_instance(inst, settings=("CSP_Strict",))
        return iid, {"CSP_HypIG": ref["CSP_Strict"]}
    counts = counts_of(inst)
    players = list(inst["players"])
    n = len(players)
    ref = solve_instance(inst, settings=("CSP_HypIG",))["CSP_HypIG"]
    if variant == "prior":
        post = {p: {r: c / n for r, c in counts.items()} for p in players}
        return iid, {"CSP_HypIG": {"posterior": post, "best": ref["best"]}}
    if variant == "sharpen_onehot":
        w = best_assignment(inst, ref["posterior"])
        return iid, {"CSP_HypIG": {"posterior": one_hot(w), "best": w}}
    if variant == "sharpen_power":
        gamma = float(os.environ.get("POWER", "3"))
        powered = {p: {r: v ** gamma for r, v in rp.items()} for p, rp in ref["posterior"].items()}
        return iid, {"CSP_HypIG": {"posterior": sinkhorn(inst, powered), "best": ref["best"]}}
    if variant == "constant_ones":
        return iid, {"CSP_HypIG": {"posterior": {p: {r: 1.0 for r in counts} for p in players}, "best": ref["best"]}}
    if variant == "impossible":
        return iid, {"CSP_HypIG": {"posterior": {p: {r: 10.0 for r in counts} for p in players}, "best": ref["best"]}}
    if variant == "empty":
        return iid, {"CSP_HypIG": {"posterior": {}, "best": {}}}
    if variant == "malformed":
        return iid, {"CSP_HypIG": {"posterior": {"UNKNOWN": {r: 1.0 / len(counts) for r in counts}}, "best": {}}}
    if variant == "empty_map":
        return iid, {"CSP_HypIG": {"posterior": ref["posterior"], "best": {}}}
    if variant == "arbitrary_world":
        world = dict(zip(players, [r for r in sorted(counts) for _ in range(counts[r])]))
        return iid, {"CSP_HypIG": {"posterior": one_hot(world), "best": world}}
    if variant == "pool":
        return iid, {"CSP_HypIG": ref}
    if variant == "lookup_visible":
        hit = VISIBLE_INDEX.get(fingerprint(inst))
        if hit is not None and Counter(hit) == Counter(counts):
            world = {p: hit[i] for i, p in enumerate(players)}
            return iid, {"CSP_HypIG": {"posterior": one_hot(world), "best": world}}
        return iid, {"CSP_HypIG": ref}
    if variant == "rename":
        full = solve_instance(inst, settings=("CSP_HypIG",), knowledge_mode="full")["CSP_HypIG"]
        return iid, {"CSP_HypIG": ref, "Copy_Reference": ref, "FullKnowledge_NewName": full}
    raise SystemExit(f"unknown variant {variant}")


# ----------------------------------------------- visible-log lookup shortcut
VISIBLE_INDEX = {}


def fingerprint(inst):
    """Public-history fingerprint invariant to player names (seat order kept)."""
    seat = {p: i for i, p in enumerate(inst["players"])}
    parts = []
    for m in inst["missions"]:
        for pr in m["proposals"]:
            parts.append((seat[pr["proposer"]], tuple(sorted(seat[p] for p in pr["team"])),
                          tuple(sorted(seat[p] for p in pr["approve"]))))
        parts.append(("q", int(m["num_fails"])))
    return hashlib.sha256(repr((len(seat), parts)).encode()).hexdigest()


def build_visible_index():
    idx = {}
    for fp in sorted((ROOT / "data" / "avalonlogs_raw").iterdir()):
        try:
            raw = json.loads(fp.read_text(encoding="utf-8"))
            names = [p["name"] for p in raw["players"]]
            seat = {p: i for i, p in enumerate(names)}
            roles = {r["name"]: _canon(r["role"]) for r in raw["outcome"]["roles"]}
            parts = []
            for m in raw["missions"]:
                if m.get("state") not in ("SUCCESS", "FAIL"):
                    break
                for pr in m.get("proposals", []):
                    parts.append((seat[pr["proposer"]], tuple(sorted(seat[p] for p in pr["team"])),
                                  tuple(sorted(seat[p] for p in pr["votes"]))))
                parts.append(("q", int(m["numFails"])))
                key = hashlib.sha256(repr((len(names), parts)).encode()).hexdigest()
                idx[key] = [roles[nm] for nm in names]
        except Exception:
            continue
    return idx


def _init(variant):
    global VISIBLE_INDEX
    if variant == "lookup_visible":
        VISIBLE_INDEX = build_visible_index()


def main():
    variant, inp, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if variant == "forge_scores":
        # Write a forged score file where the evaluator will write, then predict normally.
        forged = {"experiments": {f"avalonlogs_{n}player": {"results": {"CSP_HypIG": {
            f"{v}_brier": 0.0 for v in ("Obj", "MRL", "PCV", "MRG", "LSV", "EVM")}}} for n in range(5, 11)}}
        (ROOT / "scoring" / "scores_test.json").write_text(json.dumps(forged))
        variant = "reference"
    if variant == "read_heldout":
        # Try to read the hidden file while the method runs; record the outcome.
        try:
            (ROOT / "eval" / "test" / "heldout.dat").read_bytes()
            msg = "readable"
        except OSError as exc:
            msg = f"unreadable: {type(exc).__name__}"
        (ROOT / "redteam" / "iter11" / "read_heldout_probe.txt").write_text(msg + "\n")
        variant = "reference"
    data = json.loads((inp / "instances.json").read_text())
    insts = data["instances"]
    if variant == "pool":
        insts = sorted(insts, key=lambda x: x["instance_id"])[: len(insts) // 2]
    if variant in ("learned_votes", "combined"):
        _load_lik()
    if variant == "lookup_visible":
        idx = build_visible_index()
        full = sum(1 for i in insts if fingerprint(i) in idx)
        same = sum(1 for i in insts if fingerprint(i) in idx and Counter(idx[fingerprint(i)]) == Counter(counts_of(i)))
        (ROOT / "redteam" / "iter11" / "lookup_hits.txt").write_text(
            f"instances {len(insts)}; public-history matches in visible logs {full}; "
            f"matches with the same role composition {same}\n")
    workers = int(os.environ.get("PREDICT_WORKERS", min(8, os.cpu_count() or 1)))
    with Pool(workers, initializer=_init, initargs=(variant,)) as pool:
        preds = dict(pool.imap(predict, [(variant, i) for i in insts], chunksize=8))
    out.mkdir(parents=True, exist_ok=True)
    (out / "predictions.json").write_text(json.dumps({"predictions": preds}))
    if variant == "crash":
        sys.exit(1)


if __name__ == "__main__":
    main()
