# Evaluation

## What is evaluated

Hidden-role inference on real AvalonLogs games (5–10 players, no dialogue). An
**instance** is one game cut after a completed quest and seen from one
viewpoint. For every instance a method returns, for every player, a probability
distribution over the roles of the declared composition, plus one complete role
assignment.

The method never receives roles. The evaluators build the instances, run the
method on them, and score the predictions against roles they hold themselves.

## Data and splits

- 12,393 usable public AvalonLogs games. Half of every player count (6,197
  games) is the **hidden test set**: it lives only, encoded, in `eval/test/`.
  The other half (6,196 usable games, with their roles) is visible in
  `data/avalonlogs_raw/` for development and for fitting anything a method wants
  to learn.
- Each game gives exactly **one** instance: the public history up to one
  uniformly sampled completed quest, seen from **one** viewpoint. Viewpoints
  are balanced within each player count. One instance per game means no
  instance can be combined with another viewpoint, or a later part, of the same
  game.
- Player names are replaced by seat labels `P1..Pn` (seat order = leader
  rotation order).
- `scripts/evaluate_train.sh` builds train instances the same way from the
  visible games; `scripts/evaluate_test.sh` uses the hidden ones. Same metrics,
  same interface.

## Viewpoints

| key | viewer | private information given in `view` |
|---|---|---|
| `Obj` | none (objective observer) | none |
| `MRL` | Merlin | `sees_evil`: every evil player except Mordred |
| `PCV` | Percival | `merlin_candidates`: Merlin and Morgana, unlabelled (only Merlin if there is no Morgana) |
| `MRG` | Morgana | `sees_evil`: every other evil player except Oberon |
| `LSV` | a loyal follower | none besides their own role |
| `EVM` | an evil minion | `sees_evil`: every other evil player except Oberon |

Every non-objective view also gives `viewer` and `viewer_role`. The lists are
complete under the Avalon rules: a player missing from `sees_evil` is not an
evil player of a role the viewer is shown.

## Method interface

```
bash scripts/predict.sh <input_dir> <output_dir>
```

`<input_dir>/instances.json`:

```json
{"format": "avalonlogs-instances-v2",
 "instances": [{
   "instance_id": "t1a2b3c4d5e6f",
   "n_players": 7,
   "players": ["P1", "P2", "P3", "P4", "P5", "P6", "P7"],
   "role_counts": {"evil_minion": 1, "loyal_follower": 2, "merlin": 1, "mordred": 1, "morgana": 1, "percival": 1},
   "good_roles": ["loyal_follower", "merlin", "percival"],
   "evil_roles": ["evil_minion", "mordred", "morgana"],
   "missions": [{"mission": 1, "team_size": 2, "fails_required": 1,
                 "proposals": [{"proposer": "P3", "team": ["P3", "P5"],
                                "approve": ["P1", "P3", "P5"], "reject": ["P2", "P4", "P6", "P7"],
                                "approved": false}, "..."],
                 "team": ["P4", "P1"], "num_fails": 0, "result": "SUCCESS"}, "..."],
   "view": {"perspective": "merlin", "viewer": "P2", "viewer_role": "merlin", "sees_evil": ["P5", "P6"]}}]}
```

`missions` holds only the completed quests up to the cut, in order, with every
team proposal, every player's vote and the number of fail cards.

`<output_dir>/predictions.json`:

```json
{"predictions": {"<instance_id>": {"<method_name>": {
    "posterior": {"P1": {"merlin": 0.4, "loyal_follower": 0.6}, "...": {}},
    "best": {"P1": "loyal_follower", "...": "..."}}}}}
```

Every method name found in `predictions.json` is scored separately, so one run
can submit several methods. Names are sanitised to letters, digits and `_`.

## Validity (otherwise the method has failed)

For a method to be scored, the predictor must exit with status 0 and the method
must have, for **every** instance:

- `posterior` with exactly the instance's players; per player, probabilities for
  roles of the declared composition only (missing roles count as 0), each finite
  and in [0, 1], summing to 1 (±1e-3);
- role totals consistent with the composition: for every role r,
  sum over players of P(player = r) equals count(r) (±1e-2) — as any mixture of
  legal complete assignments does;
- `best`: a complete assignment of the declared roles with the declared counts.

A failed method gets the worst value of every metric in every experiment
(Brier 2, marginal accuracy 0). If the predictor writes nothing, the failure is
recorded under the method names of `scoring/reference.json`.

## Metrics

For an instance with P players, true roles r_p and predicted probabilities q:

- **Brier score** (ranked, lower is better):
  `(1/P) * sum_p sum_r (q_{p,r} - 1[r = r_p])^2`.
  A strictly proper scoring rule: reporting the true posterior is optimal, so it
  rewards both sharpness and calibration.
- **Marginal accuracy** (reported, coefficient 0): `(1/P) * sum_p q_{p,r_p}`,
  the paper's AvalonLogs quantity. It is not ranked because it is linear in q:
  moving all mass onto the most likely assignment raises it without better
  inference.

Both are averaged over the instances of each (player count, viewpoint) cell.
The `best` assignment is required and validated but not scored.

## Experiments and ranking

`avalonlogs_5player` … `avalonlogs_10player`, each with `Obj/MRL/PCV/MRG/LSV/EVM`
× `brier/marginal`. Held-out instances per viewpoint cell: about 280 (5p), 265
(6p), 228 (7p), 140 (8p), 70 (9p), 50 (10p).

The rank sums, over experiments and ranked metrics, experiment weight ×
|coefficient| × improvement over the reference (taken in the better direction)
divided by that metric's spread across ranked attempts. Weights:
6p 0.35, 9p 0.25, and 0.10 each for 5p, 7p, 8p, 10p. All 36 `*_brier`
coefficients (6 viewpoints × 6 experiments) are 1.

## Statistical validation

All methods see identical instances, so compare them with paired tests on
per-instance Brier differences. On the test set, the paired standard error of
the experiment-weighted mean Brier difference between two methods was 0.0004
for methods with similar posteriors (e.g. two CSP settings) and about 0.0013 for
methods built on a different evidence model. The inference is deterministic;
changing the seed of the one random step in the reference (which team member a
rejecting voter is taken to suspect) moves that aggregate by at most 0.0002.
