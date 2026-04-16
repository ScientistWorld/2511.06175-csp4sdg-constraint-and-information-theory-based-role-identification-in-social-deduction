"""
Convert every processed game JSON (with rounds & transcript) into
<game_id>_constraints.json via LLM extraction.

Input  directory: mafia_dataset_processed/{Truth,Lie}/*.json
Output directory: mafia_constraints/{Truth,Lie}/
Prompt file      : system prompt template for LLM extraction

Usage:
    python build_mafia_constraints.py mafia_dataset mafia_dataset_constraints prompt_head.txt
"""

import os, sys, json, re, random, time
from pathlib import Path
import openai

# ---------------- configs ---------------- #
MODEL       = "gpt-4o-mini"
TEMP        = 0.0
openai.api_key = os.getenv("OPENAI_API_KEY", "")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")

# ---------- helper: read prompt ----------- #
def load_system_prompt(path: Path, player_names):
    with open(path, encoding="utf-8") as f:
        tpl = f.read().strip()
    # optional player list injection
    return tpl.replace("{PLAYERS}", ", ".join(player_names))

# ---------- LLM call with retry ----------- #
def ask_llm(system_prompt, transcript, retries=4):
    for attempt in range(retries):
        try:
            resp = openai.ChatCompletion.create(
                model=MODEL,
                temperature=TEMP,
                messages=[
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":transcript}
                ]
            )
            txt = resp.choices[0].message.content.strip()
            return json.loads(re.search(r"\{.*\}", txt, flags=re.S).group(0))
        except Exception as e:
            wait = 2**attempt + random.random()
            print(f"   [retry {attempt+1}] {e}. wait {wait:.1f}s")
            time.sleep(wait)
    print("   ⚠️  extraction failed; returning empty constraints.")
    return {"evidence":[],"phenomenon":[],"assertions":[],"hypotheses":[]}

# ---------- per-game processing ----------- #
def process_game(game_fp: Path, out_dir: Path, prompt_path: Path):
    game = json.loads(game_fp.read_text(encoding="utf-8"))
    players = game["players"]
    player_names = [p["name"] for p in players]

    system_prompt_template = load_system_prompt(prompt_path, player_names)

    days_out = []
    for rd in game["rounds"]:
        idx = rd["round"]
        transcript = "\n".join(f"[{m['speaker']}] {m['text']}"
                               for m in rd["transcript"])
        print(f"   · Round {idx:02d}: {len(rd['transcript'])} lines")
        constraints = ask_llm(system_prompt_template, transcript)
        days_out.append({"day": idx, **constraints})

    out_json = {"players": players, "days": days_out}
    out_dir.mkdir(parents=True, exist_ok=True)
    out_fp = out_dir / f"{game_fp.stem}_constraints.json"
    out_fp.write_text(json.dumps(out_json, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"   ✔ saved {out_fp.relative_to(out_dir.parent)}")

# ---------- main -------------------------- #
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python build_mafia_constraints.py "
              "<processed_root> <out_root> <prompt_file>")
        sys.exit(1)

    proc_root = Path(sys.argv[1]).resolve()
    out_root  = Path(sys.argv[2]).resolve()
    prompt_file = Path(sys.argv[3]).resolve()

    if not prompt_file.exists():
        print("Prompt file not found:", prompt_file); sys.exit(1)

    for cond in ("Truth", "Lie"):
        for fp in (proc_root/cond).glob("*.json"):
            print(f"[Game] {fp.name} ({cond})")
            process_game(fp, out_root/cond, prompt_file)
