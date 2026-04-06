# Evaluation Targets

## Primary: role_identification_accuracy
Improve the accuracy of CSP-based role inference in social deduction games.

- **Metric**: marginal_accuracy (higher is better) — average probability assigned to true roles
- **Metric**: map_accuracy (higher is better) — fraction of exact role assignments correct
- **Experiment**: avalonlogs_6player, avalonlogs_9player (Tables 3 and 8 in the paper)

## Primary: llm_vs_csp_gap
Demonstrate that structured constraint reasoning outperforms language-model-only approaches.

- **Metric**: The CSP methods should score higher than LLM-Only on all role perspectives
- **Experiment**: avalonnlu_truth_main (Table 2 in the paper)

## Constraint: hypothesis_weighting_quality
Auto IG weighting should match or exceed manual weight tuning.

- **Metric**: Marginal accuracy of +HypIG should be within 2pp of +HypM
- **Experiment**: Compare CSP_+HypIG vs CSP_+HypM on all datasets

## Ablation: constraint_types
Removing soft constraints should degrade accuracy, confirming they add value.

- **Metric**: Strict should score below +Assert below +HypIG
- **Direction**: Each added constraint type should improve accuracy
- **Experiment**: Compare Strict < +Assert < +HypIG across all datasets

## Compliance Checklist
- [ ] Marginal accuracy is computed correctly (average probability of true roles)
- [ ] MAP accuracy is computed correctly (fraction of players with correct exact roles)
- [ ] Results are averaged over all games and all quests within each game
- [ ] 6-player results match the paper's Table 3 AvalonLogs-6p section
- [ ] 9-player results match the paper's Table 3 AvalonLogs-9p section
