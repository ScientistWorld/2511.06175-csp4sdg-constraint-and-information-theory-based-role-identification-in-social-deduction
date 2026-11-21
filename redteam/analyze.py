#!/usr/bin/env python3
"""Audit the actual test files; apply the rank formula specified by the user.

Future across-attempt standard deviations are unknowable. We therefore retain
every metric delta and show a reproducible rank using this audit's cohort. A
dominating vector or an empty vector has the stated sign for any positive
finite standard deviations, independently of that illustrative cohort.
"""
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
R = ROOT/'redteam'
spec = json.loads((ROOT/'scoring/reference.json').read_text())['experiments']
ref = json.loads((R/'reference/scores_test.json').read_text())['experiments']
exps = sorted(ref)
den = sum(spec[e]['weight'] for e in exps)
weights = {e:spec[e]['weight']/den for e in exps}
scored = [(e,m) for e in exps for m in spec[e]['metrics']]
all_scores = {p.parent.name:json.loads(p.read_text()) for p in R.glob('*/scores_test.json')}


def values(d, method='CSP_HypIG'):
    return {(e,m):d.get('experiments',{}).get(e,{}).get('results',{}).get(method,{}).get(m) for e,m in scored}


vv = {name:values(d) for name,d in all_scores.items()}
rv = vv['reference']
sigma = {}
for key in scored:
    xs = [v[key] for v in vv.values() if isinstance(v[key],(int,float)) and math.isfinite(v[key])]
    sigma[key] = statistics.pstdev(xs) if len(xs)>1 else 0.

report = {'rank_definition':'sum normalized experiment weight * abs(coefficient) * better-direction (attempt - original test reference) / audit-cohort population standard deviation; missing values skipped',
          'rank_limit':'Future ranking cohort and its standard deviations are not available. These numeric ranks describe this saved audit cohort, not a claimed final leaderboard rank.',
          'reference_method':'CSP_HypIG', 'weights':weights, 'attempts':{}, 'active_bounds':[], 'dormant_paper_bounds':[]}
for e,m in scored:
    if rv[e,m] in (0,1):
        report['active_bounds'].append([e,m,rv[e,m]])
for e,s in spec.items():
    if e not in exps:
        for method,rs in s['results'].items():
            for m in s['metrics']:
                if rs.get(m) in (0,1):
                    report['dormant_paper_bounds'].append([e,method,m,rs[m]])
for name, v in vv.items():
    terms = []
    paper_terms = []
    deltas = {}
    by_exp = {}
    for e,m in scored:
        x = v[e,m]
        if not isinstance(x,(int,float)) or not math.isfinite(x):
            continue
        c = spec[e]['metrics'][m]
        delta = (x-rv[e,m])*(1 if c['higher_is_better'] else -1)
        deltas[e+'/'+m] = delta
        if sigma[e,m]>0:
            scale = weights[e]*abs(c['coefficient'])/sigma[e,m]
            terms.append(scale*delta)
            paper_delta = (x-spec[e]['results']['CSP_HypIG'][m])*(1 if c['higher_is_better'] else -1)
            paper_terms.append(scale*paper_delta)
        by_exp.setdefault(e,{})[m] = x
    present = [key for key in scored if isinstance(v[key],(int,float))]
    q = sum(weights[e]*v[e,m]/len(spec[e]['metrics']) for e,m in present)
    report['attempts'][name] = {'rank':sum(terms),'rank_vs_paper_csp_hypig':sum(paper_terms),'weighted_marginal':q if len(present)==len(scored) else None,
        'weighted_marginal_if_missing_zero':q,'n_present':len(present),'n_expected':len(scored),
        'positive_deltas':sum(x>0 for x in deltas.values()),'negative_deltas':sum(x<0 for x in deltas.values()),
        'metric_deltas':deltas,'metrics':by_exp,'split_counts':all_scores[name]['metadata'].get('n_selected_files_by_experiment',{})}
seeds = [report['attempts'][f'reference_seed_{i}'] for i in range(3)]
report['seed_spread'] = {'implementation':'Current visible solver, conditional hypothesis entropy; exact grouped summation verified against the original solver by source_probe.py','weighted_marginal_range':[min(x['weighted_marginal'] for x in seeds),max(x['weighted_marginal'] for x in seeds)],
    'rank_range':[min(x['rank'] for x in seeds),max(x['rank'] for x in seeds)],
    'max_metric_range':max(max(vv[f'reference_seed_{i}'][key] for i in range(3))-min(vv[f'reference_seed_{i}'][key] for i in range(3)) for key in scored)}
strict = values(all_scores['reference'],'CSP_Strict')
report['reproduction'] = {'hypig_minus_strict':{e+'/'+m:rv[e,m]-strict[e,m] for e,m in scored},
    'hypig_minus_paper':{e+'/'+m:rv[e,m]-spec[e]['results']['CSP_HypIG'][m] for e,m in scored},
    'no_reproduced_llm_baseline':True}
report['sigmas'] = {e+'/'+m:x for (e,m),x in sigma.items()}
(R/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
lines = ['attempt\tweighted_marginal\taudit_cohort_rank\trank_vs_paper_csp_hypig\tmetrics_present\tpositive_deltas\tnegative_deltas']
for name,a in report['attempts'].items():
    lines.append(f"{name}\t{a['weighted_marginal']}\t{a['rank']}\t{a['rank_vs_paper_csp_hypig']}\t{a['n_present']}\t{a['positive_deltas']}\t{a['negative_deltas']}")
(R/'summary.tsv').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines),flush=True)
