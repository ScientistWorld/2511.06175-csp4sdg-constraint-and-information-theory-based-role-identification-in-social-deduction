# CSP4SDG: Constraint and Information-Theory Based Role Identification in Social Deduction Games with LLM-Enhanced Inference

<!-- scope-note -->
> [!NOTE]
> **Not a full reproduction of the paper.** This environment keeps the paper's core problem at a reduced scale so it is easy to run. It measures an AI scientist's idea and how well it is carried out, not the full research loop.

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2511.06175"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2511.06175-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| **Paper ID** | [2511.06175](https://arxiv.org/abs/2511.06175) |
|:---|:---|
| **Domain** | Game AI / Multi-Agent Systems / Constraint Satisfaction |
| **TL;DR** | A probabilistic constraint-satisfaction framework (CSP4SDG) outperforms LLMs at hidden-role inference in social deduction games by modeling game rules as hard constraints and player statements as weighted soft constraints. |

## Summary

The paper tackles the role identification problem in Social Deduction Games (Avalon, Mafia, Werewolf), where players must infer each other's hidden identities from game events and dialogue. CSP4SDG maps all game information to four constraint types (evidence, phenomenon, assertions, hypotheses), then uses a CSP solver with information-gain-weighted soft constraints to compute calibrated role posteriors. The key insight is that the combinatorial game structure provides strong inductive bias — structured constraint reasoning dramatically outperforms large language models, even the most capable ones, on this task.

## Problem

In social deduction games such as Avalon, Mafia, and Werewolf, players have hidden roles and reveal information only indirectly through public actions, optional communication, and game outcomes. The central task is **role identification**: given the observed game history and the role composition for that game, infer the most likely role for each player.

The problem is difficult because:
- Observations are incomplete and noisy.
- Some players benefit from misleading others.
- Different roles have different private information.
- The number of possible full role assignments grows rapidly with player count.
- Public events and communication can support multiple conflicting explanations.

## The paper's method

CSP4SDG: A **Constraint Satisfaction Problem (CSP)** framework for role inference in Social Deduction Games. It decomposes game information into four linguistically-agnostic constraint types, then uses a probabilistic CSP solver with information-gain weighting to compute calibrated role posteriors.

## Key results of the paper

- **CSP methods dominate**: On Avalon-NLU (21 games, 6 players), CSP+HypIG achieves ~0.76 marginal / 0.79 MAP accuracy for Percival vs. ~0.16 marginal / 0.19 MAP for LLM-Global
- **Information-gain weighting is effective**: IG-auto-weighted hypotheses perform on par with hand-tuned weights, eliminating manual tuning
- **LLMs amplify heuristics**: Across GPT-4o-mini, GPT-4o, GPT-4.1, DeepSeek-v3, Gemini-2.0-flash, accuracy barely changes — suggesting the bottleneck is combinatorial reasoning, not language understanding
- **Hybrid LLM+CSP helps LLMs**: All LLM backbones gain ~10-20pp when augmented with CSP posteriors

## Run it

```bash
pip install sciworld
sw research 2511.06175 --mode innovate --agent claude-code
sw evaluate 2511.06175
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

