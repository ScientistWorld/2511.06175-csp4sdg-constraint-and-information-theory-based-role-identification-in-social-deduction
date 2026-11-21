"""Forensic cache provenance and direct validation of exact grouped summation.
Only visible method code, constraints and cached method outputs are consumed.
"""
import json
import math
from pathlib import Path
import sys
import time
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from redteam.exact_inference import solve
from method.avalon_logs_solver import solve_one, QUICK_SETTINGS

def diff(a,b):
    return max((abs(x-b['quests'][q][v][s]['posterior'].get(p,{}).get(r,0))
        for q,vs in a['quests'].items() for v,ss in vs.items() for s,d in ss.items()
        if s in ('Strict','+HypIG') for p,rp in d['posterior'].items() for r,x in rp.items()),default=0.)
t=time.monotonic()
classes=Counter();examples={};validation={};max_worlds={};counts=Counter();questcounts=Counter()
for j,fp in enumerate(sorted((ROOT/'data/avalonlogs_solve').glob('*_solve.json'))):
    saved=json.loads(fp.read_text());n=len(saved['players']);counts[n]+=1
    cp=ROOT/'data/avalonlogs_constraints'/fp.name.replace('_solve.json','.json')
    game=json.loads(cp.read_text())
    max_worlds[n]=max(max_worlds.get(n,0),math.factorial(n)//math.prod(math.factorial(c) for c in game['schema']['role_counts'].values()))
    for q in game['quests']:
        for k in ('evidence','phenomenon','assertions','hypotheses'):
            questcounts[k]+=len(q['constraints'][k])
    if n in (5,6) and str(n) not in validation:
        direct=solve_one(cp,settings=QUICK_SETTINGS)
        validation[str(n)]={'source':cp.name,'grouped_vs_current_source_max_posterior_difference':diff(direct,solve(game,weighting='ig'))}
    if n>=9:
        dr=diff(saved,solve(game,weighting='raw_ig'));dc=diff(saved,solve(game,weighting='ig'))
        tag='both' if max(dr,dc)<1e-8 else 'raw_only' if dr<1e-8 else 'conditional_only' if dc<1e-8 else 'neither'
        key=str(n)+'_'+tag;classes[key]+=1
        examples.setdefault(key,{'source':cp.name,'raw_max_difference':dr,'conditional_max_difference':dc})
    if (j+1)%1000==0:print(j+1,'elapsed',round(time.monotonic()-t,1),flush=True)
out={'cached_9_10_player_rule_classes':dict(classes),'examples':examples,'direct_source_validation':validation,'maximum_complete_assignments_by_size':max_worlds,'solved_counts':counts,'constraint_counts':questcounts,'elapsed_seconds':time.monotonic()-t}
(ROOT/'redteam/source_probe.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2),flush=True)
