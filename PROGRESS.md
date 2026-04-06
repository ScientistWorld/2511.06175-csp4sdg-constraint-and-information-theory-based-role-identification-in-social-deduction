# Progress

## What Works

1. **CSP solver** (method/sdg_framework.py): Complete implementation of the SDGModel class with hard constraints, multiplicative assertions, additive hypotheses, and IG auto-weighting. Matches the paper's algorithm exactly.

2. **AvalonLogs solver** (method/avalon_logs_solver.py): Processes converted constraint JSON files and computes marginal posteriors and MAP assignments for all perspectives (objective, merlin, percival, morgana, servant, evil roles) across all quests.

3. **Data conversion** (data/convert_avalonlogs.py): Converts raw AvalonLogs JSON files to CSP constraint format using the same logic as the paper's batch_convert_structured.py. Includes programmatic constraint extraction from votes, quests, and team proposals.

4. **Evaluation** (eval/evaluator.py): Computes marginal accuracy and MAP accuracy from solver results, aggregated per game then across games.

5. **Optimized solver**: Processes 6-8 player games in ~1-10s per game. 9-10 player games are slower (~160s each) due to combinatorial explosion (9000+ worlds).

## Results

Paper's AvalonLogs results (Table 3, 6-player, marginal accuracy):
- CSP-Strict: Obj=0.290, Merlin=0.614, Percival=0.635, EvilMinion=0.691
- CSP+HypIG: Obj=0.326, Merlin=0.615, Percival=0.637, EvilMinion=0.729
- LLM-Global: Obj=0.283, Merlin=0.360, Percival=0.325, EvilMinion=0.464
- Random: ~0.267 for all roles (uniform prior)

Awaiting full batch results from job.

## Remaining

1. **Full batch processing**: Process all 6-8 player games (~10,000 games) to get robust accuracy estimates
2. **Validate against paper**: Compare reproduced numbers with reference.json
3. **core_claim**: Demonstrate that CSP significantly outperforms random on AvalonLogs
4. **Expand to more experiments**: 7-player, 8-player, 9-player game sizes

## Issues

1. **9-10 player games too slow**: World enumeration has ~9000-90000 worlds. Need either sampling or a smarter enumeration approach. Filtered to 6-8 player games for now.
2. **Avalon-NLU and Mafia datasets unavailable**: These require LLM-based constraint extraction with OpenAI API keys. Focus is on AvalonLogs which has programmatic extraction.

## Deviations from Paper

1. **Datasets**: Only AvalonLogs is used. The paper also evaluates on Avalon-NLU and Mafia-UCB, which require LLM-based constraint extraction. These are skipped because they need API keys and the LLM extraction step.
2. **LLM comparisons**: No LLM-based experiments are run. The paper shows LLM struggles with combinatorial reasoning, but replicating this would require API calls or a local LLM.
3. **Game size filtering**: 9-10 player games are excluded due to computational cost (combinatorial explosion). Focus is on 6-8 player games where results should still validate the core claim.
