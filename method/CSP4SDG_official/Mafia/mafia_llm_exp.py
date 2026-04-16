"""
Batch run LLM-only & LLM+CSP experiments for Mafia dataset.

Input  : mafia_dataset_processed/{Truth,Lie}/*.json   (with rounds & transcript)
Aux-CSP: mafia_constraints/{Truth,Lie}/*.json         (for CSP assistance)
Output : mafia_llm/{Truth,Lie}/<stem>_<mode>_<setting>_<chat>_<view>_<day>.json

Usage:
    python mafia_llm_exp.py mafia_dataset mafia_dataset_constraints mafia_dataset_llm
"""

import json, re, textwrap, os, sys
from pathlib import Path
from collections import defaultdict
import openai
from copy import deepcopy

from sdg_framework import SDGModel
from mafia_board  import build_schema, role_is, role_not, mafia_at_least

openai.api_key = os.getenv("OPENAI_API_KEY", "")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")
MODEL = "gpt-4o-mini"

# ---------------- CSP Settings ---------------- #
CSP_SETTINGS = [
    ("Strict",  False, False, False, False),
    ("+Assert", True,  False, False, False),
    ("+HypIG",  True,  True,  True,  False),
    ("+HypM",   True,  True,  False, False),
    ("TurnIG",  True,  True,  True,  True),
]

GOOD = {"bystander"}
MAF  = {"mafioso"}

def is_good(r):  return r in GOOD
def is_maf(r):   return r in MAF

# ---------------- predicate helpers ------------- #
def norm(role:str) -> str:
    """Map any spelling 'mafia' -> 'mafioso'."""
    return "mafioso" if role.lower()=="mafia" else role.lower()

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


def add_hypo(model, c):
    a  = c["args"]
    w  = c.get("weight", 0.2)
    aw = c.get("auto_weight", False)

    tgt_set = norm(a["set"])
    tgt     = a["target"]

    pred = (lambda w,t=tgt: w[t]=="mafioso") if tgt_set=="mafioso" \
           else (lambda w,t=tgt: w[t]=="bystander")

    model.add_hypothesis(a["speaker"], pred, weight=w, auto_weight=aw)


def compute_map(model: SDGModel):
    import math
    best,score={},-math.inf
    for w in model._worlds():
        m=sum(1 for s in model.mul_soft if s.func(w))
        s=sum(sa.weight for sa in model.add_soft if sa.func(w))
        val=m*math.log(model.A_base)+math.log(1+s)
        if val>score: best,score=w,val
    return best

# ---------------- CSP runner -------------------- #
def run_csp(view, setting, hard_acc, hypo_acc, current_hyps, players, role_of):
    _,use_assert,use_hyp,auto,only_today = setting
    schema=build_schema([{"name":n,"role":r} for n,r in role_of.items()])
    model = SDGModel(players, schema)

    for pr in hard_acc: model.add_evidence(build_pred(pr))

    # perspective extras
    if view=="BYS":
        me = next(p for p,r in role_of.items() if r=="bystander")
        model.add_evidence(role_is(me,"bystander"))
    if view=="MAF":
        me = next(p for p,r in role_of.items() if r=="mafioso")
        model.add_evidence(role_is(me,"mafioso"))
        for q,r in role_of.items():
            if r=="mafioso" and q!=me:
                model.add_evidence(role_is(q,"mafioso"))

    # (no assertions in Mafia dataset)

    if use_hyp:
        src = current_hyps if only_today else hypo_acc
        for c in src:
            add_hypo(model, c if auto else {**c,"auto_weight":False})

    try:
        post,_,_=model.evaluate_advanced() if use_hyp else model.evaluate_hard_only()
    except: post={}
    try: best=compute_map(model)
    except: best={}
    return post,best

# ---------------- prompt builder ---------------- #
SYS_JSON="You are an impartial Mafia analyst. Respond ONLY with a JSON object."

def build_prompt(view, role_of, players, day_idx,
                 events_txt, chat_txt, chat_global,
                 mode, setting=None, csp_post=None, csp_best=None):

    roles_str="bystander, mafioso"
    if view=="objective":
        pdesc="You have NO hidden information."
    elif view=="BYS":
        pdesc="You are a BYSTANDER (good); you know only your own innocence."
    else:  # MAF
        knows=[p for p,r in role_of.items() if r=="mafioso"]
        pdesc=f"You are a MAFIOSO; you know mafia team: {', '.join(knows)}."

    prompt=f"""{SYS_JSON}

## Day {day_idx}
### Perspective
{pdesc}

### Events so far
{events_txt}

### Chat ({'global' if chat_global else 'current day'})
{chat_txt}

### Possible roles
{roles_str}
"""
    if mode=="llm_csp":
        prompt+=f"""\n### CSP Assistance
Setting: {setting[0]}
Posterior: {json.dumps(csp_post)}
Best: {json.dumps(csp_best)}\n"""

    prompt+=textwrap.dedent("""
        ### Task
        1. For each player output probabilities over {"bystander","mafioso"}
           as "posterior": { "Alice":{"bystander":0.8,"mafioso":0.2}, ... }.
           Probabilities per player must sum to 1.
        2. Output "best": a single legal assignment meeting role counts.
        3. Return ONLY JSON with keys "posterior" and "best".
    """)
    return prompt

# ---------------- main loop --------------------- #
def run_game(game_fp: Path, constr_root: Path, out_root: Path):
    game = json.loads(game_fp.read_text(encoding="utf-8"))
    players=[p["name"] for p in game["players"]]
    role_of = {p["name"]: norm(p["role"]) for p in game["players"]}
    gid   = game_fp.stem
    cond  = game_fp.parent.name

    # load corresponding constraints for CSP assist
    constr_fp = constr_root/cond/f"{gid}_constraints.json"
    if constr_fp.exists():
        constr_data=json.loads(constr_fp.read_text(encoding="utf-8"))
        constr_by_day={entry["day"]: entry for entry in constr_data["days"]}
    else:
        constr_data=None
        constr_by_day={}

    hard_acc_all=[]
    hypo_acc_all=[]

    cumulative_events=[]; cumulative_chat=[]

    for rd in game["rounds"]:
        d = rd["round"]
        # build events/chat separation
        ev_block=[m for m in rd["transcript"] if m["speaker"].lower()=="system"]
        chat_block=[m for m in rd["transcript"] if m["speaker"].lower()!="system"]
        cumulative_events.extend(ev_block)
        cumulative_chat.extend(chat_block)

        events_txt="\n".join(f"[system] {m['text']}" for m in cumulative_events)
        chat_global_txt="\n".join(f"[{m['speaker']}] {m['text']}"
                                  for m in cumulative_chat)
        chat_turn_txt  ="\n".join(f"[{m['speaker']}] {m['text']}"
                                  for m in chat_block)

        # --------- update CSP accum from constraints (if available) ----------
        if constr_data:
            day_constr = constr_by_day.get(d, {"evidence": [], "phenomenon": [], "hypotheses": []})
            current_hyps = day_constr["hypotheses"]
            hard_acc_all.extend(day_constr["evidence"]+day_constr["phenomenon"])
            hypo_acc_all.extend(current_hyps)
        else:
            current_hyps = []

        # -------------- LLM-only ------------------
        for chat_mode,chat_txt in [("global",chat_global_txt),
                                   ("turn",  chat_turn_txt)]:
            for view in ("objective","BYS","MAF"):
                fname=f"{gid}_llm_{chat_mode}_{view}_{d}.json"
                out_fp=out_root/cond/fname
                if out_fp.exists():
                    print("[SKIP]",fname); continue
                print("[RUN] File=",gid,"Mode=LLM chat",chat_mode,
                      "View",view,"Day",d)
                prompt=build_prompt(view,role_of,players,d,
                                    events_txt,chat_txt,chat_mode=="global",
                                    mode="llm")
                rsp=openai.ChatCompletion.create(
                    model=MODEL,
                    temperature=0,
                    messages=[{"role":"system","content":SYS_JSON},
                              {"role":"user","content":prompt}]
                )
                out=json.loads(re.search(r"\{.*\}",rsp.choices[0].message.content,re.S).group(0))
                out_fp.parent.mkdir(parents=True,exist_ok=True)
                out_fp.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")

        # -------------- LLM + CSP ----------------
        if not constr_data:
            continue   # no CSP assistance available
        for setting in CSP_SETTINGS:
            sname=setting[0]
            chat_scope="turn" if sname=="TurnIG" else "global"
            chat_txt = chat_turn_txt if chat_scope=="turn" else chat_global_txt

            for view in ("objective","BYS","MAF"):
                fname=f"{gid}_llm_csp_{sname}_{chat_scope}_{view}_{d}.json"
                out_fp=out_root/cond/fname
                if out_fp.exists():
                    print("[SKIP]",fname); continue

                csp_post,csp_best=run_csp(
                    view, setting,
                    hard_acc_all,
                    hypo_acc_all,
                    current_hyps,
                    players, role_of
                )

                print("[RUN] File=",gid,"Mode=LLM+CSP",sname,
                      "View",view,"Day",d)
                prompt=build_prompt(view,role_of,players,d,
                                    events_txt,chat_txt,chat_scope=="global",
                                    mode="llm_csp",setting=setting,
                                    csp_post=csp_post,csp_best=csp_best)
                rsp=openai.ChatCompletion.create(
                    model=MODEL,temperature=0,
                    messages=[{"role":"system","content":SYS_JSON},
                              {"role":"user","content":prompt}]
                )
                out=json.loads(re.search(r"\{.*\}",rsp.choices[0].message.content,re.S).group(0))
                out_fp.parent.mkdir(parents=True,exist_ok=True)
                out_fp.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")

# ---------------- CLI ------------------ #
if __name__=="__main__":
    if len(sys.argv)!=4:
        print("Usage: python mafia_llm_exp.py mafia_dataset mafia_dataset_constraints mafia_dataset_llm")
        sys.exit(1)
    proc_root=Path(sys.argv[1]).resolve()
    constr_root=Path(sys.argv[2]).resolve()
    out_root   =Path(sys.argv[3]).resolve()

    for cond in ("Truth","Lie"):
        for game_fp in (proc_root/cond).glob("*.json"):
            run_game(game_fp, constr_root, out_root)
    print("✔ All Mafia LLM experiments finished.")
