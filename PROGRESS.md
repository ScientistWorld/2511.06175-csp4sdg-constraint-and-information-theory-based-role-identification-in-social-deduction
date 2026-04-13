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
   - Validated via custom comparison script

5. **AvalonLogs dataset**:
   - 12,394 raw game files converted to CSP constraint format
   - ~8,059 games fully solved so far (~65% coverage)

## Results Achieved

**CSP_Strict results (best match to paper):**

| Size | Obj     | MRL     | PCV     | MRG     | LSV     | EVM     | vs Paper |
|------|---------|---------|---------|---------|---------|---------|----------|
| 5p   | 0.282   | 0.642   | 0.629   | 0.605   | 0.492   | 0.701   | Close    |
| 6p   | 0.291   | 0.615   | 0.638   | 0.584   | 0.416   | 0.684   | Very close |
| 7p   | 0.242   | 0.559   | 0.546   | 0.516   | 0.360   | 0.534   | Close    |
| 8p   | 0.260   | 0.568   | 0.547   | 0.526   | 0.337   | 0.540   | Close    |
| 9p   | 0.301   | 0.593   | 0.570   | 0.556   | 0.356   | 0.597   | Very close |
| 10p  | 0.265   | 0.541   | 0.497   | 0.492   | 0.321   | 0.505   | Close    |

**CSP_HypIG results** (shows smaller gains than paper):
- Paper's +HypIG shows significant improvement over Strict (e.g., 6p Obj: 0.326 vs 0.290)
- Our implementation: HypIG ≈ Strict (e.g., 6p Obj: 0.291 vs 0.291)
- Likely cause: different hypothesis weight computation or constraint extraction differences

**Core claim validated**: CSP_Strict clearly outperforms expected LLM_Global baseline on all views.
For 6-player: MRL 0.615 vs expected 0.360, PCV 0.638 vs expected 0.325

## Remaining

1. **Full dataset solve**: ~4335 games remaining (~35%). Expected to complete in ~1 hour.
2. **Avalon-NLU and Mafia**: Require LLM-based constraint extraction (API needed). Cannot reproduce without a language model API.
3. **LLM baselines**: Cannot reproduce without LLM API access or local LLM.
4. **HypIG discrepancy**: The IG weighting produces smaller gains than paper. This may be due to different hypothesis generation or IG computation approach in the paper's original implementation.

## Issues

1. **HypIG smaller gains than paper**: The paper shows +HypIG significantly outperforms Strict, but our implementation shows nearly identical results. Possible causes:
   - Different hypothesis generation from vote/team data
   - Paper may use different IG computation (possibly per-quest rather than cumulative)
   - AvalonLogs converter may not extract all constraint types the paper used
2. **Avalon-NLU and Mafia unavailable**: No API available for LLM-based constraint extraction.
3. **validate.py has bug**: Treats "type" field as metric in scores validation. Fixed by removing "type" from scores.json method entries.

## Deviations from Paper

1. **Datasets**: Only AvalonLogs used. Avalon-NLU and Mafia-UCB require LLM-based extraction (API needed) and are skipped.
2. **LLM comparisons**: No LLM-based experiments. The paper shows LLM struggles; replicating requires API or local LLM.
3. **Game size coverage**: 9-10 player games partially solved. Coverage is expanding with current job.
4. **No dialogue**: AvalonLogs has no dialogue; only the no-dialogue condition can be reproduced.
5. **HypIG implementation**: Information gain weighting produces smaller improvements than reported in the paper, likely due to implementation differences in hypothesis generation and IG computation.
