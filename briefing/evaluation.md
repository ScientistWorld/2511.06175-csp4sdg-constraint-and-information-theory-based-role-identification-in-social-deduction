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
