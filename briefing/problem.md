# Problem Definition

## Research Question

In Social Deduction Games (SDGs) like Avalon, Mafia, and Werewolf, players are secretly assigned roles and must deduce each other's hidden identities through game events (votes, quests, eliminations) and dialogue. The core challenge is **role identification**: given partial, noisy, and often deceptive information, what is the most likely role assignment for each player?

The problem is hard because:
- Information is incomplete and distributed across players
- Players deliberately deceive each other
- The combinatorial space of possible role assignments grows factorially with player count (90 worlds for 6 players, ~78,000 for 10 players)
- Some roles have special knowledge (e.g., Merlin knows who is evil) that provides asymmetric information
- Dialogue contains both honest claims and strategic lies

## Why It Matters

Accurate role identification is the foundation of decision-making in SDGs — for both human players and AI agents. If an agent cannot correctly infer who is on its team, it cannot coordinate effectively or deceive opponents. This problem also generalizes to any multi-agent setting where agents must reason about hidden state from public observations and communication.

## Success Criteria

A successful role identification system should:
1. **Maximise marginal accuracy**: assign high probability to the true role of each player (1/P for random)
2. **Maximise MAP (maximum-a-posteriori) accuracy**: correctly recover the exact full role assignment
3. **Be interpretable**: provide calibrated probabilities and explain why certain roles are likely
4. **Be game-agnostic**: work across different social deduction games without per-game tuning
5. **Be training-free**: not require learning from game data (the combinatorial structure is known from game rules)

## Task Definition

**Input**: Game history consisting of:
- Player list and known role composition (e.g., "6 players: 3 good, 2 evil, 1 special")
- Public events: team proposals, votes, quest outcomes, night eliminations
- Private dialogue (optional, not always available)
- Role perspective (optional): the viewpoint from which reasoning is performed

**Output**: For each player, a probability distribution over possible roles, plus a MAP assignment.

## Difficulty

- 6 players: 90 possible role assignments (choose 3 good from 6, then assign special roles)
- 8 players: ~2,800 assignments
- 10 players: ~78,000 assignments

The challenge is not just enumeration but also appropriately weighting different evidence sources — votes may indicate suspicion but a player could be lying; quest failures indicate evil presence but don't identify who.
