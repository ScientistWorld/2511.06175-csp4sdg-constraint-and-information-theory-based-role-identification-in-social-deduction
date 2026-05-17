# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-05-17 15:30] - core_claim_plus
- Completed continuation audit after the milestone reset and restored `core_claim_plus`.
- Confirmed the method implementation is the actual CSP4SDG algorithm, not a surrogate, and that evaluation reads solver artifacts independently from `method/`.
- Fixed evaluator reference lookup so `scripts/evaluate.sh` preserves the same reference-based output contract even when writing scores outside `scoring/`.
- Re-ran `scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

### [2026-05-17 15:13] - core_claim_plus
- Confirmed the implementation is the paper's actual CSP4SDG algorithm: hard-constraint pruning, multiplicative assertions, additive IG/manual hypotheses, posterior marginals, and MAP worlds.
- Validated the reusable AvalonLogs gym with `python3 validate.py --compare` and bytecode compilation for method, data conversion, and evaluation modules.
- Reproduced the core AvalonLogs claim across 5-, 6-, 7-, 8-, 9-, and partially solved 10-player settings. CSP_Strict is close to the paper on the accessible no-dialogue benchmark and clearly beats the paper's LLM_Global reference on informative role views.

## Stop Justification
- Completed at milestone `core_claim_plus`.
