"""
avalon_logs_llm_exp.py — single‑quest LLM experiments per player view
"""

import json, os, random, re, math, sys, textwrap, time
from pathlib import Path
from typing import Dict, List
import openai
from openai.error import APIError, Timeout, RateLimitError, APIConnectionError
from sdg_framework import SDGModel
import generic_board as gb
sys.setrecursionlimit(100000)

# ------------------- OpenAI Settings ------------------- #
openai.api_key = os.getenv("OPENAI_API_KEY", "")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY is not set.")
MODEL = "gpt-4o-mini"
SYS   = "You are an impartial Avalon analyst. Output ONLY the requested JSON."

GOOD = {"merlin","percival","loyal_follower","servant"}
EVIL = {"evil_minion","mordred","morgana","oberon","assassin"}

# ---------------- util ---------------- #
def fmt_role(r:str): return r.replace(" ","_").lower()

def summarise(m, idx):
    prop = m["proposals"][-1] if m["proposals"] else {}
    return (f"Quest {idx}: proposer={prop.get('proposer','?')} "
            f"team={m['team']} fails={m['numFails']} state={m['state']}")

def build_view_maps(player2role:Dict[str,str]):
    cnt={}; p2v={}; v2p={}
    for p,r in player2role.items():
        cnt[r]=cnt.get(r,0)+1
        v=r if cnt[r]==1 else f"{r}{cnt[r]}"
        p2v[p]=v; v2p[v]=p
    return p2v,v2p

# percival helper
def percival_mm_pred(c1,c2):
    return lambda w,c1=c1,c2=c2: {w[c1],w[c2]}=={"merlin","morgana"} and \
        all(p in (c1,c2) or w[p] not in {"merlin","morgana"} for p in w)

# perspective blurb
def make_blurb(player, role, by_role):
    if player=="objective": return "You have NO hidden information."
    if role=="evil_minion":
        know=sum((by_role.get(r,[]) for r in ("evil_minion","mordred","morgana")),[])
    elif role=="mordred":
        know=sum((by_role.get(r,[]) for r in ("evil_minion","morgana")),[])
    elif role=="morgana":
        know=sum((by_role.get(r,[]) for r in ("evil_minion","mordred")),[])
    elif role=="merlin":
        know=sum((by_role.get(r,[]) for r in ("evil_minion","oberon","morgana")),[])
    elif role=="percival":
        mm=by_role.get("merlin",[])+by_role.get("morgana",[])
        if len(mm)==2:
            return f"You are Percival; exactly {{Merlin,Morgana}} = {mm[0]}, {mm[1]}."
        know=[]
    else: know=[]
    return f"You are {role}; known‑evil: {', '.join(sorted(set(know)))}." if know \
           else f"You are {role}; you have no extra hidden information."

# ---------------- CSP assistant (+IG) ---------------- #
def _compute_map(model:SDGModel):
    best,score={},-math.inf
    for w in model._worlds():
        m=sum(1 for s in model.mul_soft if s.func(w))
        s=sum(sa.weight for sa in model.add_soft if sa.func(w))
        v=m*math.log(model.A_base)+math.log(1+s)
        if v>score: best,score=w,v
    return best

def csp_assist(const_fp: Path, qidx: int, view: str):
    """Return (posterior, best) for quest qidx under the given view."""
    data   = json.loads(const_fp.read_text())
    players= [p["name"] for p in data["players"]]
    truth  = {p["name"]: p["role"] for p in data["players"]}
    schema = gb.build_schema(data["schema"])

    # build by_role
    by_role = {}
    for name, role in truth.items():
        by_role.setdefault(role, []).append(name)

    extras = []
    if view != "objective":
        m = re.match(r'([a-z_]+)', view)
        role_base = m.group(1)
        idx       = None if role_base == view else int(view[len(role_base):]) - 1

        if role_base not in by_role or (idx is not None and idx >= len(by_role[role_base])):
            raise ValueError(f"view '{view}' absent in this game")

        holder = by_role[role_base][idx or 0]
        my_role = truth[holder]

        extras.append(gb.role_is(holder, my_role))

        def mark(p): extras.append(lambda w, p=p: w[p] in EVIL)

        if my_role == "evil_minion":
            for r2 in ("evil_minion","mordred","morgana"):
                for p2 in by_role.get(r2, []):
                    if p2 != holder: mark(p2)
        elif my_role == "mordred":
            for r2 in ("evil_minion","morgana"):
                for p2 in by_role.get(r2, []):
                    if p2 != holder: mark(p2)
        elif my_role == "morgana":
            for r2 in ("evil_minion","mordred"):
                for p2 in by_role.get(r2, []):
                    if p2 != holder: mark(p2)
        elif my_role == "merlin":
            for r2 in ("evil_minion","oberon","morgana"):
                for p2 in by_role.get(r2, []):
                    mark(p2)
        elif my_role == "percival":
            mm = by_role.get("merlin", []) + by_role.get("morgana", [])
            if len(mm) == 2:
                extras.append(percival_mm_pred(mm[0], mm[1]))

    hard, hyps = [], []
    for q in data["quests"]:
        if q["quest"] > qidx: break
        hard += q["constraints"]["evidence"]
        hyps  += q["constraints"]["hypotheses"]

    model = SDGModel(players, schema)

    for ev in hard:
        team = ev["args"]["team"]
        k    = ev["args"].get("min_fail", 1)
        model.add_evidence(lambda w, team=team, k=k:
                           sum(1 for p in team if w[p] in EVIL) >= k)

    for ex in extras:
        model.add_evidence(ex)

    for h in hyps:
        if h["type"] == "hypo_team_good":
            pred = gb.team_all_good(schema, h["args"]["team"])
        else:
            tgt  = h["args"]["target"]
            pred = lambda w, tgt=tgt: w[tgt] in EVIL
        model.add_hypothesis(h["args"]["speaker"], pred,
                             weight=h.get("weight", 0.2), auto_weight=True)

    posterior, _, _ = model.evaluate_advanced()
    best = _compute_map(model)
    return posterior, best


# ---------------- safe_chat ---------------- #
def safe_chat(msgs,model=MODEL,max_retry=6):
    for k in range(max_retry):
        try:
            rsp=openai.ChatCompletion.create(model=model,temperature=0,messages=msgs)
            return json.loads(re.search(r"\{.*\}",rsp.choices[0].message.content,re.S).group(0))
        except (APIError,Timeout,RateLimitError,APIConnectionError):
            time.sleep(2**k)
    raise RuntimeError("Chat API failed")

# ---------------- prompt builder ---------- #
def build_prompt(players,qidx,events,counts,view,blurb,mode,post=None,best=None):
    txt=f"{SYS}\n\n## Status after Quest {qidx}\nPlayers: {', '.join(players)}\n"
    txt+=f"### Perspective\n{blurb}\n"
    txt+=f"### Task history\n{events}\n"
    txt+=f"### Legal roles & counts\n{json.dumps(counts)}\n"
    if mode=="llm_csp":
        txt+=f"\n### CSP (+HypIG) assistance (raw JSON)\nposterior: {json.dumps(post)}\nbest: {json.dumps(best)}\n"
    roles=list(counts)
    txt+=textwrap.dedent(f"""
        ### Strict output specification
        Return ONE JSON object with:
        1. "posterior": {{player → {{role → prob}}}} (roles = {roles}, probs sum 1)
        2. "best": {{player → role}} respecting the counts above.
        No markdown, comments, or extra keys.
    """)
    return txt

# ---------------- main pipeline ----------- #
def processed_already(out_dir:Path,stem:str,view:str)->bool:
    """True if BOTH llm & llm_csp outputs exist"""
    return (list(out_dir.glob(f"{stem}_{view}_llm_Q*.json"))
            and list(out_dir.glob(f"{stem}_{view}_llm_csp_Q*.json")))

def process_game(raw_fp,const_dir,out_dir,view_arg):
    stem=raw_fp.stem
    if processed_already(out_dir,stem,view_arg):
        print(f"[SKIP] {stem} ({view_arg}) already done"); return

    game=json.loads(raw_fp.read_text())
    outcome={r["name"]:fmt_role(r["role"]) for r in game["outcome"]["roles"]}
    players={p["name"]: outcome.get(p["name"],"unknown") for p in game["players"]}
    _,inv=build_view_maps(players)

    # ---- validate requested view ----
    if view_arg=="objective":
        view="objective"; me=None; role=None
    else:
        if view_arg not in inv:
            print(f"[SKIP] {stem}: view '{view_arg}' absent"); return
        me=inv[view_arg]; role=players[me]; view=view_arg

    missions=[m for m in game["missions"] if m["state"]!="PENDING"]
    if not missions: return
    random.seed(stem); qidx=random.randint(1,len(missions))
    events="\n".join(summarise(missions[i],i+1) for i in range(qidx))

    counts={}; by_role={}
    for n,r in players.items():
        counts[r]=counts.get(r,0)+1
        by_role.setdefault(r,[]).append(n)
    blurb=make_blurb(me or "objective",role,by_role)

    # ---------- LLM only ----------
    llm_prompt=build_prompt(list(players),qidx,events,counts,view,blurb,"llm")
    llm_json=safe_chat([{"role":"system","content":SYS},{"role":"user","content":llm_prompt}])
    llm_json={"view":view,**llm_json}
    out_dir.mkdir(parents=True,exist_ok=True)
    (out_dir/f"{stem}_{view}_llm_Q{qidx}.json").write_text(json.dumps(llm_json,indent=2))

    # ---------- LLM + CSP ----------
    const_fp=const_dir/f"{stem}_constraints.json"
    if not const_fp.exists(): return
    try:
        post,best=csp_assist(const_fp,qidx,view)
    except ValueError as e:
        print(f"[SKIP] {stem}: {e}"); return
    llm_csp_prompt=build_prompt(list(players),qidx,events,counts,view,blurb,"llm_csp",post,best)
    llm_csp_json=safe_chat([{"role":"system","content":SYS},{"role":"user","content":llm_csp_prompt}])
    llm_csp_json={"view":view,**llm_csp_json}
    (out_dir/f"{stem}_{view}_llm_csp_Q{qidx}.json").write_text(json.dumps(llm_csp_json,indent=2))
    print(f"[DONE] {stem} (Quest {qidx}, view={view})")

# ---------------- CLI -------------------- #
if __name__=="__main__":
    if len(sys.argv) not in (4,5):
        print("Usage: python avalon_logs_llm_exp.py <raw_dir> <constraints_dir> <out_dir> [view]")
        sys.exit(1)
    raw   = Path(sys.argv[1]).resolve()
    const = Path(sys.argv[2]).resolve()
    out   = Path(sys.argv[3]).resolve()
    view  = sys.argv[4] if len(sys.argv)==5 else "objective"
    for fp in raw.iterdir():
        if fp.is_file():
            process_game(fp,const,out,view)
    print("✓ All experiments finished.")
