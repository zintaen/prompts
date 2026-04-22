#!/usr/bin/env bash
# flake-check.sh — detect non-determinism in fixture replays.
#
# In this rig, build.py scripts are hand-authored to be fully deterministic:
# run_ids, timestamps, and fingerprints are hard-coded; dict iteration order
# is stable on CPython 3.7+; all file paths are computed from fixed inputs.
# That means a given fixture's build.py should produce byte-identical output
# across replays. Any deviation is a RED FLAG indicating:
#   - dict/set iteration that the author assumed was stable but isn't
#   - a time-dependent branch that leaked in
#   - a randomness seed that wasn't pinned
#   - a future LLM-in-the-loop step that needs explicit tolerance budgeting
#
# Usage:
#   flake-check.sh [--fixtures F001,F003,...] [--n N] [--audit-md ../../../AUDIT.md]
#                  [--out ../runs/flake-report-<date>.json]
#                  [--tolerance-pct 0]
#                  [--verbose]
#
# What it does, per selected fixture:
#   1. Resolve the fixture's canonical run_dir (same logic as run-baseline.sh).
#   2. Skip if fixture.yaml type==resume (not replayable in isolation —
#      same policy as run-baseline.sh).
#   3. Loop N iterations (default 5). For each iteration:
#      a. Run build.py (cwd = run_dir) capturing stdout/stderr.
#      b. Compute a CANONICAL HASH of capture.json = sha256 of jq -S -c output
#         (sort keys, compact whitespace). This normalizes formatting noise
#         while still flipping on any real content change.
#      c. Record: iteration#, capture_hash, step_7_5_passed, hard, soft,
#                 rules_exercised (full map).
#   4. Aggregate:
#      - pass_rate = (# iters with step_7_5_passed==true) / N
#      - capture_stability_rate = (# iters whose hash == iter1.hash) / N
#      - rule_flakes = per-rule list of any rule whose status flipped between
#                      any two iterations
#      - hard_count_range / soft_count_range
#   5. Emit one row per fixture into the report.
#
# HARD RULE (mirrors ANALYZER.md's philosophy):
#   Do NOT weaken the stability bar to make a flaky fixture pass. If a
#   fixture is flaky, the fix is in build.py (or in the AUDIT.md clause it
#   exercises) — not in this harness.
#
# Output: a merge-candidate-style JSON at --out (default:
#   evals/runs/flake-report-<YYYY-MM-DD>.json). This script NEVER mutates
#   baseline.json — same design rationale as promote-baseline.sh. If you
#   want to record a flake-ledger snapshot in baseline.json, do it by hand
#   after reviewing the report.
#
# Exit codes:
#   0  every selected fixture met stability bar (pass_rate==1.0 AND
#      capture_stability_rate >= 1.0 - tolerance_pct/100)
#   2  arg / prerequisite error
#   6  flakiness detected in at least one fixture

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
EVALS="$(cd "$HERE/.." && pwd)"
AUDIT_MD="$EVALS/../../AUDIT.md"
DATE="$(date -u +%Y-%m-%d)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OUT="$EVALS/runs/flake-report-${DATE}.json"
N=5
ONLY=""
TOLERANCE_PCT=0
VERBOSE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --audit-md)      AUDIT_MD="$2"; shift 2 ;;
    --out)           OUT="$2"; shift 2 ;;
    --fixtures)      ONLY="$2"; shift 2 ;;
    --n)             N="$2"; shift 2 ;;
    --tolerance-pct) TOLERANCE_PCT="$2"; shift 2 ;;
    --verbose)       VERBOSE=1; shift ;;
    -h|--help)       sed -n '1,60p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$AUDIT_MD" ]] || { echo "AUDIT.md not found at $AUDIT_MD" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 2; }
command -v jq      >/dev/null || { echo "jq required" >&2; exit 2; }
command -v shasum  >/dev/null || { echo "shasum required" >&2; exit 2; }
[[ "$N" =~ ^[0-9]+$ && "$N" -ge 2 ]] || { echo "--n must be integer >=2" >&2; exit 2; }

FP="sha256:$(shasum -a 256 "$AUDIT_MD" | awk '{print $1}')"

echo "flake-check.sh"
echo "  AUDIT.md fingerprint: $FP"
echo "  Iterations per fixture: $N"
echo "  Tolerance: ${TOLERANCE_PCT}%"
echo "  Output report:        $OUT"
echo ""

# -- resolve fixture set (same pattern as run-baseline.sh) --
mapfile -t ALL_FIXTURES < <(ls -1 "$EVALS/fixtures" | grep -E '^F[0-9]{3}-')
if [[ -n "$ONLY" ]]; then
  IFS=',' read -ra WANTED <<< "$ONLY"
  FIXTURES=()
  for w in "${WANTED[@]}"; do
    for f in "${ALL_FIXTURES[@]}"; do
      if [[ "$f" == *"$w"* ]]; then FIXTURES+=("$f"); fi
    done
  done
else
  FIXTURES=("${ALL_FIXTURES[@]}")
fi

if [[ "${#FIXTURES[@]}" -eq 0 ]]; then
  echo "No fixtures selected." >&2
  exit 2
fi

# -- iterate --
FIXTURES_JSON="$(mktemp)"
echo '[]' > "$FIXTURES_JSON"
OVERALL_OK=1
FLAKES_TOTAL=0

for fx in "${FIXTURES[@]}"; do
  FX_TYPE="$(grep -E '^type:' "$EVALS/fixtures/$fx/fixture.yaml" 2>/dev/null | awk '{print $2}' || echo "")"

  if [[ "$FX_TYPE" == "resume" ]]; then
    echo "[$fx] SKIPPED (type=resume — cannot be replayed in isolation)"
    jq --arg f "$fx" '. += [{fixture:$f, skipped:"resume", iterations:[]}]' \
       "$FIXTURES_JSON" > "$FIXTURES_JSON.new"
    mv "$FIXTURES_JSON.new" "$FIXTURES_JSON"
    continue
  fi

  # Resolve canonical run dir for this fixture (same logic as run-baseline.sh).
  RUN_DIR="$(grep -rl "$fx" "$EVALS/runs" --include=build.py 2>/dev/null \
             | sort | tail -n1)"
  RUN_DIR="${RUN_DIR%/build.py}"

  if [[ -z "${RUN_DIR:-}" ]]; then
    echo "[$fx] NO-RUN-DIR — no build.py references this fixture"
    OVERALL_OK=0
    jq --arg f "$fx" '. += [{fixture:$f, error:"no-run-dir", iterations:[]}]' \
       "$FIXTURES_JSON" > "$FIXTURES_JSON.new"
    mv "$FIXTURES_JSON.new" "$FIXTURES_JSON"
    continue
  fi

  echo "[$fx] run_dir=$(realpath --relative-to="$EVALS" "$RUN_DIR")"

  ITERS_JSON="$(mktemp)"
  echo '[]' > "$ITERS_JSON"
  FIRST_HASH=""
  PASS_COUNT=0
  STABLE_COUNT=0
  HARD_MIN=9999; HARD_MAX=-1
  SOFT_MIN=9999; SOFT_MAX=-1
  # Collect rule_exercised maps so we can diff per-rule across iterations.
  RULES_PER_ITER="$(mktemp)"
  echo '[]' > "$RULES_PER_ITER"

  for ((i = 1; i <= N; i++)); do
    LOG="$(mktemp)"
    if (cd "$RUN_DIR" && python3 build.py >"$LOG" 2>&1); then
      BUILD_OK=1
    else
      BUILD_OK=0
      if [[ "$VERBOSE" == "1" ]]; then
        echo "       iter=$i BUILD_EXIT_NONZERO — first 20 lines of stderr:"
        sed -n '1,20p' "$LOG" | sed 's/^/         /'
      fi
    fi
    rm -f "$LOG"

    if [[ ! -f "$RUN_DIR/capture.json" ]]; then
      # capture.json didn't land — record as a failure iteration.
      jq --argjson i "$i" --arg err "no-capture" \
         '. += [{iter:$i, error:$err, capture_hash:null, step_7_5:null, hard:null, soft:null}]' \
         "$ITERS_JSON" > "$ITERS_JSON.new"
      mv "$ITERS_JSON.new" "$ITERS_JSON"
      jq '. += [{}]' "$RULES_PER_ITER" > "$RULES_PER_ITER.new"
      mv "$RULES_PER_ITER.new" "$RULES_PER_ITER"
      continue
    fi

    # Canonical hash: jq -S -c gives sorted-keys, compact JSON — so any
    # key-order or whitespace shuffle in capture.json doesn't create false flake.
    CAP_CANON="$(jq -S -c '.' "$RUN_DIR/capture.json")"
    CAP_HASH="$(printf '%s' "$CAP_CANON" | shasum -a 256 | awk '{print $1}')"

    STEP=$(jq -r '.step_7_5_passed'      "$RUN_DIR/capture.json")
    HARD=$(jq -r '.hard_violation_count' "$RUN_DIR/capture.json")
    SOFT=$(jq -r '.soft_violation_count' "$RUN_DIR/capture.json")
    RULES=$(jq -c '.rules_exercised // {}' "$RUN_DIR/capture.json")

    if [[ -z "$FIRST_HASH" ]]; then FIRST_HASH="$CAP_HASH"; fi
    if [[ "$STEP" == "true" ]];    then PASS_COUNT=$((PASS_COUNT + 1)); fi
    if [[ "$CAP_HASH" == "$FIRST_HASH" ]]; then STABLE_COUNT=$((STABLE_COUNT + 1)); fi

    # Track hard/soft range across iterations (ints or "null").
    if [[ "$HARD" != "null" ]]; then
      (( HARD < HARD_MIN )) && HARD_MIN=$HARD || true
      (( HARD > HARD_MAX )) && HARD_MAX=$HARD || true
    fi
    if [[ "$SOFT" != "null" ]]; then
      (( SOFT < SOFT_MIN )) && SOFT_MIN=$SOFT || true
      (( SOFT > SOFT_MAX )) && SOFT_MAX=$SOFT || true
    fi

    jq --argjson i "$i" --arg h "$CAP_HASH" \
       --argjson step "$STEP" --argjson hard "$HARD" --argjson soft "$SOFT" \
       --argjson bok "$BUILD_OK" \
       '. += [{iter:$i, capture_hash:$h, step_7_5:$step, hard:$hard, soft:$soft, build_exited_ok:($bok==1)}]' \
       "$ITERS_JSON" > "$ITERS_JSON.new"
    mv "$ITERS_JSON.new" "$ITERS_JSON"
    jq --argjson r "$RULES" '. += [$r]' \
       "$RULES_PER_ITER" > "$RULES_PER_ITER.new"
    mv "$RULES_PER_ITER.new" "$RULES_PER_ITER"
  done

  # --- compute per-rule flake list across the N iterations ---
  # For each rule present in any iteration's map, check whether its status
  # (pass | fail | not_exercised) differs between iterations. If yes → flake.
  RULE_FLAKES=$(jq -c '
    . as $iters
    | ([ .[] | keys[] ] | unique | map(select(startswith("_") | not)))
    | map(. as $rule
          | {rule: $rule,
             statuses: ([$iters[] | (.[$rule] // "not_exercised")] | unique)})
    | map(select(.statuses | length > 1))
  ' "$RULES_PER_ITER")

  RULE_FLAKE_COUNT=$(echo "$RULE_FLAKES" | jq 'length')
  FLAKES_TOTAL=$((FLAKES_TOTAL + RULE_FLAKE_COUNT))

  PASS_RATE=$(python3 -c "print(f'{$PASS_COUNT / $N:.4f}')")
  STAB_RATE=$(python3 -c "print(f'{$STABLE_COUNT / $N:.4f}')")
  STAB_BAR=$(python3 -c "print(f'{1.0 - $TOLERANCE_PCT / 100:.4f}')")

  FIXTURE_OK=1
  if [[ "$PASS_COUNT" -ne "$N" ]]; then FIXTURE_OK=0; fi
  if (( $(python3 -c "print(int($STAB_RATE < $STAB_BAR))") )); then FIXTURE_OK=0; fi
  if [[ "$RULE_FLAKE_COUNT" -gt 0 ]]; then FIXTURE_OK=0; fi

  if [[ "$HARD_MIN" == "9999" ]]; then HARD_MIN="null"; HARD_MAX="null"; fi
  if [[ "$SOFT_MIN" == "9999" ]]; then SOFT_MIN="null"; SOFT_MAX="null"; fi

  if [[ "$FIXTURE_OK" == "1" ]]; then
    echo "       pass_rate=${PASS_RATE}  stability=${STAB_RATE}  rule_flakes=${RULE_FLAKE_COUNT}  → OK"
  else
    echo "       pass_rate=${PASS_RATE}  stability=${STAB_RATE}  rule_flakes=${RULE_FLAKE_COUNT}  → FLAKE"
    OVERALL_OK=0
    if [[ "$RULE_FLAKE_COUNT" -gt 0 ]]; then
      echo "$RULE_FLAKES" | jq -r '.[] | "         rule=\(.rule)  observed_statuses=\(.statuses | tostring)"'
    fi
  fi

  jq -n \
     --arg fx "$fx" \
     --arg rd "$(realpath --relative-to="$EVALS" "$RUN_DIR")" \
     --arg fp "$FP" \
     --argjson n "$N" \
     --argjson pass_count "$PASS_COUNT" \
     --arg pass_rate "$PASS_RATE" \
     --argjson stable_count "$STABLE_COUNT" \
     --arg stability "$STAB_RATE" \
     --arg tolerance "$TOLERANCE_PCT" \
     --argjson hard_min "$HARD_MIN" --argjson hard_max "$HARD_MAX" \
     --argjson soft_min "$SOFT_MIN" --argjson soft_max "$SOFT_MAX" \
     --slurpfile iters "$ITERS_JSON" \
     --argjson rule_flakes "$RULE_FLAKES" \
     --argjson ok "$FIXTURE_OK" '
     {
       fixture: $fx,
       run_dir: $rd,
       audit_md_version: $fp,
       iterations_requested: $n,
       pass_count: $pass_count,
       pass_rate: ($pass_rate | tonumber),
       stability_count: $stable_count,
       capture_stability_rate: ($stability | tonumber),
       tolerance_pct: ($tolerance | tonumber),
       hard_violation_range: [$hard_min, $hard_max],
       soft_violation_range: [$soft_min, $soft_max],
       rule_flakes: $rule_flakes,
       iterations: $iters[0],
       verdict: (if $ok == 1 then "stable" else "flake" end)
     }' > "$ITERS_JSON.row"

  jq --slurpfile row "$ITERS_JSON.row" '. += $row' \
     "$FIXTURES_JSON" > "$FIXTURES_JSON.new"
  mv "$FIXTURES_JSON.new" "$FIXTURES_JSON"

  rm -f "$ITERS_JSON" "$ITERS_JSON.row" "$RULES_PER_ITER"
done

# --- emit report ---
mkdir -p "$(dirname "$OUT")"
jq -n \
  --arg ts "$TS" \
  --arg fp "$FP" \
  --argjson n "$N" \
  --arg tolerance "$TOLERANCE_PCT" \
  --slurpfile rows "$FIXTURES_JSON" '
  {
    kind: "flake-report",
    generated_at: $ts,
    audit_md_version: $fp,
    iterations_per_fixture: $n,
    tolerance_pct: ($tolerance | tonumber),
    fixtures: $rows[0],
    rationale: "Every build.py in this rig is hand-authored to be deterministic. A stability_rate < 1.0 or a rule_flakes entry means the fixture is leaking non-determinism — fix build.py (or the AUDIT.md clause it exercises), do not weaken this bar.",
    next_steps: [
      "If all verdicts are stable, no action.",
      "If a verdict is flake, diff capture.json or .audit/ outputs between two iterations that produced different hashes to locate the non-deterministic code path.",
      "Record a deliberate flake ledger entry in baseline.json under a new top-level flake_ledger key only after root-causing. Never auto-merge this report into baseline.json."
    ]
  }' > "$OUT"
rm -f "$FIXTURES_JSON"

echo ""
echo "Wrote report: $OUT"
echo "  rule_flakes_total=$FLAKES_TOTAL"

if [[ "$OVERALL_OK" == "1" ]]; then
  echo "flake-check: ALL STABLE."
  exit 0
fi
echo "flake-check: FLAKINESS DETECTED — see report and log above."
exit 6
