"""
Convert *all* files in <in_dir> to SDG-framework constraints JSON and
write them to <out_dir>.
Files that cannot be parsed as valid Avalon-Logs JSON are skipped (with a
warning).

Usage
-----
    python batch_convert_structured.py avalon_logs_raw avalon_logs
"""

import json
import sys
import uuid
import random
import pathlib
from typing import List, Dict, Any

# ---------------- constants / helpers copied from convert_structured.py ---- #
GOOD_ROLES = {"LOYAL FOLLOWER", "MERLIN", "PERCIVAL", "SERVANT"}
EVIL_ROLES = {"ASSASSIN", "MORDRED", "MORGANA", "MINION"}

W_STRONG = 0.50
W_REJECT = 0.20
W_WEAK   = 0.10
RNG = random.Random(0)


def map_true_roles(out_roles: List[Dict[str, Any]]) -> Dict[str, str]:
    return {r["name"]: r["role"].lower().replace(" ", "_") for r in out_roles}


def build_schema(out_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    good:   List[str]      = []
    for r in out_roles:
        key = r["role"].lower().replace(" ", "_")
        counts[key] = counts.get(key, 0) + 1
        if r["role"] in GOOD_ROLES:
            good.append(key)
    return {"role_counts": counts, "good_roles": good}


def split_votes(raw_votes: Any, players: List[str]):
    if isinstance(raw_votes, dict):
        approved = [p for p, v in raw_votes.items() if v]
        rejected = [p for p, v in raw_votes.items() if not v]
    else:            # list of approvers
        approved = raw_votes
        rejected = [p for p in players if p not in approved]
    return approved, rejected


def mission_to_constraints(m: Dict[str, Any], idx: int,
                           players: List[str]) -> Dict[str, Any]:
    evidence, hypotheses = [], []

    if m["state"] in ("SUCCESS", "FAIL") and m["numFails"] > 0:
        evidence.append({
            "type": "evil_at_least",
            "args": {"team": m["team"], "min_fail": m["numFails"]}
        })

    for prop in m.get("proposals", []):
        team      = prop["team"]
        proposer  = prop["proposer"]

        # proposer strongly trusts the team
        hypotheses.append({
            "type": "hypo_team_good",
            "args": {"speaker": proposer, "team": team},
            "weight": W_STRONG
        })

        approved, rejected = split_votes(prop.get("votes", []), players)

        for a in approved:   # weak positive
            hypotheses.append({
                "type": "hypo_team_good",
                "args": {"speaker": a, "team": team},
                "weight": W_WEAK
            })
        for r in rejected:   # weak negative (pick any member as suspect)
            if team:
                hypotheses.append({
                    "type": "hypo_role_in",
                    "args": {"speaker": r,
                             "target": RNG.choice(sorted(team)),
                             "set": "evil"},
                    "weight": W_REJECT
                })

    return {
        "quest": idx,
        "constraints": {
            "evidence": evidence,
            "phenomenon": [],
            "assertions": [],
            "hypotheses": hypotheses
        }
    }


def convert_file(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """
    Try to convert one file.  Returns True on success, False if skipped.
    """
    try:
        game = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:          # not a JSON file or malformed
        print(f"[SKIP] {src.name}: cannot parse JSON ({e})")
        return False

    # minimal validity checks
    if "players" not in game or "missions" not in game or "outcome" not in game:
        print(f"[SKIP] {src.name}: missing required keys")
        return False

    players = [p["name"] for p in game["players"]]
    true_role_map = map_true_roles(game["outcome"]["roles"])
    schema        = build_schema(game["outcome"]["roles"])

    quests = []
    for idx, mission in enumerate(game["missions"], start=1):
        if mission.get("state") == "PENDING":
            break
        quests.append(mission_to_constraints(mission, idx, players))

    out_data = {
        "id": str(uuid.uuid4()),
        "players": [{"name": p, "role": true_role_map.get(p, "unknown")}
                    for p in players],
        "schema": schema,
        "quests": quests
    }

    dst.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"[OK] {src.name} → {dst.name}")
    return True
# --------------------------------------------------------------------------- #


def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_convert_avalon_logs.py <in_dir> <out_dir>")
        sys.exit(1)

    in_dir  = pathlib.Path(sys.argv[1]).resolve()
    out_dir = pathlib.Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    for fp in in_dir.iterdir():
        if fp.is_file():
            out_fp = out_dir / (fp.stem + "_constraints.json")
            if convert_file(fp, out_fp):
                converted += 1

    print(f"✓ Finished.  {converted} file(s) converted.")


if __name__ == "__main__":
    main()
