"""Check saved audit evidence and restoration without rerunning computation."""
import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'redteam'
base = (R / 'initial_head.txt').read_text().strip()
summary = json.loads((R / 'summary.json').read_text())
checks = {}
checks['attempt_count'] = len(summary['attempts'])
checks['shortcut_count'] = sum(n.startswith('shortcut_') for n in summary['attempts'])
assert checks['attempt_count'] == 26
assert checks['shortcut_count'] == 15
for name, vals in summary['attempts'].items():
    folder = R / name
    runner = (folder / 'run.sh').read_text()
    assert 'bash scripts/evaluate_test.sh >' in runner, name
    assert 'Test scores written to scoring/scores_test.json' in (folder / 'test.log').read_text(), name
    scores = json.loads((folder / 'scores_test.json').read_text())
    assert scores['metadata']['slice'] == 'test', name
    assert len(scores['experiments']) == 6, name
    for exp in scores['experiments'].values():
        for method in exp['results'].values():
            assert all(isinstance(x, (int, float)) and math.isfinite(x) for x in method.values()), name
    install = json.loads((folder / 'install.json').read_text())
    assert install['n_input_files'] == 12091, name
    assert install['method_whitelist_origin'] == 'constructed from visible game sizes and Strict/+HypIG setting names', name
checks['every_attempt_has_no_argument_hidden_test_and_saved_evidence'] = True
checks['reference_seed_max_metric_spread'] = summary['seed_spread']['max_metric_range']
assert checks['reference_seed_max_metric_spread'] == 0
assert summary['attempts']['better_knowledge']['positive_deltas'] == 6
assert summary['attempts']['better_knowledge']['negative_deltas'] == 0
for name in ('weaker_prior', 'weaker_no_hypotheses'):
    assert summary['attempts'][name]['negative_deltas'] == 36
checks['honest_fix_and_both_ablations_order_correctly'] = True
assert int((R / 'shortcut_replace_method/shortcut_method_exit_code.txt').read_text()) == 1
checks['failed_inference_reproduces_cached_test_score'] = (
    summary['attempts']['shortcut_replace_method']['metrics'] == summary['attempts']['reference']['metrics'])
assert checks['failed_inference_reproduces_cached_test_score']
visibility = json.loads((R / 'reference/whitelist_visibility_check.json').read_text())
assert visibility['strict_hypig_metrics_identical_with_and_without_whitelist']
assert visibility['n_compared_metric_cells'] == 72
install = json.loads((R / 'shortcut_unregistered_better_method/install.json').read_text())
assert install['shortcut_whitelist'] == 'explicitly created from visible game sizes and setting names'
checks['reference_score_independent_of_initial_whitelist'] = True
checks['unregistered_method_shortcut_explicitly_creates_visible_whitelist'] = True
replay = json.loads((R / 'visibility_replay.json').read_text())
assert len(replay['attempts']) == 26
assert all(a['scores_identical_to_original_run'] for a in replay['attempts'].values())
checks['all_attempts_replayed_with_visible_whitelist_construction'] = True

protected = ['baseline', 'briefing', 'data', 'environment', 'eval', 'method', 'paper', 'scoring', 'scripts', 'validate.py']
changed = subprocess.check_output(['git', 'diff', '--name-only', base, '--', *protected], cwd=ROOT, text=True).splitlines()
checks['changed_protected_files_vs_initial_revision'] = changed
assert not changed, changed
checks['output_file_count_after_git_restoration'] = len(list((ROOT / 'data/avalonlogs_solve').glob('*_solve.json')))
assert checks['output_file_count_after_git_restoration'] == 12091
assert not (R / '_state/original_solve').exists()
checks['pending_attempt_restoration'] = False

allowed = {'README.md', 'manifest.json', 'action.yaml'}
diff = subprocess.check_output(['git', 'diff', '--name-only', base], cwd=ROOT, text=True).splitlines()
unexpected = [p for p in diff if not (p.startswith(('redteam/', 'trajectory/')) or p == 'REDTEAM.md' or p in allowed)]
assert not unexpected, unexpected
checks['unexpected_tracked_workspace_differences'] = unexpected
checks['initial_container_substitutions_preserved'] = 'README.md and manifest.json device files, absent trajectory files, and the initially untracked git shim were left as found; see initial_status.txt'
checks['job_control_exception'] = 'action.yaml is set to done after the final audit commit'
checks['initial_revision'] = base
checks['status'] = 'passed'
(R / 'restoration_check.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))
