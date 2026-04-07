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

---

# Problem Definition

What problem does this paper address? Write this so that someone with no knowledge of the paper can understand what needs to be solved and how success is measured.

Do NOT describe the paper's method or solution here — only the problem itself. Think about if a future scientist agent try to solve this problem from scratch without knowing what approach the paper took. If you leak the solution, you compromise the benchmark.

## Research Question

In Social Deduction Games (SDGs) like Avalon, Mafia, and Werewolf, players are secretly assigned roles and must deduce each other's hidden identities through game events (votes, quests, eliminations) and dialogue. The core challenge is **role identification**: given partial, noisy, and often deceptive information, what is the most likely role assignment for each player?

The problem is hard because:
- Information is incomplete and distributed across players
- Players deliberately deceive each other
- The combinatorial space of possible role assignments grows factorially with player count
- Some roles have special knowledge (e.g., Merlin knows who is evil) that provides asymmetric information
- Dialogue contains both honest claims and strategic lies

## Why It Matters

Accurate role identification is the foundation of decision-making in SDGs — for both human players and AI agents. If an agent cannot correctly infer who is on its team, it cannot coordinate effectively or deceive opponents. This problem also generalizes to any multi-agent setting where agents must reason about hidden state from public observations and communication.

## Success Criteria

A successful role identification system should:
1. **Maximise marginal accuracy**: assign high probability to the true role of each player
2. **Maximise MAP (maximum-a-posteriori) accuracy**: correctly recover the exact full role assignment
3. **Be interpretable**: provide calibrated probabilities and explain why certain roles are likely
4. **Be game-agnostic**: work across different social deduction games without per-game tuning
5. **Be trainable-free**: not require learning from game data (the combinatorial structure is known)

---

# Paper's Method

How the paper approaches the problem, i.e. the paper's core contributions.

## Key Contribution

CSP4SDG: A **Constraint Satisfaction Problem (CSP)** framework for role inference in Social Deduction Games. It decomposes game information into four linguistically-agnostic constraint types, then uses a probabilistic CSP solver with information-gain weighting to compute calibrated role posteriors.

## Approach

### Four Constraint Types

1. **Evidence (hard)**: Absolutely true facts — e.g., the assassin's target was Merlin, a night-kill victim is bystander
2. **Phenomenon (hard)**: Aggregate constraints from game events — e.g., at least one evil on a failed quest team
3. **Assertions (soft, high weight)**: Player claims treated as likely true — e.g., "I am Percival", "this team is clean"
4. **Hypotheses (soft, low weight)**: Weaker speculative statements — e.g., "X looks evil" (from votes or chat)

### CSP-Based Inference

The framework formulates role assignment as a constraint satisfaction problem:
- Variables: each player's role
- Hard constraints (E ∪ P): prune infeasible assignments
- Soft constraints (A ∪ H): score remaining assignments

**Scoring function**: For an assignment $a$:
$$S(a) = \left(\prod_{c \in A, a \models c} w_A\right) \cdot \left(1 + \sum_{h \in H, a \models h} w_H(h)\right)$$

where $w_A \gg 1$ is a high assertion weight, and $w_H(h)$ are hypothesis weights.

**Posterior**: $\Pr(a | \mathcal{C}_t) = S(a) / \sum_{a' \in AS_t} S(a')$

### Information-Gain Weighting

Rather than hand-tuning hypothesis weights, the paper computes Information Gain (IG) for each hypothesis as the entropy reduction when incorporating it. This automatically down-weights noisy hypotheses and up-weights informative ones.

### Three Inference Methods

1. **CSP-only**: Pure constraint-based inference
2. **LLM-only**: Prompt the LLM directly with dialogue history
3. **LLM+CSP**: Augment LLM prompts with CSP posteriors as auxiliary input

## Main Claims

1. CSP-based methods (with proper constraint modeling) consistently outperform LLM-only approaches in role identification accuracy
2. Information-gain auto-weighting for hypotheses is near-optimal vs. hand-tuned weights
3. The hybrid LLM+CSP approach adds modest value to LLMs but the CSP remains the dominant component
4. Pure LLMs struggle with combinatorial reasoning even with large model scale

---

# Evaluation

How success is measured. Describe only the metrics, targets, and evaluation procedure — do NOT describe the paper's method or how they achieved these results. Think of this as a general evaluation protocol for other scientists trying to solve the same problem, where they should not see this paper's solution.

## Metrics

Two accuracy metrics are used to evaluate role identification:

### Marginal Accuracy (MA)
For a game with $P$ players, let $r_p^*$ be player $p$'s true role and $a_{p,r}$ be the model's posterior probability that player $p$ has role $r$:

$$\text{MA}_q = \frac{1}{P} \sum_{p=1}^{P} a_{p, r_p^*}$$

This is the average probability the model assigns to the true role across all players in a single game round $q$.

### MAP (Maximum-A-Posteriori) Accuracy
Let $\hat{r}_p$ be the role assigned to player $p$ in the model's most likely complete assignment (MAP estimate):

$$\text{MAP}_q = \frac{1}{P} \sum_{p=1}^{P} \mathbf{1}[\hat{r}_p = r_p^*]$$

This is the fraction of players whose exact role is correctly recovered.

### Aggregation
Both metrics are first averaged over the $Q$ rounds of a single game, then averaged across all games $\mathcal{G}$ in the dataset. Results are reported as mean $\pm$ standard deviation.

## Baselines and Targets

The paper reports results on three datasets (Avalon-NLU, Mafia-UCB, AvalonLogs) with multiple role perspectives. Representative targets from the paper (Table 2, Truthful-Good condition, Avalon-NLU 6-player):

| Method | Setting | Obj (Marg/MAP) | Merlin (Marg/MAP) | Percival (Marg/MAP) | Assassin (Marg/MAP) | Morgana (Marg/MAP) | Servant (Marg/MAP) |
|--------|---------|---------------|------------------|--------------------|--------------------|--------------------|--------------------|
| CSP | Strict | 0.28/0.24 | 0.63/0.60 | 0.69/0.67 | 0.59/0.53 | 0.59/0.53 | 0.56/0.53 |
| CSP | +HypIG | 0.34/0.30 | 0.65/0.60 | 0.76/0.79 | 0.61/0.53 | 0.61/0.53 | 0.60/0.65 |
| LLM | GChat | 0.14/0.20 | 0.20/0.24 | 0.16/0.19 | 0.13/0.19 | 0.16/0.25 | 0.13/0.21 |
| LLM+CSP | Strict | 0.16/0.12 | 0.41/0.39 | 0.44/0.41 | 0.42/0.39 | 0.42/0.39 | 0.12/0.17 |

Random baseline: Objective = 0.267, Merlin = 0.4, Percival = 0.4, Assassin = 0.583, Servant = 0.333.

The key finding is that **pure CSP methods significantly outperform LLM-only approaches**, especially for special roles with hidden information.

## Evaluation Protocol

1. **Dataset split**: Games are split into Truthful-Good (no lying) and Lying-Good (at least one good player lies) conditions
2. **Perspectives**: Evaluated from multiple viewpoints — objective (no private info), and per-role perspectives (Merlin, Percival, Servant, Assassin, Morgana, etc.)
3. **CSP settings**: Five constraint configurations are tested:
   - Strict: hard constraints only (evidence + phenomenon)
   - +Assert: adds high-weight assertions
   - +HypIG: adds all hypotheses with information-gain auto-weights
   - +HypM: adds all hypotheses with manual weights
   - +TurnIG: adds current-turn hypotheses with IG weights
4. **LLM settings**: Global chat (all history) and turn-only chat
5. **LLM+CSP settings**: Same five CSP configurations used to augment LLM prompts

---

# Reproduction Log

### Iteration 1: MiniMax-M2.7
- **Milestone**: `method_runs` | **Status**: done
- **Working time**: 6.4h | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

### [2026-04-06] - method_runs
- Implemented the CSP4SDG solver based on the paper's code (method/sdg_framework.py, method/avalon_logs_solver.py)
- CSP solver runs end-to-end on AvalonLogs data without errors
- Data preprocessing (convert_avalonlogs.py) successfully converts raw game logs to CSP constraints
- Optimized solver processes 6-8 player games in ~1-10s per game (9-10 player games are slow due to combinatorial explosion)
- AvalonLogs dataset: 12,402 game files, converted to constraints
- Evaluation code computes marginal accuracy and MAP accuracy per game, aggregated across games

### [2026-04-06] - none
- Read the paper and identified key components: CSP framework, four constraint types, IG weighting
- Cloned CSP4SDG GitHub repo for reference implementation
- Downloaded AvalonLogs dataset (12,402 games) from GitHub

</details>


---

# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-06] - method_runs
- Implemented the CSP4SDG solver based on the paper's code (method/sdg_framework.py, method/avalon_logs_solver.py)
- CSP solver runs end-to-end on AvalonLogs data without errors
- Data preprocessing (convert_avalonlogs.py) successfully converts raw game logs to CSP constraints
- Optimized solver processes 6-8 player games in ~1-10s per game (9-10 player games are slow due to combinatorial explosion)
- AvalonLogs dataset: 12,402 game files, converted to constraints
- Evaluation code computes marginal accuracy and MAP accuracy per game, aggregated across games

### [2026-04-06] - none
- Read the paper and identified key components: CSP framework, four constraint types, IG weighting
- Cloned CSP4SDG GitHub repo for reference implementation
- Downloaded AvalonLogs dataset (12,402 games) from GitHub
