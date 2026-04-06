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
