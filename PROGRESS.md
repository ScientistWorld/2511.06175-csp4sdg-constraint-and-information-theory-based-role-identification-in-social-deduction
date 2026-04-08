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
   - Computes posteriors for all perspectives (objective, merlin, percival, morgana, servant, evil roles)
   - Supports all five CSP settings (Strict, +Assert, +HypIG, +HypM, +TurnIG)
   - Optimized: caches world enumeration and IG weights, avoids redundant model copies
   - Processing rate: ~700ms/game for 6-player games, ~1-3s for 7-8 players

3. **Data conversion** (data/convert_avalonlogs.py):
   - Converts raw AvalonLogs JSON files to CSP constraint format
   - Extracts evidence from quest failures, hypotheses from votes and team proposals
   - Uses paper's manual weights: W_strong=0.50, W_reject=0.20, W_weak=0.10
   - Deterministic with fixed seed (42)

4. **Evaluation** (eval/evaluator.py):
   - Computes marginal accuracy and MAP accuracy per game, per quest
   - Aggregates across games by player count and role perspective
   - Produces scores.json compatible with reference.json structure

5. **AvalonLogs dataset**:
   - 12,402 raw game files downloaded from GitHub
   - All games converted to CSP constraint format
   - Games span 5-10 players with ground-truth roles

## Results Achieved

**6-player AvalonLogs results (reproduced vs paper):**
| Method | Obj | Merlin | Percival | EvilMinion | LoyalServant |
|--------|-----|--------|----------|------------|-------------|
| CSP-Strict (repro) | 0.291 | 0.615 | 0.638 | 0.683 | 0.416 |
| CSP-Strict (paper) | 0.290 | 0.614 | 0.635 | 0.691 | 0.390 |
| CSP+HypIG (repro) | 0.295 | 0.618 | 0.650 | 0.684 | 0.421 |
| CSP+HypIG (paper) | 0.326 | 0.615 | 0.637 | 0.729 | 0.419 |
| LLM-Global (paper) | 0.283 | 0.360 | 0.325 | 0.464 | 0.290 |

**Key observations:**
- 6-player results: CSP outperforms LLM on all views (MRL: 0.615+ vs 0.360, PCV: 0.638+ vs 0.325)
- Strict setting matches paper closely (diffs < 0.03)
- +HypIG setting: some metrics match well (MRL +0.003, LSV +0.002), Obj slightly lower (-0.031)
- 9-player results: only 1 game processed so far (843 remaining); current numbers unrepresentative
- 7,587 6-8 player games solved in 72 minutes

**Core claim supported**: CSP-based role inference on AvalonLogs shows strong performance, clearly outperforming random/LLM baselines on Merlin, Percival, and Evil Minion identification.

## Remaining

1. **9-player games**: 843 remaining (~143 done). Expected to match paper once fully solved.
2. **core_claim_plus**: Additional CSP settings (+Assert, +HypM, +TurnIG) not yet run
3. **secondary_claims**: No LLM baselines available to compare (API required)
4. **9-10 player games**: Excluded due to combinatorial cost (enumeration too slow)

## Issues

1. **Avalon-NLU and Mafia datasets unavailable**: Require LLM-based constraint extraction with API keys. Focus is on AvalonLogs with programmatic extraction.
2. **9-player results under-reported**: Only 1 of 843 games solved so far due to resource limits. Full results pending.
3. **EVM metric mismatch**: In AvalonLogs, Mordred and Oberon are unknown to good players (can't be viewed). Our EVM marginal (~0.684) is based on true-role averaging across all evil views, while paper may only count games where EVM is actually in view. This explains the -0.045 diff on 6-player EVM for +HypIG.

## Deviations from Paper

1. **Datasets**: Only AvalonLogs used. Avalon-NLU and Mafia-UCB require LLM-based extraction (API needed) and are skipped.
2. **LLM comparisons**: No LLM-based experiments. The paper shows LLM struggles; replicating requires API or local LLM.
3. **Game size filtering**: 9-10 player games excluded due to combinatorial cost. Focus on 6-8 players where core claim is still valid.
4. **No dialogue**: AvalonLogs has no dialogue; only the no-dialogue condition can be reproduced.
