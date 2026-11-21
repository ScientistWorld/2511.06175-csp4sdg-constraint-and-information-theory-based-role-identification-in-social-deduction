# Train/Test Evaluation Design Notes

Current design (iteration 11; see `HARDENING.md` for why it changed).

## Split and instances

- 12,393 usable AvalonLogs games. Half of every player count (seeded) is the
  hidden test set, stored encoded in `eval/test/heldout.dat` (inputs and roles in
  separate sections) and removed from `data/avalonlogs_raw/`.
  `eval/test/heldout_ids.txt` holds the SHA-256 of their file names so that
  `scripts/download.sh` drops them from a fresh archive download.
  `eval/test/build_heldout.py` documents how the file was built.
- One instance per game: the public history up to one uniformly sampled completed
  quest, one viewpoint (Obj, Merlin, Percival, Morgana, loyal follower, evil
  minion; balanced within each player count), seat labels instead of names.
  One instance per game rules out combining viewpoints or prefixes of a game.
- `eval/train/evaluate.py` builds train instances the same way (its own code and
  seed) from the visible games.

## Running the method

Both evaluators write the instances to a fresh temporary directory and call
`bash scripts/predict.sh <input_dir> <output_dir>`. The test evaluator keeps
`heldout.dat` mode 000 while the predictor runs and decodes the roles only after
it returns. There is no wall-clock limit.

## Scoring

- Method names are discovered from `predictions.json`; no whitelist.
- Validity per instance: posterior over exactly the instance's players and the
  declared roles, finite values in [0,1], rows summing to 1, role totals equal
  to the composition; `best` a complete assignment with the declared counts;
  predictor exit status 0. Any failure gives the method Brier 2 and marginal 0
  in every metric of every experiment; a run with no predictions is recorded as
  failed under the method names in `scoring/reference.json`.
- Ranked metric: Brier score per (player count, viewpoint), coefficient 1.
  Reported only: the paper's marginal accuracy (coefficient 0).
