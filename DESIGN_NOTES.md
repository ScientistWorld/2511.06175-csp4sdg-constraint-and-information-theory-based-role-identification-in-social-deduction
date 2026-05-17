# Train/Test Evaluation Design Notes

## Checks performed

- Reviewed `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side for slice paths, output paths, and hardcoded method defaults.
- Read both slice evaluators for method attachment. They score pre-generated solver artifacts from `--results-dir` instead of rerunning training or inference.
- Grepped for train/test cross-imports, paper-agreement metric names, `METHOD_NAME` defaults, and accidental test-to-train script references.
- Checked `scoring/reference.json` metric definitions for required fields and for forbidden paper-agreement metrics.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both train/test shell wrappers.

## Changes made

- Added AvalonLogs MAP scoring to both `eval/train/evaluate.py` and `eval/test/evaluate.py`. The first pass only scored marginal probability on AvalonLogs, which left a shortcut path where a method could tune probability mass without producing coherent best role assignments. The split now triangulates marginal accuracy with MAP accuracy on every AvalonLogs role view.
- Added Mafia JSONL slice scoring to both train and test evaluators. `reference.json` already contained `mafia_truth_main`, but `--dataset mafia` previously returned an empty warning, so that experiment was not actually covered by the split.
- Removed the held-out evaluator's dependency on `scoring/scores_train.json`. Test now discovers method entries directly from held-out artifacts, preserving the same method interface as train without coupling the hidden slice to a visible score file.
- Added `description` fields to every metric definition in `scoring/reference.json`.
- Added AvalonLogs `*_map` metric entries in `scoring/reference.json` with lower coefficient than the marginal metrics. These are secondary anti-shortcut checks, not replacements for the paper's headline marginal quantities.

## Runtime concerns for the runner iteration

- Mafia support was added against the official CSP JSONL shape (`players`, `cond`, `days`, per-view `posterior` and `best`). The runner should confirm future Mafia artifacts use that same shape or adapt the method wrapper, not the evaluator.
- AvalonLogs MAP metrics are newly emitted by train/test. Existing paper-result entries in `reference.json` do not include AvalonLogs MAP values because those were not part of the original transcribed result table for those experiments; the benchmark scorer should treat the metric definitions as the target schema for future score files.
- The split is deterministic 50/50 within player-count groups or JSONL records. If a provided result directory is very small, train/test variance may be high; the runner should watch selected-count metadata before interpreting a large gap as method overfit.
- Mafia-UCB `MAF_*` metrics may saturate for CSP-style methods because the mafia perspective often knows the mafia team. The paired `Obj_*` and `BYS_*` metrics are more informative for shortcut detection.
