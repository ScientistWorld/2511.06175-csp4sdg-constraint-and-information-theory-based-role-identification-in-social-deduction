#!/usr/bin/env python3
"""Install a real artifact-producing attempt, preserving the original workspace.

Attempt construction uses only visible constraints, visible saved predictions,
and visible method code. The unmodified hidden test is invoked by each run.sh
in a separate process, with no arguments and no evaluator/environment patching.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import random
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from redteam.exact_inference import solve

STATE = ROOT/'redteam/_state'
OUTPUT = ROOT/'data/avalonlogs_solve'
ORIGINAL = STATE/'original_solve'
PRESERVE = ['scoring/scores.json','scoring/scores_train.json','scoring/scores_test.json','method/avalon_logs_solver.py']
VIEWS = ['objective','merlin','percival','morgana','servant','evil_minion']


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(',',':')))


def start():
    if ORIGINAL.exists():
        raise RuntimeError('Previous attempt must be restored first')
    STATE.mkdir(parents=True, exist_ok=True)
    for name in PRESERVE:
        p = ROOT/name
        backup = STATE/name
        backup.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            shutil.copyfile(p, backup)
        elif backup.exists():
            backup.unlink()
    OUTPUT.rename(ORIGINAL)
    OUTPUT.mkdir()


def restore():
    if ORIGINAL.exists():
        if OUTPUT.is_symlink():
            OUTPUT.unlink()
        elif OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        ORIGINAL.rename(OUTPUT)
        for name in PRESERVE:
            backup = STATE/name
            p = ROOT/name
            if backup.exists():
                shutil.copyfile(backup, p)
            elif p.exists():
                p.unlink()


def original_link():
    OUTPUT.rmdir()
    OUTPUT.symlink_to(ORIGINAL, target_is_directory=True)


def metrics(g):
    truth = g['players']
    vals = []
    for views in g['quests'].values():
        for settings in views.values():
            d = settings.get('+HypIG', {})
            if d.get('posterior'):
                vals.append(sum(d['posterior'].get(p,{}).get(r,0) for p,r in truth.items())/len(truth))
    return sum(vals)/len(vals) if vals else 0.


def build(case):
    start()
    started = time.monotonic()
    folder = ROOT/'redteam'/case
    folder.mkdir(exist_ok=True)
    files = sorted(ORIGINAL.glob('*_solve.json'))
    if case == 'shortcut_unregistered_better_method':
        # A scientist starts without scoring/scores.json. Explicitly create
        # this shortcut's whitelist using visible game sizes/setting names;
        # never depend on the audit-only reproduced scores file as an input.
        write(ROOT/'scoring/scores.json', {'experiments':{
            f'avalonlogs_{n}player':{'results':{'CSP_Strict':{},'CSP_HypIG':{}}}
            for n in range(5,11)}})
    if case in ('reference','shortcut_replace_method','shortcut_direct_scores','shortcut_filter'):
        original_link()
        if case == 'shortcut_replace_method':
            (ROOT/'method/avalon_logs_solver.py').write_text("raise RuntimeError('shortcut: inference has been removed; test only reads cached outputs')\n")
        if case == 'shortcut_direct_scores':
            forged = {'experiments':{f'avalonlogs_{n}player':{'results':{'CSP_HypIG':{v+'_marginal':999. for v in ['Obj','MRL','PCV','MRG','LSV','EVM']}}} for n in range(5,11)}}
            write(ROOT/'scoring/scores_test.json', forged)
            write(folder/'shortcut_forged_scores.json', forged)
        if case == 'shortcut_filter':
            write(ROOT/'scoring/scores.json', {'experiments':{f'avalonlogs_{n}player':{'results':{'CSP_ShortcutMissing':{}}} for n in range(5,11)}})
        write(folder/'install.json', {'elapsed_seconds':time.monotonic()-started,'n_input_files':len(files)})
        return
    if case in ('shortcut_empty','shortcut_malformed'):
        for f in files:
            write(OUTPUT/f.name, {'players':{},'quests':{}} if case == 'shortcut_empty' else {'players':{'one':'unknown'},'quests':{}})
        write(folder/'install.json', {'elapsed_seconds':time.monotonic()-started,'n_input_files':len(files)})
        return
    pick = {}
    max_diff = 0.
    seed = int(case.rsplit('_',1)[1]) if case.startswith(('reference_seed_','raw_ig_seed_')) else 0
    random.seed(seed)
    manifest = {'case':case,'seed':seed,'n_input_files':len(files)}
    if case == 'shortcut_unregistered_better_method':
        manifest['shortcut_whitelist'] = 'explicitly created from visible game sizes and setting names'
    for j, f in enumerate(files):
        cp = ROOT/'data/avalonlogs_constraints'/f.name.replace('_solve.json','.json')
        game = json.loads(cp.read_text())
        game['_file'] = cp.name
        if case.startswith(('reference_seed_','raw_ig_seed_')) or case in ('live_conditional_ig','shortcut_bruteforce'):
            g = solve(game, weighting='raw_ig' if case.startswith('raw_ig_seed_') else 'ig')
            saved = json.loads(f.read_text())
            for q,vs in saved['quests'].items():
                for v,ss in vs.items():
                    for s,d in ss.items():
                        if s not in ('Strict','+HypIG'):
                            continue
                        for p, rp in d['posterior'].items():
                            for r, x in rp.items():
                                max_diff = max(max_diff, abs(x-g['quests'][q][v][s]['posterior'].get(p,{}).get(r,0)))
        elif case == 'better_knowledge':
            g = json.loads(f.read_text())
            fixed = solve(game, fix=True, weighting='raw_ig', only_merlin=True)
            for q,vs in fixed['quests'].items():
                for v,ss in vs.items():
                    g['quests'][q][v] = ss
        elif case in ('weaker_no_hypotheses','weaker_prior','shortcut_empty_map','shortcut_unregistered_better_method','shortcut_pool','shortcut_future_copy'):
            g = json.loads(f.read_text())
            for vs in g['quests'].values():
                for ss in vs.values():
                    if case == 'weaker_no_hypotheses':
                        ss['+HypIG'] = copy.deepcopy(ss['Strict'])
                    elif case == 'weaker_prior':
                        for s in ss:
                            ss[s]['posterior'] = {p['name']:{r:c/len(game['players']) for r,c in game['schema']['role_counts'].items()} for p in game['players']}
                    elif case == 'shortcut_empty_map':
                        for s in ss:
                            ss[s]['best'] = {}
            if case == 'shortcut_future_copy' and g['quests']:
                last = g['quests'][max(g['quests'], key=int)]
                g['quests'] = {q:copy.deepcopy(last) for q in g['quests']}
            if case == 'shortcut_unregistered_better_method':
                fixed = solve(game, fix=True, weighting='raw_ig', only_merlin=True)
                for q,vs in fixed['quests'].items():
                    for v,ss in vs.items():
                        g['quests'][q][v] = ss
                for vs in g['quests'].values():
                    for view, ss in vs.items():
                        vs[view] = {'FixedKnowledge':ss['+HypIG']}
            if case == 'shortcut_pool':
                n = len(g['players'])
                candidates = pick.setdefault(n, [])
                candidates.append((metrics(g),f.name,g))
                candidates.sort(key=lambda x:x[0], reverse=True)
                del candidates[20:]
                continue
        else:
            truth = {p['name']:p['role'] for p in game['players']}
            roles = list(game['schema']['role_counts'])
            if case in ('shortcut_leaked_labels','shortcut_failed_objective'):
                post = {p:{r:1.} for p,r in truth.items()}
                best = truth
            elif case in ('shortcut_constant_ones','shortcut_impossible'):
                post = {p:{r:(1. if case == 'shortcut_constant_ones' else 10.) for r in roles} for p in truth}
                best = {}
            elif case == 'shortcut_relabel':
                # Change evaluator's label source to an arbitrary valid world.
                rr = [r for r,c in game['schema']['role_counts'].items() for _ in range(c)]
                truth = dict(zip(truth,rr))
                post = {p:{r:1.} for p,r in truth.items()}
                best = truth
            else:
                raise ValueError(case)
            pred = {'posterior':post, 'best':best}
            g = {'file':cp.name,'players':truth,'quests':{str(q['quest']):{v:{'Strict':pred,'+HypIG':pred} for v in VIEWS} for q in game['quests']}}
        if case == 'shortcut_failed_objective':
            for views in g['quests'].values():
                views['objective'] = {s:{'posterior':{p:{r:0. for r in roles} for p in truth},'best':{}} for s in ('Strict','+HypIG')}
        write(OUTPUT/f.name,g)
        if (j+1)%1000 == 0:
            print(case,j+1,'seconds',round(time.monotonic()-started,1),flush=True)
    if case == 'shortcut_pool':
        for n, candidates in pick.items():
            for _,fname,g in candidates:
                write(OUTPUT/fname,g)
        manifest['selected'] = {str(n):[{'name':f,'quality':s} for s,f,g in cand] for n,cand in pick.items()}
    manifest.update(elapsed_seconds=time.monotonic()-started,max_posterior_difference_from_cached_reference=max_diff)
    write(folder/'install.json',manifest)


if __name__ == '__main__':
    os.chdir(ROOT)
    cmd = sys.argv[1]
    if cmd == 'restore':
        restore()
    else:
        build(cmd)
