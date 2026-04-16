"""
Run LLM-only and LLM+CSP experiments for every raw game under:
  dataset/{Truth,Lie}/

Outputs per-game, per-perspective, per-setting, per-chat JSON, in:
  output_dir/{Truth,Lie}/<file>_<mode>_<setting>_<chat>_<view>_<quest>.json

Before running each individual experiment, check if its output file already exists;
if so, skip it. Print the parameters of each experiment as you run it.

Usage:
    python avalon_batch_llm_exp.py dataset/ dataset_processed/ dataset_llm/
"""

import os
import sys
import json
import re
import textwrap
from pathlib import Path
from collections import defaultdict
import openai

from sdg_framework import SDGModel
from avalon_board import SCHEMA, role_is, role_not, evil_at_least, team_all_good

openai.api_key = os.getenv("OPENAI_API_KEY", "")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")

# ----------------- CSP settings definition -----------------
CSP_SETTINGS = [
    ("Strict",  False, False, False, False),
    ("+Assert", True,  False, False, False),
    ("+HypIG",  True,  True,  True,  False),
    ("+HypM",   True,  True,  False, False),
    ("TurnIG",  True,  True,  True,  True),
]

# ----------------- utilities -----------------
def load_raw(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    users = {u["name"]: u for u in data["users"].values()}
    messages = {int(k): v for k, v in data["messages"].items()}
    return users, messages

def group_by_quest(messages: dict):
    quests = defaultdict(list)
    for mid in sorted(messages):
        msg = messages[mid]
        quests[msg["quest"]].append(msg)
    return quests

def build_transcript(block: list):
    return "\n".join(f"[{m['player']}] {m['msg'].replace(chr(10), ' ')}" for m in block)

def safe_json_parse(text: str):
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except:
        return {}

# ----------------- perspective evidence -----------------
GOOD_ROLES = {"merlin", "percival", "servant"}
EVIL_ROLES = {"assassin", "morgana"}

def perspective_evidence(view: str, role_of: dict):
    ev = []
    if view != "objective":
        # knows own role
        for p, r in role_of.items():
            if r == view:
                ev.append(role_is(p, r))
        # special knowledge
        if view == "merlin":
            for p, r in role_of.items():
                if r in EVIL_ROLES:
                    ev.append(lambda w, p=p: w[p] in EVIL_ROLES)
        if view == "percival":
            mm = [p for p, r in role_of.items() if r in {"merlin", "morgana"}]
            if len(mm) == 2:
                ev.append(lambda w, mm=mm: set(w[p] for p in mm) == {"merlin", "morgana"})
        if view in EVIL_ROLES:
            # know fellow evils
            for p, r in role_of.items():
                if r in EVIL_ROLES and r != view:
                    ev.append(lambda w, p=p: w[p] in EVIL_ROLES)
    return ev

# ----------------- CSP runner -----------------
def run_csp_for_setting(view, setting, hard_acc, assert_acc, hypo_acc, current_hyp, players, role_of):
    _, use_assert, use_hyp, auto_w, only_today = setting

    model = SDGModel(players, SCHEMA)
    for c in hard_acc:
        if c["type"] in {"role_is", "role_not", "evil_at_least"}:
            model.add_evidence(build_pred(c))
    for pr in perspective_evidence(view, role_of):
        model.add_evidence(pr)

    if use_assert:
        for c in assert_acc:
            add_assert(model, c)

    if use_hyp:
        hyps = current_hyp if only_today else hypo_acc
        for c in hyps:
            if not auto_w:
                c = {**c, "auto_weight": False}
            add_hypo(model, c)

    try:
        if not use_assert and not use_hyp:
            post, _, _ = model.evaluate_hard_only()
        else:
            post, _, _ = model.evaluate_advanced()
    except ValueError:
        post = {}
    try:
        best = compute_map(model)
    except:
        best = {}
    return post, best

def compute_map(model: SDGModel):
    import math
    best, sc = {}, -math.inf
    for w in model._worlds():
        m = sum(1 for s in model.mul_soft if s.func(w))
        s = sum(s.weight for s in model.add_soft if s.func(w))
        score = m * math.log(model.A_base) + math.log(1 + s)
        if score > sc:
            sc, best = score, w
    return best

# ----------------- constraint helpers -----------------
def build_pred(c):
    t, a = c["type"], c["args"]
    if t == "role_is": return role_is(a["player"], a["role"])
    if t == "role_not": return role_not(a["player"], a["role"])
    if t == "evil_at_least":
        k = a.get("min_fail", a.get("min"))
        return evil_at_least(a["team"], k)
    if t == "team_all_good": return team_all_good(a["team"])
    raise ValueError(t)

def add_assert(model, c):
    t, a = c["type"], c["args"]
    if t == "assert_role_is":
        model.add_assertion(a["speaker"], role_is(a["speaker"], a["role"]))
    if t == "assert_team_good":
        model.add_assertion(a["speaker"], team_all_good(a["team"]))
    if t == "assert_role_in":
        if a["set"] == "evil":
            model.add_assertion(a["speaker"], lambda w, p=a["target"]: w[p] in EVIL_ROLES)
        else:
            model.add_assertion(a["speaker"], lambda w, p=a["target"]: w[p] in GOOD_ROLES)

def add_hypo(model, c):
    t, a = c["type"], c["args"]
    w = c.get("weight", 0.2); aw = c.get("auto_weight", False)
    if t == "hypo_role_in":
        pred = (lambda w, p=a["target"]: w[p] in EVIL_ROLES) if a["set"] == "evil" \
               else (lambda w, p=a["target"]: w[p] in GOOD_ROLES)
        model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=aw)
    if t == "hypo_team_good":
        model.add_hypothesis(a["speaker"], team_all_good(a["team"]), weight=w, auto_weight=aw)

# ----------------- prompt builder -----------------
SYS_JSON = "You are an impartial Avalon analyst. Respond ONLY with a single JSON object."

def build_prompt(view: str,
                 role_of: dict,
                 players: list,
                 quest_idx: int,
                 events_desc: str,
                 chat_text: str,
                 chat_global: bool,
                 mode: str,
                 setting=None,
                 csp_post=None,
                 csp_best=None) -> str:
    role_keys = list(SCHEMA.role_counts.keys())
    roles_str = ", ".join(role_keys)

    if view == "objective":
        pdesc = "You have NO hidden information."
    else:
        pdesc = f"You are **{view.upper()}**; your true role is {view}."
        if view == "merlin":
            evils = [p for p, r in role_of.items() if r in EVIL_ROLES]
            pdesc += f" You know these players are evil: {', '.join(evils)}."
        elif view == "percival":
            mm = [p for p, r in role_of.items() if r in {"merlin", "morgana"}]
            if len(mm) == 2:
                pdesc += f" You know exactly two players {mm[0]} and {mm[1]} are {{Merlin, Morgana}}."
        elif view in EVIL_ROLES:
            mates = [p for p, r in role_of.items() if r in EVIL_ROLES and r != view]
            if mates:
                pdesc += f" You know your evil teammate(s): {', '.join(mates)}."

    prompt = f"""{SYS_JSON}

## Quest {quest_idx}
### Perspective
{pdesc}

### Events up to now
{events_desc}

### Chat ({'global' if chat_global else 'current quest'})
{chat_text}

### Possible roles
{roles_str}
"""

    if mode == "llm_csp" and setting:
        prompt += f"""\n### CSP Assistance
Setting: {setting[0]}
Posterior (JSON): {json.dumps(csp_post)}
Best assignment: {json.dumps(csp_best)}\n"""

    role_counts_json = json.dumps(SCHEMA.role_counts)
    prompt += textwrap.dedent(f"""
        ### Task

        • Predict a full probability distribution over roles for **each player**.
          Output "posterior": {{ "<player>": {{ "<role>":prob,... }} }}.
          Probabilities per player must sum to 1.

        • Produce a **legal** "best" assignment mapping each player to one role,
          matching global role counts: {role_counts_json}.

        • Return **only** a JSON object with keys "posterior" and "best".

        Begin.
    """)
    return prompt

# ----------------- main driver -----------------
def run_experiment(raw_path: Path, out_dir: Path, proc_dir: Path):
    constr_fp = proc_dir / raw_path.parent.name / f"{raw_path.stem}_constraints.json"
    quest_constraints = {}
    if constr_fp.exists():
        c_data = json.loads(constr_fp.read_text(encoding="utf-8"))
        # converter stores a *list* of quests
        quest_constraints = {q["quest"]: q["constraints"] for q in c_data["quests"]}
    else:
        print(f"[WARN] constraints file missing -> pure-LLM only  ({constr_fp.name})")

    users, msgs = load_raw(raw_path)
    players = list(users.keys())
    role_of = {p: users[p]["role"].lower().replace(" ", "_") for p in players}

    # 1. group all messages by quest
    msgs_by_quest = group_by_quest(msgs)

    # 2. split system vs player messages
    events_by_quest = {}
    chat_by_quest   = {}
    for qid, block in msgs_by_quest.items():
        events_by_quest[qid] = [m for m in block if m["player"].lower()=="system"]
        chat_by_quest[qid]   = [m for m in block if m["player"].lower()!="system"]

    # 3. accumulators for CSP constraints (if needed)
    hard_acc, assert_acc, hypo_acc = [], [], []

    # 4. maintain cumulative lists
    cumulative_events = []
    cumulative_chat   = []

    views = ["objective"] + sorted(set(role_of.values()))

    for qid in sorted(msgs_by_quest):
        # update cumulative events & chat
        cumulative_events.extend(events_by_quest[qid])
        cumulative_chat.extend(chat_by_quest[qid])
        # prepare textual snippets
        events_desc = build_transcript(cumulative_events)
        # LLM-only modes will choose between global vs turn chat
        # LLM+CSP TurnIG also uses turn chat
        qc = quest_constraints.get(qid)
        if qc:
            hard_acc.extend(qc.get("evidence", []) + qc.get("phenomenon", []))
            assert_acc.extend(qc.get("assertions", []))
            hypo_acc.extend(qc.get("hypotheses", []))
            quest_hyp = qc.get("hypotheses", [])
        else:
            quest_hyp = []

        # --- LLM-only experiments ---
        for chat_mode in ("global", "turn"):
            chat_log = build_transcript(
                cumulative_chat if chat_mode == "global"
                else chat_by_quest[qid]
            )
            for view in views:
                mode = "llm"
                fname = f"{raw_path.stem}_{mode}_{chat_mode}_{view}_{qid}.json"
                out_fp = out_dir / raw_path.parent.name / fname
                if out_fp.exists():
                    print(f"[SKIP] {fname}")
                    continue

                print(f"[RUN] File={raw_path.name} | Mode=LLM-only | Chat={chat_mode} | "
                      f"View={view} | Quest={qid}")
                prompt = build_prompt(
                    view, role_of, players, qid,
                    events_desc, chat_log, chat_mode == "global",
                    mode
                )
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role":"system","content":SYS_JSON},
                        {"role":"user","content":prompt}
                    ],
                    temperature=0
                )
                out = safe_json_parse(resp.choices[0].message.content)
                out_fp.parent.mkdir(parents=True, exist_ok=True)
                out_fp.write_text(json.dumps(out, indent=2), encoding="utf-8")

        # --- LLM+CSP experiments ---
        mode = "llm_csp"
        for setting in CSP_SETTINGS:
            setting_name = setting[0]
            # choose chat scope
            chat_scope = "turn" if setting_name=="TurnIG" else "global"
            chat_log = build_transcript(
                cumulative_chat if chat_scope=="global"
                else chat_by_quest[qid]
            )

            for view in views:
                fname = (
                    f"{raw_path.stem}_{mode}_{setting_name}_"
                    f"{chat_scope}_{view}_{qid}.json"
                )
                out_fp = out_dir / raw_path.parent.name / fname
                if out_fp.exists():
                    print(f"[SKIP] {fname}")
                    continue

                # compute CSP posterior & best for this view+setting
                csp_post, csp_best = run_csp_for_setting(
                    view, setting,
                    hard_acc, assert_acc, hypo_acc, quest_hyp,
                    players, role_of
                )

                print(f"[RUN] File={raw_path.name} | Mode=LLM+CSP | Setting={setting_name} | "
                      f"Chat={chat_scope} | View={view} | Quest={qid}")
                prompt = build_prompt(
                    view, role_of, players, qid,
                    events_desc, chat_log, chat_scope=="global",
                    mode, setting, csp_post, csp_best
                )
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role":"system","content":SYS_JSON},
                        {"role":"user","content":prompt}
                    ],
                    temperature=0
                )
                out = safe_json_parse(resp.choices[0].message.content)
                out_fp.parent.mkdir(parents=True, exist_ok=True)
                out_fp.write_text(json.dumps(out, indent=2), encoding="utf-8")



if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python avalon_batch_llm_exp.py <raw_dataset_dir> <processed_constraints_dir> <output_dir>")
        sys.exit(1)

    raw_root  = Path(sys.argv[1]).resolve()
    proc_root = Path(sys.argv[2]).resolve()   # new
    out_root  = Path(sys.argv[3]).resolve()

    for cond in ("Truth", "Lie"):
        for fp in (raw_root / cond).glob("*.json"):
            run_experiment(fp, out_root, proc_root)
    print("Done LLM experiments.")
