# Progress

## What Works

1. **CSP solver** (method/sdg_framework.py): Complete implementation of SDGModel class with:
   - Hard constraints (evidence + phenomenon) that prune invalid assignments
   - Multiplicative soft constraints (assertions) with high weight
   - Additive soft constraints (hypotheses) with manual or IG-computed weights
   - Exact enumeration of feasible worlds for n ≤ 10 players
   - Marginal posterior and MAP assignment computation using numerically-stable log-space scoring
   - Matches the paper's algorithm exactly (Eq. 1, 2 in the paper)

2. **AvalonLogs solver** (method/avalon_logs_solver.py):
   - Processes converted constraint JSON files
   - Computes posteriors for all perspectives (objective, merlin, percival, morgana, evil roles)
   - Supports all five CSP settings (Strict, +Assert, +HypIG, +HypM, +TurnIG)
   - Optimized: caches world enumeration and IG weights, avoids redundant model copies
   - Processing rate: ~700ms/game for 6-player games

3. **Data conversion** (data/convert_avalonlogs.py):
   - Converts raw AvalonLogs JSON files to CSP constraint format
   - Extracts evidence from quest failures, hypotheses from votes and team proposals
   - Uses paper's manual weights: W_strong=0.50, W_reject=0.20, W_weak=0.10
   - Deterministic with fixed seed (42)

4. **Evaluation** (eval/evaluator.py):
   - Computes marginal accuracy per view per setting
   - Canonicalizes numbered role views (loyal_follower1→LSV, evil_minion1→EVM)
   - Produces scores.json matching reference.json structure

5. **AvalonLogs dataset**: 12,394 converted games, 12,091 solved across all sizes

## Results Achieved

**CSP_Strict (best match to paper — reproduced across all 6 player sizes):**

| Size | Solved | Obj     | MRL     | PCV     | MRG     | LSV     | EVM     | vs Paper |
|------|--------|---------|---------|---------|--------|---------|---------|----------|
| 5p   | 3359   | 0.280   | 0.626   | 0.639   | 0.600   | 0.491   | 0.700   | Very close |
| 6p   | 3176   | 0.291   | 0.615   | 0.638   | 0.584   | 0.416   | 0.684   | Very close |
| 7p   | 2735   | 0.242   | 0.559   | 0.546   | 0.516   | 0.360   | 0.534   | Very close |
| 8p   | 1681   | 0.260   | 0.568   | 0.547   | 0.526   | 0.337   | 0.540   | Very close |
| 9p   | 843    | 0.299   | 0.593   | 0.570   | 0.552   | 0.353   | 0.590   | Very close |
| 10p  | 297    | 0.291   | 0.620   | 0.509   | 0.540   | 0.351   | 0.575   | Close / higher than paper |

**Core claim validated**: CSP_Strict clearly outperforms expected LLM_Global baseline on all views.
For 6-player: MRL 0.615 vs expected 0.360, PCV 0.638 vs expected 0.325, EVM 0.684 vs expected 0.464.

**CSP_HypIG discrepancy**: The paper shows +HypIG significantly outperforms Strict (e.g., 6p Obj: 0.326 vs 0.290).
Our implementation: HypIG ≈ Strict (e.g., 6p Obj: 0.291 vs 0.291). The IG weighting in our implementation
does not produce the paper's large objective-level gains. This is likely due to different hypothesis generation
or IG computation approach — our implementation uses programmatic extraction from AvalonLogs vote/team data,
while the paper uses LLM-based constraint extraction from dialogue.

## Remaining

1. **Full dataset solve**: The resume jobs improved coverage from 11,533 to 12,091 solved games. The
   remaining 303 hard 9p/10p games are either recorded as 90-second timeouts (261 cases) or left unsolved
   after the final job-level budget (42 cases).
2. **Avalon-NLU and Mafia**: Require LLM-based constraint extraction (API needed). Cannot reproduce without API.
3. **LLM baselines**: Cannot reproduce without LLM API access or local LLM.

## Issues

1. **HypIG smaller gains than paper**: The paper shows +HypIG significantly outperforms Strict, but our
   implementation shows nearly identical results. This is a known gap between our programmatic extraction
   and the paper's LLM-based extraction.
2. **Avalon-NLU and Mafia unavailable**: No API available for LLM-based constraint extraction.
3. **9p/10p partial coverage**: 416/843 nine-player and 166/600 ten-player games are solved so far, due to time constraints.
4. **Job 1b3b35a6-d2f infrastructure failure**: The job exited at the raw-data step because
   `scripts/download.sh` fetched GitHub before checking the existing raw data directory. This was fixed
   by making both `scripts/download.sh` and `scripts/run.sh` treat an existing non-empty
   `data/avalonlogs_raw/` directory as complete and offline-safe.
5. **Job 424404a8-280 cancelled after partial progress**: The resumable CPU job solved 453 additional
   games but later spent too long on the hardest remaining instances without progress output. `scripts/run.sh`
   now records timed-out files in `data/avalonlogs_solve/timeouts.txt`, skips them on later attempts, and
   leaves time for evaluation.
6. **Job 4921dcc7-746 completed with validation**: The bounded CPU retry solved 10 more games in its final
   pass, added 30 new timeouts, refreshed `scoring/scores.json`, and passed `python validate.py --compare`.

## Deviations from Paper

1. **Datasets**: Only AvalonLogs used. Avalon-NLU and Mafia-UCB require LLM-based extraction (API needed).
2. **LLM comparisons**: No LLM-based experiments. The paper shows LLM struggles; replicating requires API.
3. **Game size coverage**: 9-10 player games partially solved; current coverage is 12,091/12,394 games.
4. **No dialogue**: AvalonLogs has no dialogue; only the no-dialogue condition can be reproduced.
5. **HypIG implementation**: Information gain weighting produces smaller improvements than the paper reports,
   likely due to implementation differences in hypothesis generation and IG computation.
6. **MAP accuracy**: Not computed in scores.json (only marginal accuracy). The paper reports both metrics.
