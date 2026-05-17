# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-05-17 15:08] - core_claim_plus
- Audited the existing CSP4SDG implementation and confirmed it implements exact role-assignment enumeration, hard filtering, assertion scoring, hypothesis scoring, IG weighting, posterior marginals, and MAP decoding.
- Verified `scripts/evaluate.sh` works standalone by regenerating an audit scores file from existing method outputs.
- Fixed the container definition so Python package installation remains confined to `environment/setup.sh`; no runtime dependencies changed.

### [2026-05-17 15:03] - core_claim_plus
- Packaged the upstream CSP4SDG code release and a reusable AvalonLogs reproduction environment.
- Verified `python3 validate.py --compare` passes.
- Reproduced the core CSP role-inference claim on AvalonLogs across 5-10 player settings using the paper's exact hard-filtering, soft assertion, hypothesis weighting, posterior marginal, and MAP computation.

## Stop Justification
- Completed at milestone `core_claim_plus`.
