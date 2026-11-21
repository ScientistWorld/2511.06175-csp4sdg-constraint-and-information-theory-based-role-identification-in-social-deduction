"""Try literal full-assignment enumeration on an available 151,200-world game."""
import json
import math
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from method.sdg_framework import enumerate_assignments
from method.generic_board import build_schema
from method.avalon_logs_solver_fast import build_pred, build_hypothesis_checker, _build_hypo_predicate, score_worlds_direct
from redteam.exact_inference import solve, entropy

t = time.monotonic()
chosen = None
for fp in sorted((ROOT/'data/avalonlogs_constraints').glob('*json')):
    game = json.loads(fp.read_text())
    n = len(game['players'])
    count = math.factorial(n)//math.prod(math.factorial(c) for c in game['schema']['role_counts'].values())
    if count == 151200 and (ROOT/'data/avalonlogs_solve'/(fp.stem+'_solve.json')).exists():
        chosen = fp
        break
assert chosen
names = [p['name'] for p in game['players']]
schema = build_schema(game['schema'])
worlds = list(enumerate_assignments(names,schema))
enumeration_seconds = time.monotonic()-t
hard = [build_pred(schema,e) for q in game['quests'] for e in q['constraints']['evidence']]
feasible = [w for w in worlds if all(h(w) for h in hard)]
hypos = [h for q in game['quests'] for h in q['constraints']['hypotheses']]
ig = []
for h in hypos:
    pred = _build_hypo_predicate(h)
    ig.append(entropy(sum(build_hypothesis_checker(schema,h)(w) for w in feasible)/len(feasible)))
post,best = score_worlds_direct(feasible,names,10000.,[],[build_hypothesis_checker(schema,h) for h in hypos],ig,ig,False,True,True,[])
grouped = solve(game,weighting='ig')['quests'][str(game['quests'][-1]['quest'])]['objective']['+HypIG']['posterior']
diff = max(abs(p-grouped[player].get(role,0)) for player,rs in post.items() for role,p in rs.items())
result = {'source':chosen.name,'full_assignments':len(worlds),'feasible_at_last_quest':len(feasible),'enumeration_seconds_including_input_search':enumeration_seconds,'total_seconds':time.monotonic()-t,'max_posterior_difference_from_grouped_exact':diff,'truth_accuracy':sum(post[p].get(r,0) for p,r in ((p['name'],p['role']) for p in game['players']))/len(names)}
(ROOT/'redteam/shortcut_bruteforce/brute_probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(result,flush=True)
