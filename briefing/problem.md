# Problem Definition

## Research Question

In social deduction games such as Avalon, Mafia, and Werewolf, players have hidden roles and reveal information only indirectly through public actions, optional communication, and game outcomes. The central task is **role identification**: given the observed game history and the role composition for that game, infer the most likely role for each player.

The problem is difficult because:
- Observations are incomplete and noisy.
- Some players benefit from misleading others.
- Different roles have different private information.
- The number of possible full role assignments grows rapidly with player count.
- Public events and communication can support multiple conflicting explanations.

## Why It Matters

Accurate role identification is a prerequisite for strategic play in social deduction games. It is also a compact benchmark for hidden-state reasoning in multi-agent settings: a system must combine public evidence, asymmetric information, and uncertainty about other agents' motives.

## Task Definition

**Input** (one instance):
- Player list (seat labels) and the declared role composition of the game.
- The public history up to a completed quest: every team proposal, every
  player's approve/reject vote, each quest team and its number of fail cards.
- One viewpoint: either the objective observer (public information only) or a
  player whose role is given together with the private information that role
  receives under the Avalon rules (Merlin sees every evil player except Mordred;
  Percival sees Merlin and Morgana without knowing which is which; evil players
  other than Oberon see their evil teammates except Oberon; loyal followers see
  nothing).

**Output** (per instance):
- For every player, a probability distribution over the roles of the declared
  composition.
- One complete role assignment that respects the declared role counts.

## Success Criteria

A strong solution should:
1. Assign high probability to each player's true role.
2. Recover accurate full role assignments when uncertainty is low.
3. Remain calibrated when evidence is ambiguous.
4. Respect the declared role composition and viewpoint-specific information.
5. Generalize across player counts without changing the evaluation protocol.

## Difficulty

For Avalon-style role sets, the possible assignment space is small enough to define exactly but large enough to make naive reasoning weak:
- 6 players: 90 possible full assignments in the reproduced role schema.
- 8 players: roughly 2,800 assignments.
- 10 players: roughly 78,000 assignments.

The challenge is not just listing assignments. A method must decide how much each event, outcome, and viewpoint should shift probability mass toward or away from competing hidden-role explanations.
