"""Exact CSP inference, summing exchangeable role assignments by evil subset.

All supplied AvalonLogs constraints have no assertions. Hypotheses depend only
on sides, so summing equal-score full worlds within each side subset is exact.
Truth is used to construct the same allowed viewpoints as the supplied solver;
only each viewpoint's permitted information enters its inference calculation.
"""
import itertools
import math
from collections import Counter

GOOD = {'merlin', 'percival', 'loyal_follower', 'servant', 'loyal_servant'}
EVIL = {'evil_minion', 'evil-minion', 'assassin', 'morgana', 'mordred', 'oberon'}
VISIBLE = {'evil_minion', 'evil-minion', 'oberon', 'morgana'}


def entropy(p):
    return -p * math.log2(p) - (1-p)*math.log2(1-p) if 0 < p < 1 else 0.


def solve(game, fix=False, prior=False, weighting='ig', only_merlin=False):
    names = [p['name'] for p in game['players']]
    truth = {p['name']: p['role'] for p in game['players']}
    counts = game['schema']['role_counts']
    good_roles = set(game['schema']['good_roles'])
    n = len(names)
    ix = {p: i for i, p in enumerate(names)}
    def mask(ps):
        return sum(1 << ix[p] for p in set(ps))
    full = (1 << n)-1
    k = sum(c for r, c in counts.items() if r not in good_roles)
    subsets = [sum(1 << p for p in ss) for ss in itertools.combinations(range(n), k)]
    by_role = {}
    for p, r in truth.items():
        by_role.setdefault(r, []).append(p)
    view_specs = [('objective', {}, 0, None, None)]
    ctr = Counter()
    for p in names:
        r = truth[p]
        ctr[r] += 1
        title = r + str(ctr[r]) if len(by_role[r]) > 1 else r
        known = []
        if r in ('evil_minion', 'evil-minion'):
            known = [p2 for r2 in ('evil_minion', 'evil-minion', 'mordred', 'morgana') for p2 in by_role.get(r2, []) if p2 != p]
        elif r in ('mordred', 'morgana'):
            known = [p2 for r2 in ('evil_minion', 'evil-minion', 'mordred', 'morgana') if r2 != r for p2 in by_role.get(r2, []) if p2 != p]
        elif r == 'merlin':
            known = [p2 for r2 in VISIBLE for p2 in by_role.get(r2, [])]
        mm = by_role.get('merlin', []) + by_role.get('morgana', []) if r == 'percival' else []
        view_specs.append((title, {p:r}, mask(known), mm if len(mm) == 2 else None, set(known) if fix and r == 'merlin' else None))

    # Conditional role marginals and one legal complete world per evil subset.
    configs = {}
    for title, forced0, known, mm, merlin_seen in view_specs:
        if only_merlin and not title.startswith('merlin'):
            continue
        vv = []
        for side in subsets:
            if side & known != known:
                continue
            forced = dict(forced0)
            if mm:
                if bool(side & (1 << ix[mm[0]])) == bool(side & (1 << ix[mm[1]])):
                    continue
                for p in mm:
                    forced[p] = 'morgana' if side & (1 << ix[p]) else 'merlin'
            if any(bool(side & (1 << ix[p])) != (r not in good_roles) for p, r in forced.items()):
                continue
            rem = Counter(counts)
            rem.subtract(forced.values())
            if min(rem.values()) < 0:
                continue
            # Merlin's complete visible set restricts identity among the evil
            # players. These restrictions are within the legal private view.
            assignments = [(dict(forced), rem, 1.)]
            if merlin_seen is not None:
                evil_free = [p for p in names if p not in forced and side & (1 << ix[p])]
                possible = []
                def assign_evil(j, a, left):
                    if j == len(evil_free):
                        possible.append((dict(a), Counter(left), 1.))
                        return
                    p = evil_free[j]
                    for r, c in list(left.items()):
                        if c and r not in good_roles and ((r in VISIBLE) == (p in merlin_seen)):
                            a[p] = r; left[r] -= 1
                            assign_evil(j+1, a, left)
                            left[r] += 1; del a[p]
                assign_evil(0, dict(forced), Counter(rem))
                assignments = possible
            for forced, rem, unused in assignments:
                probs = {}
                best = dict(forced)
                ways = 1
                for evil_side in (False, True):
                    free = [p for p in names if p not in forced and bool(side & (1 << ix[p])) == evil_side]
                    rc = {r:c for r,c in rem.items() if c > 0 and (r not in good_roles) == evil_side}
                    if sum(rc.values()) != len(free):
                        break
                    ways *= math.factorial(len(free)) // math.prod(math.factorial(c) for c in rc.values())
                    for p in free:
                        probs[p] = {r:c/len(free) for r,c in rc.items()}
                    for p, r in zip(free, [r for r,c in rc.items() for _ in range(c)]):
                        best[p] = r
                else:
                    for p,r in forced.items():
                        probs[p] = {r:1.}
                    vv.append((side, ways, probs, best))
        configs[title] = vv

    out = {'file': game.get('_file', ''), 'players':truth, 'quests':{}}
    hard = []
    hypos = []
    manual = Counter()
    for q in game['quests']:
        c = q['constraints']
        assert not c['assertions'], 'Grouped inference requires assertion-free logs'
        hard.extend((mask(e['args']['team']), e['args']['min_fail']) for e in c['evidence'])
        for h in c['hypotheses']:
            a = h['args']; speaker = 1 << ix[a['speaker']]
            if h['type'] == 'hypo_team_good':
                hypos.append(('team', speaker, mask(a['team'])))
            elif h['type'] == 'hypo_role_in':
                hypos.append((a['set'], speaker, 1 << ix[a['target']]))
            else:
                raise ValueError(h['type'])
            manual[hypos[-1]] += h.get('weight', .2)
        unique_h = Counter(hypos)
        qo = {}
        for title, vv in configs.items():
            vv = [v for v in vv if all((v[0] & t).bit_count() >= f for t,f in hard)]
            if not vv:
                qo[title] = {s:{'posterior':{}, 'best':{}} for s in ('Strict', '+HypIG')}
                continue
            weights = [v[1] for v in vv]
            z = sum(weights)
            scores = [1.] * len(vv)
            for (typ, sp, target), multiplicity in unique_h.items():
                sat = [(bool(v[0] & sp) or ((v[0] & target == 0) if typ == 'team' else (bool(v[0] & target) == (typ == 'evil')))) for v in vv]
                raw = [((v[0] & target == 0) if typ == 'team' else (bool(v[0] & target) == (typ == 'evil'))) for v in vv]
                ig_sat = raw if weighting == 'raw_ig' else sat
                w = (manual[(typ, sp, target)] if weighting == 'manual' else entropy(sum(v[1] for v,s in zip(vv, ig_sat) if s)/z) * multiplicity)
                if w:
                    for j,s in enumerate(sat):
                        if s:
                            scores[j] += w
            qo[title] = {}
            for setting, ss in [('Strict',[1.]*len(vv)), ('+HypIG',scores)]:
                z = sum(v[1]*s for v,s in zip(vv,ss))
                post = {p:Counter() for p in names}
                for v,s in zip(vv,ss):
                    for p,rp in v[2].items():
                        for r,pv in rp.items():
                            post[p][r] += v[1]*s*pv/z
                best = vv[max(range(len(vv)), key=lambda j:ss[j])][3]
                qo[title][setting] = {'posterior':post, 'best':best}
            if prior:
                post = {p:{r:c/n for r,c in counts.items()} for p in names}
                for setting in qo[title]:
                    qo[title][setting] = {'posterior':post, 'best':vv[0][3]}
        out['quests'][str(q['quest'])] = qo
    return out
