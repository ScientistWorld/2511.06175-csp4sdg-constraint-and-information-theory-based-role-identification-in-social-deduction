#!/bin/bash
# Iteration-11 hardening audit. Runs every variant/shortcut through the
# unchanged train/test evaluators (only the predictor command is swapped),
# checks the grouped solver against literal enumeration, measures seed
# sensitivity, then analyses everything into redteam/iter11/summary.{json,md}.
# Resumable: finished steps are skipped.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
A=redteam/iter11
V="python3 $A/variants.py"
mkdir -p $A/runs

run_test() {  # name, predictor command, [extra env assignments via env]
    local name="$1"; shift
    local cmd="$1"; shift
    if [ -s "$A/runs/$name/scores_test.json" ]; then echo "skip $name"; return; fi
    mkdir -p "$A/runs/$name"
    echo "=== test: $name ($(date +%T))"
    python3 eval/test/evaluate.py --predict-cmd "$cmd" --output "$A/runs/$name/scores_test.json.tmp" \
        --per-instance "$A/runs/$name/per_instance.json" > "$A/runs/$name/test.log" 2>&1 || echo "evaluator rc=$?"
    mv "$A/runs/$name/scores_test.json.tmp" "$A/runs/$name/scores_test.json"
    tail -4 "$A/runs/$name/test.log"
}

run_train() {
    local name="$1"; shift
    local cmd="$1"; shift
    if [ -s "$A/runs/$name/scores_train.json" ]; then echo "skip train $name"; return; fi
    mkdir -p "$A/runs/$name"
    echo "=== train: $name ($(date +%T))"
    python3 eval/train/evaluate.py --predict-cmd "$cmd" --output "$A/runs/$name/scores_train.json.tmp" \
        --per-instance "$A/runs/$name/per_instance_train.json" > "$A/runs/$name/train.log" 2>&1 || echo "evaluator rc=$?"
    mv "$A/runs/$name/scores_train.json.tmp" "$A/runs/$name/scores_train.json"
    tail -3 "$A/runs/$name/train.log"
}

# 1. Reference, its seeds, and the train side.
run_test reference "bash scripts/predict.sh"
run_train reference "bash scripts/predict.sh"
for s in 1 2 3; do
    CSP4SDG_SEED=$s run_test "reference_seed$s" "bash scripts/predict.sh"
done

# 2. Literal-enumeration check of the grouped solver on train instances.
if [ ! -s $A/enumeration_check.json ]; then
    python3 eval/train/evaluate.py --limit-per-size 60 --predict-cmd "python3 baseline/prior.py" \
        --output /tmp/iter11_dummy.json --dump-instances /tmp/iter11_train_instances.json > /dev/null
    python3 $A/check_enumeration.py /tmp/iter11_train_instances.json $A/enumeration_check.json
fi

# 3. Learned-likelihood variant: choose the temperature on the train slice only.
for t in 0.3 0.5 0.7 1.0; do
    LEARNED_TEMP=$t run_train "learned_votes_t$t" "$V learned_votes"
done
TAU=$(python3 $A/analyze.py pick-tau)
echo "chosen LEARNED_TEMP=$TAU (train slice)"
echo "$TAU" > $A/chosen_tau.txt

# 4. Honest variants through the hidden test.
run_test better_knowledge "$V better_knowledge"
LEARNED_TEMP=$TAU run_test learned_votes "$V learned_votes"
LEARNED_TEMP=$TAU run_test combined "$V combined"
LEARNED_TEMP=$TAU run_train combined "$V combined"
run_train better_knowledge "$V better_knowledge"
run_test prior "python3 baseline/prior.py"
run_test strict_only "$V strict_only"

# 5. Shortcuts through the hidden test.
for s in sharpen_onehot sharpen_power constant_ones impossible empty malformed pool empty_map crash \
         arbitrary_world lookup_visible rename read_heldout; do
    run_test "$s" "$V $s"
done
# Mild post-hoc recalibration of the reference posterior (closed-form probes).
POWER=1.25 run_test power_1.25 "$V sharpen_power"
POWER=0.8 run_test power_0.8 "$V sharpen_power"

# 6. Writable-whitelist and score-forgery shortcuts (use the default output path).
if [ ! -s $A/runs/filter/scores_test.json ]; then
    mkdir -p $A/runs/filter
    cp scoring/scores.json /tmp/iter11_scores_backup.json 2>/dev/null || true
    echo '{"experiments": {"avalonlogs_6player": {"results": {"NoSuchMethod": {"Obj_brier": 0.0}}}}}' > scoring/scores.json
    bash scripts/evaluate_test.sh > $A/runs/filter/test.log 2>&1
    cp scoring/scores_test.json $A/runs/filter/scores_test.json
    cp /tmp/iter11_scores_backup.json scoring/scores.json 2>/dev/null || rm -f scoring/scores.json
fi
if [ ! -s $A/runs/forge_scores/scores_test.json ]; then
    mkdir -p $A/runs/forge_scores
    bash scripts/evaluate_test.sh --predict-cmd "$V forge_scores" > $A/runs/forge_scores/test.log 2>&1
    cp scoring/scores_test.json $A/runs/forge_scores/scores_test.json
fi

# 7. Analysis.
python3 $A/analyze.py summarize
