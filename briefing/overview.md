# Overview

- **Paper ID:** 2511.06175
- **Title:** CSP4SDG: Constraint and Information-Theory Based Role Identification in Social Deduction Games with LLM-Enhanced Inference
- **Domain:** Game AI / Multi-Agent Systems / Constraint Satisfaction
- **TL;DR:** A probabilistic constraint-satisfaction framework (CSP4SDG) outperforms LLMs at hidden-role inference in social deduction games by modeling game rules as hard constraints and player statements as weighted soft constraints.

## Short Summary

The paper tackles the role identification problem in Social Deduction Games (Avalon, Mafia, Werewolf), where players must infer each other's hidden identities from game events and dialogue. CSP4SDG maps all game information to four constraint types (evidence, phenomenon, assertions, hypotheses), then uses a CSP solver with information-gain-weighted soft constraints to compute calibrated role posteriors. The key insight is that the combinatorial game structure provides strong inductive bias — structured constraint reasoning dramatically outperforms large language models, even the most capable ones, on this task.

## Key Results

- **CSP methods dominate**: On Avalon-NLU (21 games, 6 players), CSP+HypIG achieves ~0.76 MAP accuracy for Percival vs. ~0.19 for LLM-Global — a 4x improvement
- **Information-gain weighting is effective**: IG-auto-weighted hypotheses perform on par with hand-tuned weights, eliminating manual tuning
- **LLMs amplify heuristics**: Across GPT-4o-mini, GPT-4o, GPT-4.1, DeepSeek-v3, Gemini-2.0-flash, accuracy barely changes — suggesting the bottleneck is combinatorial reasoning, not language understanding
- **Hybrid LLM+CSP helps LLMs**: All LLM backbones gain ~10-20pp when augmented with CSP posteriors
