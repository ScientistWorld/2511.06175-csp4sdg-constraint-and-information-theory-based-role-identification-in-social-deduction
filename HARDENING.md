# Hardening (iteration 11)

There was no `REVIEW.md`; this pass works from `REDTEAM.md`. All "after" numbers
come from one CPU job (`jobs/32a6a669-bd2`, 3 minutes) that ran every attempt
through the unchanged `eval/test/evaluate.py`, swapping only the predictor
command (`redteam/iter11/audit.sh`). Per-attempt score files are in
`redteam/iter11/attempts/<name>/scores_test.json`; the full table is
`redteam/iter11/summary.md` / `summary.json`.

Notation. **W** = experiment-weighted mean of the six viewpoint Brier scores
(lower is better; an aggregate for reading, not the ranking formula). **dW** =
W(attempt) − W(reference), with its paired standard error on identical held-out
instances. **R** = the ranking formula from the task (sum over experiments of
weight × |coefficient| × improvement in the better direction / that metric's
population SD across the 37 entries of this audit cohort). "Before" numbers are
REDTEAM.md's: Q = weighted mean marginal accuracy, R_old = their rank against
the paper's CSP_HypIG values.

## Does a better result now score higher?

Yes. Better variants score above the reference by many paired SEs, and weaker
ones score below it. Every honest variant improves every experiment.

| attempt | before (old test) | after: W | dW ± paired se | R | ranked metrics better/worse (of 36) |
|---|---|---:|---:|---:|---|
| reference (CSP_HypIG) | Q 0.5022, R_old −0.032 | 0.4776 | 0 | 0 | – |
| better_knowledge: full viewpoint knowledge (Merlin also knows who is *not* a visible evil, evil roles know non-teammates, Percival without Morgana knows Merlin) | Q 0.5100 (Merlin-only fix), R_old −0.019 | 0.4645 | −0.0131 ± 0.0004 | +0.119 | 20/0 |
| learned_votes: exact posterior under a vote / team-choice / quest-card likelihood fitted on the visible games (temperature 0.5 chosen on train) | – | 0.4597 | −0.0179 ± 0.0012 | +0.177 | 34/2 |
| combined: learned_votes + full knowledge | – | 0.4461 | −0.0314 ± 0.0013 | +0.300 | 36/0 |
| weaker: Strict, i.e. hypotheses removed (`strict_only`, also the reference's `CSP_Strict`) | Q 0.4995, R_old −0.036 | 0.4825 | +0.0050 ± 0.0004 | −0.047 | 3/33 |
| weaker: role-count prior (`baseline/prior.py`) | Q 0.2586, R_old −0.430 | 0.7276 | +0.2500 ± 0.0012 | −2.27 | 0/36 |

Mean Brier per experiment (six viewpoints):

| experiment | Strict | reference HypIG | better_knowledge | learned_votes | combined |
|---|---:|---:|---:|---:|---:|
| 5p | 0.4250 | 0.4167 | 0.4036 | 0.3987 | 0.3855 |
| 6p | 0.4477 | 0.4401 | 0.4288 | 0.4185 | 0.4068 |
| 7p | 0.5298 | 0.5260 | 0.5095 | 0.5088 | 0.4915 |
| 8p | 0.5244 | 0.5221 | 0.5067 | 0.4964 | 0.4806 |
| 9p | 0.4902 | 0.4872 | 0.4756 | 0.4761 | 0.4639 |
| 10p | 0.5538 | 0.5524 | 0.5355 | 0.5377 | 0.5197 |

## What changed

1. **The hidden test runs the method on hidden inputs.** Half of every player
   count (6,197 of 12,393 usable games, seeded) is held out. These games exist
   only in `eval/test/heldout.dat`, encoded, with inputs and roles in separate
   sections. They were removed from `data/avalonlogs_raw/` (6,205 files remain;
   6,196 usable). `eval/test/heldout_ids.txt` holds hashed file names so that
   `scripts/download.sh` drops them from a fresh archive download and deletes
   the archive. `bash scripts/evaluate_test.sh` (no arguments) writes the inputs
   to a fresh temporary directory, runs `bash scripts/predict.sh <in> <out>`
   with `heldout.dat` set to mode 000, and decodes the roles in memory only
   after the predictor returns. In the job container the probe confirmed the
   file was unreadable during the run (`PermissionError`). The evaluator checks
   the file's SHA-256. There is no wall-clock limit anywhere.
2. **One instance per game.** Each game becomes one instance: the public
   history up to one uniformly sampled completed quest (the paper samples one
   quest per game), from one viewpoint (Obj/MRL/PCV/MRG/LSV/EVM, balanced within
   each player count). Viewpoint information is given explicitly (`sees_evil`,
   `merlin_candidates`), and players appear as seat labels. With one instance
   per game, nobody can combine two viewpoints' private information, or use a
   later quest, from the same game.
3. **Everything is recomputed from raw predictions, with validity rules.** The
   evaluator owns the labels, the game pool and the size of the test. Every
   instance needs: probabilities over exactly the instance's players and the
   declared roles; finite values in [0,1]; rows summing to 1; role totals equal
   to the composition; and a complete assignment with the declared counts. The
   predictor must also exit 0. Otherwise that method scores Brier 2 and marginal
   0 in every metric of every experiment. If a run produces nothing at all, the
   failure is written under the method names in `scoring/reference.json`.
4. **No whitelist.** Every method name in `predictions.json` is scored.
   `scoring/scores.json` is now only the train-slice development score
   (`scripts/evaluate.sh`); the evaluators never read it.
5. **The ranked metric is now the Brier score.** The paper's marginal accuracy
   is linear in the prediction, so moving all mass onto the most likely
   assignment raises it without better inference. On this test that trick
   (`sharpen_onehot`) gains +0.021 marginal accuracy, more than the honest
   knowledge fix (+0.013); a milder power-3 sharpening gains +0.008. Any
   positive coefficient on the linear metric leaves a small sharpening that
   pays. So `{view}_brier` is ranked (coefficient 1, lower is better).
   `{view}_marginal` is still reported for comparison with the paper, with
   coefficient 0. Brier is the proper version of "probability on the true
   role" and measures the calibrated posteriors the paper claims.
6. **The reference runs inside the test.** `method/csp4sdg_avalonlogs.py`
   implements the paper's AvalonLogs extraction, the official viewpoint
   evidence and Eq. 1–3 with IG weights on each viewpoint's feasible worlds. It
   runs exactly by enumerating evil subsets and the role assignments within
   each side. It agrees with literal role-level enumeration
   (`method/csp4sdg_enumerate.py`, on `method/sdg_framework.py`) to 5e-11 on
   191 instances of all sizes and views (`redteam/iter11/enumeration_check.json`).
   The whole hidden test takes about 4 s. Two small departures from the official
   code are documented in `briefing/method.md`: the random suspect is seeded per
   instance (not drawn from a global RNG in file order), and the rare explicit
   `assassin` role is included in `sees_evil`. The redteam's Merlin finding is
   *not* folded into the reference, because the paper's own code uses only
   "listed players are evil". Using the completeness of the lists remains an
   improvement open to future work (better_knowledge).
7. **Removed stale or unsafe artifacts.** The 12k cached old-format outputs
   (`data/avalonlogs_solve`) and constraint files carrying true roles
   (`data/avalonlogs_constraints`) are gone. So are `data/convert_avalonlogs.py`,
   `eval/evaluator.py`, and the label-reading solvers
   `method/avalon_logs_solver*.py`.
8. **Weights.** The never-run Avalon-NLU and Mafia experiments moved, unchanged,
   to `_paper_only_experiments` in `scoring/reference.json`. They had 46% of the
   weight while no attempt could ever produce them. The six AvalonLogs
   experiments now sum to 1: 6p 0.35 and 9p 0.25 (the paper's main-text Table
   3), and 5p/7p/8p/10p 0.10 each (Appendix H stresses the pattern across all
   sizes). Before, 7p/8p/10p each had less than a tenth of the 6p weight, so a
   method could trade them away almost for free. The paper's reported numbers
   are unchanged.

## Shortcuts: fix, score before → after

| shortcut | before (REDTEAM) | fix | after |
|---|---|---|---|
| leaked labels (copy roles from visible inputs) | Q 1.000, R_old +0.779, works | inputs carry no roles; test games removed from visible data | closest analogue `lookup_visible` (match the public history in the visible logs; 883 matches are coincidental short prefixes, 193 with the same composition): W 0.5032, dW +0.026, R −0.24, **fails** |
| constant ones (non-normalised) | Q 1.000, R_old +0.779, works | validity rules | failed, worst values, R −14.5 |
| impossible values (10) | Q 10.0, R_old +15.46, works | validity rules | failed, R −14.5 |
| relabel (method writes its own ground truth) | R_old +0.779, works | evaluator owns labels | one-hot on an arbitrary legal world: W 1.4525, R −9.24 |
| pool (keep easy games only) | R_old +0.272 on 19/36 metrics, works | evaluator fixes the instances; a missing instance fails the method | failed, R −14.5 |
| future copy (later-quest predictions into earlier slots) | beats reproduction on 36/36 | an instance holds only the prefix up to its cut; one instance per game | not constructible |
| empty / malformed outputs | 0 (ties paper, above reproduction), works | failure = worst values everywhere | failed, R −14.5 (both) |
| writable whitelist (`scoring/scores.json`) | 0, works | evaluators read no whitelist | `filter` run identical to the reference, both methods scored |
| better method under a new name | silently omitted | names discovered from predictions | `rename`: `FullKnowledge_NewName` scored, R +0.119 |
| empty MAP | exact reproduction tie | `best` must be a complete legal assignment | failed, R −14.5 |
| replace method / crash, keep old predictions | exact reproduction tie | test runs the method on hidden instances; non-zero exit fails | `crash` failed (both methods), R −14.5 |
| direct score forgery | already failed | unchanged (evaluator overwrites) | `forge_scores` identical to reference |
| failed objective view + exposed labels elsewhere | R_old +0.511, works | needs labels, which no longer reach the method; any invalid output fails all experiments | not constructible |
| **new:** one-hot sharpening of the reference posterior | (not run) under the old linear metric: marginal +0.021, above the honest fix | Brier ranked, marginal coefficient 0 | W 0.9139, dW +0.436, R −4.31 |
| **new:** power sharpening (γ=3, re-projected) | marginal +0.008 | same | dW +0.0080 ± 0.0007, R −0.081 |
| **new:** mild recalibration (γ=1.25 / 0.8) | marginal +0.0013 / −0.0012 | same | dW +0.0001 / +0.0003, R −0.001 / −0.003 (no gain) |
| **new:** read the hidden file while the method runs | – | mode 000 during the run; roles decoded after | `PermissionError` in the job container |

## Shortcuts left, and why

- **Lookup of the public corpus.** The hidden games are public AvalonLogs
  games. Their raw logs (with roles) are on GitHub, and they are also in this
  repository's git history: earlier commits tracked all of
  `data/avalonlogs_raw`, `data/avalonlogs_constraints` and
  `data/avalonlogs_solve`. A method that ships those logs and matches an
  instance's public history would recover the roles. History cannot be
  rewritten here, and real data is what makes the task meaningful. Seat labels,
  truncation, one viewpoint per game and removal from the visible data mean
  this takes deliberate use of forbidden data. `scoring/CONSTRAINTS.md` forbids
  it explicitly; the grader has to catch it.
- **Same-user file access.** Mode 000 stops a plain read, but a method running
  as the same user could chmod the file back and decode it with the key in
  `eval/test/evaluate.py`. This is blatant (it touches `eval/`) and left to the
  grader.
- **Pooling across test instances** (e.g. fitting a model to the unlabelled
  test inputs). No game appears twice, so this leaks no roles. It is declared
  out of bounds but not enforced.
- **Honest alternatives the test cannot tell apart:** literal enumeration and
  the grouped solver give the same posteriors. That is a property of the
  task, not a loophole.

## Reference score before and after

- **Before:** cached outputs mixing two IG definitions, all quests of each game
  averaged, linear metric. Q = 0.5022 over 36 marginal metrics. HypIG − Strict
  on the objective view: +0.0044 (6p) and +0.0017 (9p).
- **After:** the reference rerun from the final code in the job; it produces
  `scoring/scores_test.json`, `scores_train.json` and `scores.json`. W = 0.4776
  (Strict 0.4825); weighted marginal accuracy 0.5219 under the new aggregation
  and weights. Objective marginal accuracy, reproduced vs paper (Table 3):

  | | 6p Strict | 6p HypIG | 9p Strict | 9p HypIG |
  |---|---|---|---|---|
  | reproduced | 0.328 | 0.333 | 0.313 | 0.316 |
  | paper | 0.290 | 0.326 | 0.302 | 0.360 |

  HypIG beats Strict by dW −0.0050 ± 0.0004 (12 SE), on 33/36 Brier metrics,
  and on the objective view at every player count. That is the paper's
  direction at 6p and 9p.
- **Seed noise:** the only random step is which team member a rejecting voter
  is taken to suspect. Three other seeds move W by at most 0.0002, 25× less
  than the HypIG effect. The largest single-metric seed range is 0.0024.
- **Train and test agree** within sampling noise (e.g. 6p objective Brier
  0.681 on train vs 0.665 on test).

## Headroom check

- No ranked metric is at its bound. Reference Brier per cell ranges from 0.25
  (EVM 5p) to 0.74 (Obj 7p); the bound is 0. The only bound-valued cells in
  `reference.json` are the paper-only Mafia `MAF_*` values (1.0), which are
  never scored.
- Three honest variants beat the reference by 15–31 paired SEs (table above).
  The learned likelihood targets where the paper's method falls short: soft
  evidence weighted by hand-set or IG heuristics instead of calibrated
  likelihoods. The full-knowledge variant targets incomplete use of private
  information.
- No single simple variant reaches the bound. The best (combined) is at W 0.446.
- Brute force: the paper's method is itself exhaustive enumeration at these
  sizes; there is no cheaper exhaustive search that it avoids, and enumerating
  worlds is exactly the reference.
- Simple baseline: the role-count prior is far below (W 0.728). Closed-form
  post-processing of the reference (sharpening or recalibration) does not
  outrank it.
- No new experiment was added: the existing ones have headroom that honest
  methods reach.

## Could not fix / limitations

- The paper's LLM baselines and its Avalon-NLU and Mafia experiments cannot be
  run here (no dialogue data or LLM). Their numbers stay in `reference.json` as
  paper-only. Assertions are not exercised: AvalonLogs has none, and per
  Appendix F its constraints are extracted programmatically.
- The HypIG effect is much smaller than the paper's 9p numbers (+0.002 vs
  +0.058 marginal accuracy). The paper reports regressions at 5/8/10p; this
  reproduction shows small gains there. The paper's AvalonLogs numbers came from
  the small subset of games with LLM runs, so they are on the same scale but are
  not targets.
- The 9p and 10p cells are small (about 70 and 50 instances per viewpoint)
  because the corpus has only 843 and 600 such games, and half of each is
  already held out. Paired SEs stay well below the honest effects, but single
  cells there are noisy.
- The protocol changed (instances, metric, weights), so old cached outputs and
  scores are not comparable with the new ones.
- The public-corpus lookup above stays open.
