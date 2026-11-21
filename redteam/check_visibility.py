"""Compare actual no-argument test outputs with and without the method filter."""
import json
from pathlib import Path

folder = Path(__file__).resolve().parent / 'reference'
filtered = json.loads((folder / 'scores_test.json').read_text())
unfiltered = json.loads((folder / 'scores_test_without_whitelist.json').read_text())
assert filtered['metadata'] == unfiltered['metadata'], 'Whitelist changed the game pool'
assert set(filtered['experiments']) == set(unfiltered['experiments'])
extra = {}
compared = 0
for exp, experiment in filtered['experiments'].items():
    a = experiment['results']
    b = unfiltered['experiments'][exp]['results']
    for method in ('CSP_Strict', 'CSP_HypIG'):
        assert a[method] == b[method], (exp, method, a[method], b[method])
        compared += len(a[method])
    additional = {method: metrics for method, metrics in b.items() if method not in a}
    if additional:
        extra[exp] = additional
assert compared == 72, compared
result = {
    'strict_hypig_metrics_identical_with_and_without_whitelist': True,
    'n_compared_metric_cells': compared,
    'game_pool_identical': True,
    'whole_score_files_identical': filtered == unfiltered,
    'additional_cached_settings_without_whitelist': extra,
    'whitelist_source': 'Each attempt constructs its own file from visible game sizes and Strict/+HypIG setting names; no audit-only score values are used.',
}
(folder / 'whitelist_visibility_check.json').write_text(json.dumps(result, indent=2) + '\n')
print('Whitelist visibility: all 72 Strict/HypIG cells and the game pool agree; extra settings:', sorted(extra), flush=True)
