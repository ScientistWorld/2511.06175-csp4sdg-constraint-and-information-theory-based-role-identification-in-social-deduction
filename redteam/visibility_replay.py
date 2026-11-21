"""Replay saved attempts with a whitelist constructed from scientist-visible facts.

This is a job entry point. The original test outputs are retained for exact
comparison; each runner regenerates its artifacts and invokes the hidden test.
"""
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / 'redteam'
names = [
    'reference', 'reference_seed_0', 'reference_seed_1', 'reference_seed_2',
    'raw_ig_seed_0', 'raw_ig_seed_1', 'raw_ig_seed_2', 'better_knowledge',
    'weaker_no_hypotheses', 'weaker_prior', 'live_conditional_ig',
    'shortcut_unregistered_better_method', 'shortcut_leaked_labels',
    'shortcut_constant_ones', 'shortcut_impossible', 'shortcut_relabel',
    'shortcut_empty', 'shortcut_malformed', 'shortcut_empty_map', 'shortcut_pool',
    'shortcut_future_copy', 'shortcut_replace_method', 'shortcut_direct_scores',
    'shortcut_filter', 'shortcut_bruteforce', 'shortcut_failed_objective',
]
record_path = R / 'visibility_replay.json'
record = json.loads(record_path.read_text()) if record_path.exists() else {
    'purpose': 'Every attempt explicitly constructs the comparison whitelist from visible setting names instead of depending on an audit-only file.',
    'attempts': {},
}
subprocess.run(['python3', 'redteam/harness.py', 'restore'], cwd=ROOT, check=True)
for name in names:
    if name in record['attempts']:
        print('Visibility replay already completed:', name, flush=True)
        continue
    folder = R / name
    original = folder / 'scores_test_before_visibility.json'
    if not original.exists():
        shutil.copyfile(folder / 'scores_test.json', original)
    started = time.monotonic()
    print('Replaying', name, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), flush=True)
    subprocess.run(['bash', str(folder / 'run.sh')], cwd=ROOT, check=True)
    a = json.loads(original.read_text())
    b = json.loads((folder / 'scores_test.json').read_text())
    assert a == b, f'{name}: score changed under the explicitly constructed visible whitelist'
    installation = json.loads((folder / 'install.json').read_text())
    assert installation['method_whitelist_origin'] == 'constructed from visible game sizes and Strict/+HypIG setting names'
    record['attempts'][name] = {
        'scores_identical_to_original_run': True,
        'elapsed_seconds': time.monotonic() - started,
        'method_whitelist_origin': installation['method_whitelist_origin'],
    }
    record_path.write_text(json.dumps(record, indent=2) + '\n')
subprocess.run(['python3', 'redteam/analyze.py'], cwd=ROOT, check=True)
print('All 26 visibility replays passed.', flush=True)
