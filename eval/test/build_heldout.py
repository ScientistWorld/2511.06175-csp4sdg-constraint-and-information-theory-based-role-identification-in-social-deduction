#!/usr/bin/env python3
"""
Build eval/test/heldout.dat from raw AvalonLogs files (run once by the gym
maintainers; kept for provenance).

  python3 eval/test/build_heldout.py <raw_dir> <test_file_list_out>

Half of the valid games of every player count (chosen with the seed below)
become the hidden test set.  Each test game yields exactly ONE instance: the
public history up to a uniformly sampled completed mission, seen from ONE
viewpoint (views balanced within each player count).  One instance per game
prevents combining several viewpoints' private information, or a later
prefix, of the same game.  Player names are replaced by seat labels P1..Pn.

The raw files of the selected games must then be removed from the visible
data; their hashed names go to eval/test/heldout_ids.txt so that
scripts/download.sh can drop them from a fresh archive download.
"""

import base64
import hashlib
import json
import os
import random
import sys
import zlib
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRET = b"avalonlogs-heldout-v2/4b1f0c9e7d"
SEED = "avalonlogs-heldout-v2/split-and-instances/91c3"
GOOD = {"loyal_follower", "merlin", "percival", "servant"}
VIEW_ORDER = ["objective", "merlin", "percival", "morgana", "loyal_follower", "evil_minion"]


def canon(role):
    return role.strip().lower().replace(" ", "_")


def load_game(path):
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict) or not {"players", "missions", "outcome"} <= set(raw):
        return None
    names = [p["name"] for p in raw["players"]]
    roles = {r["name"]: canon(r["role"]) for r in raw["outcome"].get("roles", [])}
    if len(set(names)) != len(names) or set(roles) != set(names) or not 5 <= len(names) <= 10:
        return None
    done = []
    for m in raw.get("missions", []):
        if m.get("state") not in ("SUCCESS", "FAIL"):
            break
        done.append(m)
    if not done:
        return None
    ok = set(names)
    for m in done:
        if not set(m.get("team", [])) <= ok or "numFails" not in m:
            return None
        for pr in m.get("proposals", []):
            if pr.get("proposer") not in ok or not set(pr.get("team", [])) <= ok \
                    or not set(pr.get("votes", [])) <= ok:
                return None
    return {"names": names, "roles": roles, "missions": done}


def build_instance(game, q, view, rng, instance_id):
    names = game["names"]
    alias = {n: f"P{i + 1}" for i, n in enumerate(names)}
    counts = Counter(game["roles"].values())
    missions = []
    for idx, m in enumerate(game["missions"][:q], 1):
        props = []
        for pr in m.get("proposals", []):
            appr = set(pr.get("votes", []))
            props.append({
                "proposer": alias[pr["proposer"]],
                "team": [alias[p] for p in pr["team"]],
                "approve": [alias[p] for p in names if p in appr],
                "reject": [alias[p] for p in names if p not in appr],
                "approved": pr.get("state") == "APPROVED",
            })
        missions.append({"mission": idx, "team_size": m["teamSize"], "fails_required": m["failsRequired"],
                         "proposals": props, "team": [alias[p] for p in m["team"]],
                         "num_fails": m["numFails"], "result": m["state"]})
    seat = {alias[n]: i for i, n in enumerate(names)}
    lab = {alias[n]: r for n, r in game["roles"].items()}
    spec = {"perspective": view}
    if view != "objective":
        viewers = sorted([p for p, r in lab.items() if r == view], key=seat.get)
        viewer = viewers[rng.randrange(len(viewers))]
        spec.update({"viewer": viewer, "viewer_role": view})
        if view == "merlin":
            spec["sees_evil"] = sorted([p for p, r in lab.items() if r not in GOOD and r != "mordred"], key=seat.get)
        elif view == "percival":
            spec["merlin_candidates"] = sorted([p for p, r in lab.items() if r in ("merlin", "morgana")], key=seat.get)
        elif view in ("morgana", "evil_minion"):
            spec["sees_evil"] = sorted([p for p, r in lab.items()
                                        if r not in GOOD and r != "oberon" and p != viewer], key=seat.get)
    inst = {"instance_id": instance_id, "n_players": len(names),
            "players": [alias[n] for n in names],
            "role_counts": dict(sorted(counts.items())),
            "good_roles": sorted(r for r in counts if r in GOOD),
            "evil_roles": sorted(r for r in counts if r not in GOOD),
            "missions": missions, "view": spec}
    return inst, lab


def build_instances(games, rng, prefix):
    by_size = {}
    for label, g in sorted(games, key=lambda x: x[0]):
        by_size.setdefault(len(g["names"]), []).append((label, g))
    insts, labels = [], {}
    for n in sorted(by_size):
        items = by_size[n]
        rng.shuffle(items)
        vc = Counter()
        for _label, g in items:
            present = set(g["roles"].values())
            av = [v for v in VIEW_ORDER if v == "objective" or v in present]
            low = min(vc[v] for v in av)
            view = rng.choice([v for v in av if vc[v] == low])
            vc[view] += 1
            q = rng.randint(1, len(g["missions"]))
            iid = f"{prefix}{rng.getrandbits(48):012x}"
            inst, lab = build_instance(g, q, view, rng, iid)
            insts.append(inst)
            labels[iid] = lab
    rng.shuffle(insts)
    return insts, labels


def encode_section(section, obj):
    plain = zlib.compress(json.dumps(obj, separators=(",", ":")).encode("utf-8"), 9)
    key = hashlib.sha256(SECRET + section.encode()).digest()
    ks = bytearray()
    ctr = 0
    while len(ks) < len(plain):
        ks += hashlib.sha256(key + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    enc = (int.from_bytes(plain, "big") ^ int.from_bytes(bytes(ks[:len(plain)]), "big")).to_bytes(len(plain), "big")
    return base64.b64encode(enc).decode("ascii")


def main():
    raw_dir, list_out = Path(sys.argv[1]), Path(sys.argv[2])
    games = []
    for fp in sorted(raw_dir.iterdir()):
        g = load_game(fp)
        if g is not None:
            games.append((fp.name, g))
    rng = random.Random(SEED)
    test = []
    for n in range(5, 11):
        items = sorted([x for x in games if len(x[1]["names"]) == n], key=lambda x: x[0])
        rng.shuffle(items)
        test += items[: (len(items) + 1) // 2]
    insts, labels = build_instances(test, rng, "t")
    blob = "\n".join([
        "format: avalonlogs-heldout-v2",
        "inputs: " + encode_section("inputs", {"instances": insts}),
        "labels: " + encode_section("labels", labels),
    ]) + "\n"
    (HERE / "heldout.dat").write_text(blob)
    ids = sorted(hashlib.sha256(name.encode()).hexdigest() for name, _ in test)
    (HERE / "heldout_ids.txt").write_text("\n".join(ids) + "\n")
    list_out.write_text("\n".join(sorted(name for name, _ in test)) + "\n")
    sizes = Counter(len(g["names"]) for _, g in test)
    print(f"valid games {len(games)}; test games {len(test)} {dict(sorted(sizes.items()))}")
    print("sha256", hashlib.sha256((HERE / "heldout.dat").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
