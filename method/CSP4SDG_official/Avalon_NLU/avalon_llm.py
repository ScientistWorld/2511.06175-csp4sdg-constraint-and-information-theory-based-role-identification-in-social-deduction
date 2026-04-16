"""
Constraint extraction helper for Avalon-NLU logs.

Reads a raw JSON game (with users/messages structure), groups dialogue by quest,
and asks an LLM to emit evidence / phenomenon / assertion / hypothesis objects
in the grammar described in the paper.  The resulting constraints are written
next to the raw file with the suffix `_constraints.json`.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import openai


def _require_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set; "
            "please export your OpenAI API key before running avalon_llm."
        )
    return key


def _group_by_quest(messages: Dict[str, Dict]) -> Dict[int, List[Dict]]:
    grouped = defaultdict(list)
    for mid in sorted(messages, key=lambda k: int(k)):
        msg = messages[mid]
        grouped[msg["quest"]].append(msg)
    return grouped


def _build_transcript(block: List[Dict]) -> str:
    lines = []
    for msg in block:
        speaker = msg["player"]
        text = msg["msg"].replace("\n", " ")
        lines.append(f"[{speaker}] {text}")
    return "\n".join(lines)


def _call_llm(prompt_head: str, transcript: str, model: str) -> Dict:
    response = openai.ChatCompletion.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": prompt_head},
            {"role": "user", "content": transcript},
        ],
    )
    content = response.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse LLM JSON output: {content[:200]}..."
        ) from exc


def process_game(json_path: str | os.PathLike, use_ig: bool = True, model: str = "gpt-4o-mini") -> Path:
    """
    Convert one raw Avalon game log to constraints JSON.

    Args:
        json_path: path to the raw log.
        use_ig: whether to mark hypotheses with `auto_weight=True`.
        model: OpenAI model name (must support chat completions).

    Returns:
        Path to the generated constraints JSON.
    """

    openai.api_key = _require_api_key()

    src = Path(json_path).resolve()
    data = json.loads(src.read_text(encoding="utf-8"))

    users = list(data["users"].values())
    player_names = [u["name"] for u in users]

    quests_raw = _group_by_quest(data["messages"])

    prompt_file = Path(__file__).with_name("prompt_head.txt")
    prompt_head = prompt_file.read_text(encoding="utf-8").strip()
    prompt_head += (
        "\n\nVALID PLAYERS: ["
        + ", ".join(player_names)
        + "]\nEnsure every name matches exactly."
    )

    output = {
        "players": [{"name": u["name"], "role": u["role"]} for u in users],
        "quests": [],
    }

    for quest_id, block in quests_raw.items():
        transcript = _build_transcript(block)
        constraints = _call_llm(prompt_head, transcript, model)

        if use_ig:
            for hypo in constraints.get("hypotheses", []):
                hypo["auto_weight"] = True

        output["quests"].append(
            {
                "quest": int(quest_id),
                "constraints": constraints,
            }
        )

    dst = src.with_name(src.stem + "_constraints.json")
    dst.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return dst


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python avalon_llm.py <raw_game.json>")
        raise SystemExit(1)

    for target in sys.argv[1:]:
        produced = process_game(target, use_ig=True)
        print(f"[OK] {target} -> {produced}")
