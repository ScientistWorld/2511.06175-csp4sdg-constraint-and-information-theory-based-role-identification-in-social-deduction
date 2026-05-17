# Evaluation

## Metrics

Two accuracy metrics evaluate role identification quality:

### Marginal Accuracy (MA)
For a game with *P* players, let *r_p* be player *p*'s true role and *a_{p,r}* be the posterior probability that player *p* has role *r*:

$$\text{MA}_q = \frac{1}{P} \sum_{p=1}^{P} a_{p, r_p^*}$$

This is the average probability assigned to the true role across all players in a single round *q*.

### MAP (Maximum-A-Posteriori) Accuracy
Let $\hat{r}_p$ be the role assigned in the single most likely complete assignment:

$$\text{MAP}_q = \frac{1}{P} \sum_{p=1}^{P} \mathbf{1}[\hat{r}_p = r_p^*]$$

This is the fraction of players whose exact role is correctly recovered.

### Aggregation
Both metrics are averaged over the *Q* rounds of a game, then over all games in the dataset.

## Baselines and Targets

**Random baseline** (uniform prior):
- Objective ≈ 0.267, Merlin = 0.4, Percival = 0.4, Assassin = 0.583, Servant = 0.333

**LLM baseline** (for papers with dialogue): Large language model prompted with game history. Generally performs near random for special roles.

**Target performance** (from AvalonLogs 6-player, Table 3):
- CSP-Strict: Obj=0.290, Merlin=0.614, Percival=0.635, EvilMinion=0.691
- CSP+HypIG: Obj=0.326, Merlin=0.615, Percival=0.637, EvilMinion=0.729
- LLM-Global: Obj=0.283, Merlin=0.360, Percival=0.325, EvilMinion=0.464

The core claim: constraint-based probabilistic reasoning significantly outperforms LLM-based approaches for role identification.

## Evaluation Protocol

### Dataset
**AvalonLogs**: 12,699 Avalon games (5-10 players) with team proposals, votes, quest outcomes, and ground-truth roles. No dialogue.

### Perspectives
Results reported separately for each viewpoint:
- **Objective**: Public information only
- **Merlin**: Knows which players are evil
- **Percival**: Sees Merlin/Morgana candidates
- **Morgana**: Knows fellow evils
- **Servant**: No special knowledge
- **Evil roles**: Know their teammates

### Game Size
AvalonLogs results are reported separately for 5-, 6-, 7-, 8-, 9-, and 10-player games. Exact enumeration becomes expensive for 10-player games, so partial 10-player coverage is acceptable if it is clearly reported.

### Statistical Validation
Improvements over baselines should use paired tests (Wilcoxon, paired t-test) across games with p < 0.05.
