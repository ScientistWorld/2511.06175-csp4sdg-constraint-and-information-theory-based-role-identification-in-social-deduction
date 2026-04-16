"""
Convert raw AvalonLogs JSON files to CSP constraint format.

This script implements the same conversion logic as the paper's
batch_convert_structured.py, adapted for use as a data loader.

Usage:
    python convert_avalonlogs.py <raw_dir> <output_dir> [--sample N]
"""

import json
import random
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional

# Manual hypothesis weights from the paper
W_STRONG = 0.50  # proposer trusting their own team
W_REJECT = 0.20  # rejection vote → suspect
W_WEAK = 0.10    # weak support / approval vote

RNG = random.Random(42)  # fixed seed for reproducibility


GOOD_ROLES = {"LOYAL FOLLOWER", "MERLIN", "PERCIVAL", "SERVANT"}
EVIL_ROLES = {"ASSASSIN", "MORDRED", "MORGANA", "MINION"}


def map_true_roles(out_roles: List[Dict[str, Any]]) -> Dict[str, str]:
    return {r["name"]: r["role"].lower().replace(" ", "_") for r in out_roles}


def build_schema(out_roles: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    good: List[str] = []
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
    else:
        approved = raw_votes
        rejected = [p for p in players if p not in approved]
    return approved, rejected


def mission_to_constraints(
    m: Dict[str, Any],
    idx: int,
    players: List[str],
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Convert a single mission to constraint dict."""
    if rng is None:
        rng = RNG
    evidence, hypotheses = [], []

    # Evidence: quest failure implies at least numFails evil members
    if m.get("state") in ("SUCCESS", "FAIL") and m.get("numFails", 0) > 0:
        evidence.append({
            "type": "evil_at_least",
            "args": {"team": m["team"], "min_fail": m["numFails"]},
        })

    for prop in m.get("proposals", []):
        team = prop["team"]
        proposer = prop["proposer"]

        if not team:
            continue

        # Proposer strongly trusts their team
        hypotheses.append({
            "type": "hypo_team_good",
            "args": {"speaker": proposer, "team": team},
            "weight": W_STRONG,
        })

        approved, rejected = split_votes(prop.get("votes", []), players)

        # Approved voters weakly trust the team
        for a in approved:
            hypotheses.append({
                "type": "hypo_team_good",
                "args": {"speaker": a, "team": team},
                "weight": W_WEAK,
            })

        # Rejected voters suspect a team member
        for r in rejected:
            team_candidates = [p for p in team if p != r]
            if team_candidates:
                target = rng.choice(sorted(team_candidates))
                hypotheses.append({
                    "type": "hypo_role_in",
                    "args": {"speaker": r, "target": target, "set": "evil"},
                    "weight": W_REJECT,
                })

    return {
        "quest": idx,
        "constraints": {
            "evidence": evidence,
            "phenomenon": [],
            "assertions": [],
            "hypotheses": hypotheses,
        },
    }


def convert_file(src: Path) -> Optional[Dict]:
    """Convert one raw AvalonLogs file to constraint format."""
    try:
        game = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[SKIP] {src.name}: cannot parse JSON ({e})")
        return None

    if "players" not in game or "missions" not in game or "outcome" not in game:
        print(f"[SKIP] {src.name}: missing required keys")
        return None

    players = [p["name"] for p in game["players"]]
    true_role_map = map_true_roles(game["outcome"]["roles"])
    schema = build_schema(game["outcome"]["roles"])

    quests = []
    for idx, mission in enumerate(game["missions"], start=1):
        if mission.get("state") == "PENDING":
            break
        quests.append(mission_to_constraints(mission, idx, players, RNG))

    out_data = {
        "id": str(uuid.uuid4()),
        "players": [
            {"name": p, "role": true_role_map.get(p, "unknown")}
            for p in players
        ],
        "schema": schema,
        "quests": quests,
    }
    return out_data


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert AvalonLogs to CSP constraints")
    parser.add_argument("raw_dir", type=str)
    parser.add_argument("output_dir", type=str)
    parser.add_argument("--sample", type=int, default=None,
                        help="Randomly sample N files")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--size-filter", type=int, nargs="+", default=None,
                        help="Only include games with these player counts")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = [fp for fp in raw_dir.iterdir() if fp.is_file()]
    rng = random.Random(args.seed)

    if args.sample:
        files = rng.sample(files, min(args.sample, len(files)))

    # Filter by game size if requested
    if args.size_filter:
        filtered = []
        for fp in files:
            try:
                game = json.loads(fp.read_text(encoding="utf-8"))
                n_players = len(game.get("players", []))
                if n_players in args.size_filter:
                    filtered.append(fp)
            except Exception:
                pass
        files = filtered

    print(f"Converting {len(files)} files...")
    converted = 0
    for fp in files:
        result = convert_file(fp)
        if result is None:
            continue
        dst = out_dir / (fp.stem + "_constraints.json")
        dst.write_text(json.dumps(result, indent=2), encoding="utf-8")
        converted += 1

    print(f"Done. {converted}/{len(files)} files converted -> {out_dir}")


if __name__ == "__main__":
    main()
