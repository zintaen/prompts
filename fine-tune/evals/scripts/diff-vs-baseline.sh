#!/usr/bin/env bash
# diff-vs-baseline.sh — compare a single run's capture.json to baseline.json.
#
# Two layers of diff:
#   Layer 1 (cell-level):
#     verdict ∈ {OK, REGRESSION, IMPROVEMENT, NEW-CELL, VERSION-MISMATCH,
#                INDETERMINATE}
#   Layer 2 (rule-level):
#     for each rule in capture.rules_exercised ∪ baseline cell.rules_exercised,
#     report transitions:
#       pass → fail           = RULE-REGRESSION         (exits nonzero)
#       fail → pass           = RULE-FIX
#       not_exercised → pass  = RULE-COVERAGE-IMPROVED
#       pass → not_exercised  = RULE-COVERAGE-LOST
#       same                  = (silent, only shown with --verbose)
#
# Usage:
#   diff-vs-baseline.sh --run <run_id> [--verbose]
#
# Exit codes:
#   0   OK or IMPROVEMENT with no rule-level regressions
#   3   VERSION-MISMATCH (fingerprint differs)
#   4   REGRESSION (cell-level pass→fail OR any rule-level pass→fail)
#   5   INDETERMINATE (manual review needed)

set -euo pipefail

RUN_ID=""
VERBOSE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run)     RUN_ID="$2"; shift 2 ;;
    --verbose) VERBOSE=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$RUN_ID" ]] || { echo "Missing --run <run_id>" >&2; exit 2; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CAPTURE="$(find "$ROOT/runs" -type f -name capture.json -path "*${RUN_ID}*" | head -n1)"
[[ -n "$CAPTURE" ]] || { echo "No capture.json found for run_id $RUN_ID under $ROOT/runs" >&2; exit 2; }

BASELINE="$ROOT/baseline.json"
[[ -f "$BASELINE" ]] || { echo "No baseline.json at $BASELINE" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 2; }

FIXTURE=$(jq -r '.fixture_id'        "$CAPTURE")
MODEL=$(  jq -r '.model_id'          "$CAPTURE")
IDE=$(    jq -r '.ide_id'            "$CAPTURE")
RUN_FP=$( jq -r '.audit_md_version'  "$CAPTURE")
RUN_PASS=$(jq -r '.step_7_5_passed'  "$CAPTURE")

BASE_FP=$(jq -r '.audit_md_version'  "$BASELINE")

# ---- Layer 0: fingerprint gate ----
if [[ "$RUN_FP" != "$BASE_FP" ]]; then
  echo "VERSION-MISMATCH"
  echo "  run.audit_md_version:      $RUN_FP"
  echo "  baseline.audit_md_version: $BASE_FP"
  echo "  Runs against different AUDIT.md fingerprints cannot be compared."
  echo "  Either (a) re-run this run against the current AUDIT.md, or"
  echo "         (b) promote a new baseline via promote-baseline.sh."
  exit 3
fi

# ---- Layer 1: cell lookup ----
CELL=$(jq -c --arg f "$FIXTURE" --arg m "$MODEL" --arg i "$IDE" '
  .fixtures[$f].cells
  | to_entries[]
  | select(.value.model == $m and .value.ide == $i)
  | .value
' "$BASELINE" 2>/dev/null || true)

if [[ -z "$CELL" || "$CELL" == "null" ]]; then
  echo "NEW-CELL  fixture=$FIXTURE model=$MODEL ide=$IDE"
  echo "  No prior baseline for this cell. Not a regression."
  exit 0
fi

BASE_RESULT=$(echo "$CELL" | jq -r '.result')

case "$RUN_PASS" in
  true)  RUN_RESULT="pass" ;;
  false) RUN_RESULT="fail" ;;
  *)     RUN_RESULT="unknown" ;;
esac

CELL_VERDICT=""
CELL_EXIT=0
if [[ "$BASE_RESULT" == "pass" && "$RUN_RESULT" == "fail" ]]; then
  CELL_VERDICT="REGRESSION"
  CELL_EXIT=4
elif [[ "$BASE_RESULT" == "fail" && "$RUN_RESULT" == "pass" ]]; then
  CELL_VERDICT="IMPROVEMENT"
elif [[ "$BASE_RESULT" == "$RUN_RESULT" ]]; then
  CELL_VERDICT="OK"
else
  CELL_VERDICT="INDETERMINATE"
  CELL_EXIT=5
fi

echo "[cell]  $CELL_VERDICT  fixture=$FIXTURE model=$MODEL ide=$IDE  base=$BASE_RESULT run=$RUN_RESULT"

# ---- Layer 2: rule-level diff ----
RUN_RULES=$(jq -c '.rules_exercised // {}' "$CAPTURE")
BASE_RULES=$(echo "$CELL" | jq -c '.rules_exercised // {}')

# Build the union key set. Drop underscore-prefixed keys (metadata like
# _comment live alongside rule entries in baseline cells).
UNION_KEYS=$(jq -n --argjson a "$RUN_RULES" --argjson b "$BASE_RULES" '
  [($a | keys[]), ($b | keys[])]
  | map(select(startswith("_") | not))
  | unique | sort
')

RULE_REGRESSIONS=0
RULE_FIXES=0
RULE_COV_IMPROVED=0
RULE_COV_LOST=0

# Iterate each rule in the union; compare statuses.
while read -r rule; do
  [[ -z "$rule" ]] && continue
  base_v=$(echo "$BASE_RULES" | jq -r --arg k "$rule" '.[$k] // "not_exercised"')
  run_v=$( echo "$RUN_RULES"  | jq -r --arg k "$rule" '.[$k] // "not_exercised"')

  if [[ "$base_v" == "pass" && "$run_v" == "fail" ]]; then
    echo "[rule]  RULE-REGRESSION        $rule  (was pass, now fail)"
    RULE_REGRESSIONS=$((RULE_REGRESSIONS + 1))
  elif [[ "$base_v" == "fail" && "$run_v" == "pass" ]]; then
    echo "[rule]  RULE-FIX                $rule  (was fail, now pass)"
    RULE_FIXES=$((RULE_FIXES + 1))
  elif [[ "$base_v" == "not_exercised" && "$run_v" == "pass" ]]; then
    echo "[rule]  RULE-COVERAGE-IMPROVED  $rule  (now covered: pass)"
    RULE_COV_IMPROVED=$((RULE_COV_IMPROVED + 1))
  elif [[ "$base_v" == "pass" && "$run_v" == "not_exercised" ]]; then
    echo "[rule]  RULE-COVERAGE-LOST      $rule  (was pass, now not exercised)"
    RULE_COV_LOST=$((RULE_COV_LOST + 1))
  elif [[ "$base_v" == "$run_v" ]]; then
    if [[ "$VERBOSE" == "1" ]]; then
      echo "[rule]  RULE-STABLE             $rule  ($run_v)"
    fi
  else
    echo "[rule]  RULE-INDETERMINATE      $rule  base=$base_v run=$run_v"
  fi
done < <(echo "$UNION_KEYS" | jq -r '.[]')

echo ""
echo "[summary]  cell=$CELL_VERDICT"
echo "           rule_regressions=$RULE_REGRESSIONS  rule_fixes=$RULE_FIXES"
echo "           rule_coverage_improved=$RULE_COV_IMPROVED  rule_coverage_lost=$RULE_COV_LOST"

# ---- final exit ----
if [[ "$CELL_EXIT" -ne 0 ]]; then
  exit "$CELL_EXIT"
fi
if [[ "$RULE_REGRESSIONS" -gt 0 ]]; then
  echo ""
  echo "RULE-REGRESSION detected — cell looked fine but a specific rule flipped pass→fail."
  echo "This is the whole point of Layer-2: catch the 'passed overall, silently broke rule X' case."
  exit 4
fi
exit 0
