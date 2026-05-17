# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

## Stop Justification
- Completed at milestone `core_claim_plus`.
- Higher milestones would require Avalon-NLU/Mafia LLM constraint extraction and LLM baselines, which need external API access not available in this reproduction setting.
