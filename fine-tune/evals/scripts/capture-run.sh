#!/usr/bin/env bash
# capture-run.sh — wrap a manual AUDIT.md scan and produce a capture.json
#
# Usage:
#   capture-run.sh \
#     --fixture F001-fresh-repo-small \
#     --model claude-sonnet-4.5 \
#     --ide cursor-0.43 \
#     --audit-md ../../../AUDIT.md \
#     --audit-out /tmp/scan-out/.audit \
#     [--run-summary /tmp/scan-out/run_summary.json] \
#     [--notes "some free-form notes"]
#
# This script does NOT invoke the model. The human invokes the model
# inside their IDE, pointing it at the fixture repo and feeding it
# AUDIT.md. When the model is done, the .audit/ output directory is
# passed here via --audit-out. This script then:
#   1. Fingerprints AUDIT.md.
#   2. Copies the .audit/ output into evals/runs/YYYY-MM-DD/<run_id>/.
#   3. Derives capture.json from:
#        (a) --run-summary, if supplied (preferred — build.py-emitted runs)
#        (b) parsing .audit/changelog/transitions.jsonl for violations
#        (c) parsing .audit/reports/YYYY/MM/YYYY-MM-DD.md "Step 7.5" footer
#   4. Prints the run_id so the caller can reference it.
#   5. Warns if AUDIT.md fingerprint differs from baseline.json.

set -euo pipefail

# ------- arg parse (minimal, no flag libs) -------
FIXTURE=""; MODEL=""; IDE=""; AUDIT_MD=""; AUDIT_OUT=""; NOTES=""; RUN_SUMMARY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fixture)       FIXTURE="$2"; shift 2 ;;
    --model)         MODEL="$2"; shift 2 ;;
    --ide)           IDE="$2"; shift 2 ;;
    --audit-md)      AUDIT_MD="$2"; shift 2 ;;
    --audit-out)     AUDIT_OUT="$2"; shift 2 ;;
    --run-summary)   RUN_SUMMARY="$2"; shift 2 ;;
    --notes)         NOTES="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

for v in FIXTURE MODEL IDE AUDIT_MD AUDIT_OUT; do
  if [[ -z "${!v}" ]]; then echo "Missing --${v,,}" >&2; exit 2; fi
done
[[ -f "$AUDIT_MD" ]]    || { echo "AUDIT.md not found at $AUDIT_MD" >&2; exit 2; }
[[ -d "$AUDIT_OUT" ]]   || { echo ".audit/ output not found at $AUDIT_OUT" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 2; }

# ------- fingerprint -------
FP="sha256:$(shasum -a 256 "$AUDIT_MD" | awk '{print $1}')"

# ------- run_id + run dir -------
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATE="$(date -u +%Y-%m-%d)"
SUFFIX="$(head -c6 /dev/urandom | base64 | tr -dc a-z0-9 | head -c4)"
RUN_ID="ft-${TS}-${SUFFIX}"
RUN_DIR="$(dirname "$0")/../runs/${DATE}/${RUN_ID}"
mkdir -p "$RUN_DIR/.audit"

# ------- copy .audit/ and run_summary.json (if supplied) -------
cp -R "$AUDIT_OUT"/. "$RUN_DIR/.audit/"
if [[ -n "$RUN_SUMMARY" && -f "$RUN_SUMMARY" ]]; then
  cp "$RUN_SUMMARY" "$RUN_DIR/run_summary.json"
fi

# ------- derive step_7_5_passed + violations[] -------
STEP_7_5_PASSED="unknown"
VIOLATIONS="[]"
HARD_COUNT=0
SOFT_COUNT=0
RULES_EXERCISED="{}"

if [[ -f "$RUN_DIR/run_summary.json" ]]; then
  # Source 1: run_summary.json (preferred)
  HARD_COUNT=$(jq '.hard_violations | length' "$RUN_DIR/run_summary.json")
  SOFT_COUNT=$(jq '.soft_violations | length' "$RUN_DIR/run_summary.json")
  if [[ "$HARD_COUNT" == "0" ]]; then
    STEP_7_5_PASSED="true"
  else
    STEP_7_5_PASSED="false"
  fi
  # Flatten hard+soft into a single violations[] with severity tag.
  VIOLATIONS=$(jq '
    ([ .hard_violations[] | . + {severity:"hard"} ] +
     [ .soft_violations[] | . + {severity:"soft"} ])
    // []' "$RUN_DIR/run_summary.json")
  # Carry rules_exercised through if the run_summary supplies it.
  if jq -e '.rules_exercised' "$RUN_DIR/run_summary.json" >/dev/null 2>&1; then
    RULES_EXERCISED=$(jq '.rules_exercised' "$RUN_DIR/run_summary.json")
  fi
else
  # Source 2: transitions.jsonl — collect any violation-type transition events.
  TRANS="$RUN_DIR/.audit/changelog/transitions.jsonl"
  if [[ -f "$TRANS" ]]; then
    VIOLATIONS=$(jq -s '
      [ .[] | select(.type == "violation") |
        { check: .check,
          severity: (.severity // "unknown"),
          rule:     (.rule // null),
          evidence: (.evidence // null) } ]
    ' "$TRANS" 2>/dev/null || echo "[]")
    HARD_COUNT=$(echo "$VIOLATIONS" | jq '[.[] | select(.severity=="hard")] | length')
    SOFT_COUNT=$(echo "$VIOLATIONS" | jq '[.[] | select(.severity=="soft")] | length')
    if [[ "$HARD_COUNT" == "0" ]]; then
      STEP_7_5_PASSED="true"
    else
      STEP_7_5_PASSED="false"
    fi
  fi
  # Source 3 fallback: grep the daily .md for a "Step 7.5 conformance: PASS|FAIL" banner.
  DAILY_MD="$RUN_DIR/.audit/reports/$(date -u +%Y)/$(date -u +%m)/${DATE}.md"
  if [[ "$STEP_7_5_PASSED" == "unknown" && -f "$DAILY_MD" ]]; then
    if grep -qE '^Step 7\.5 conformance:\s+PASS' "$DAILY_MD"; then
      STEP_7_5_PASSED="true"
    elif grep -qE '^Step 7\.5 conformance:\s+FAIL' "$DAILY_MD"; then
      STEP_7_5_PASSED="false"
    fi
  fi
fi

# ------- write capture.json -------
NOTES_JSON=$(printf '%s' "$NOTES" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')

jq -n \
  --arg run_id     "$RUN_ID" \
  --arg ts         "$TS" \
  --arg fp         "$FP" \
  --arg model      "$MODEL" \
  --arg ide        "$IDE" \
  --arg fixture    "$FIXTURE" \
  --arg date       "$DATE" \
  --argjson step   "$STEP_7_5_PASSED" \
  --argjson hard   "$HARD_COUNT" \
  --argjson soft   "$SOFT_COUNT" \
  --argjson viol   "$VIOLATIONS" \
  --argjson rules  "$RULES_EXERCISED" \
  --argjson notes  "$NOTES_JSON" '
  {
    run_id:            $run_id,
    timestamp:         $ts,
    audit_md_version:  $fp,
    model_id:          $model,
    ide_id:            $ide,
    fixture_id:        $fixture,
    step_7_5_passed:   $step,
    hard_violation_count: $hard,
    soft_violation_count: $soft,
    violations:        $viol,
    rules_exercised:   $rules,
    artifacts: {
      state_index: ".audit/state/index.json",
      daily_md:    (".audit/reports/" + ($date | split("-")[0]) + "/" + ($date | split("-")[1]) + "/" + $date + ".md"),
      daily_json:  (".audit/reports/" + ($date | split("-")[0]) + "/" + ($date | split("-")[1]) + "/" + $date + ".json"),
      transitions: ".audit/changelog/transitions.jsonl"
    },
    notes: $notes
  }
' > "$RUN_DIR/capture.json"

# ------- baseline fingerprint warning -------
BASELINE="$(dirname "$0")/../baseline.json"
if [[ -f "$BASELINE" ]]; then
  BASE_FP=$(jq -r '.audit_md_version' "$BASELINE")
  if [[ "$FP" != "$BASE_FP" ]]; then
    echo "WARNING: AUDIT.md fingerprint does not match baseline.json." >&2
    echo "  run:      $FP" >&2
    echo "  baseline: $BASE_FP" >&2
    echo "  diff-vs-baseline.sh will exit VERSION-MISMATCH." >&2
  fi
fi

# ------- append to runs index (append-only; R-anti-drift-history-append-only) -------
INDEX="$(dirname "$0")/../runs/index.jsonl"
mkdir -p "$(dirname "$INDEX")"
jq -c --arg rid "$RUN_ID" --arg ts "$TS" --arg fx "$FIXTURE" \
      --arg m "$MODEL"  --arg i "$IDE"  --arg fp "$FP" \
      --argjson step "$STEP_7_5_PASSED" --argjson hard "$HARD_COUNT" \
  -n '{run_id:$rid, timestamp:$ts, fixture_id:$fx, model_id:$m, ide_id:$i,
       audit_md_version:$fp, step_7_5_passed:$step, hard_violation_count:$hard}' \
  >> "$INDEX"

echo "$RUN_ID"
echo "Wrote: $RUN_DIR/capture.json" >&2
echo "       step_7_5_passed=$STEP_7_5_PASSED hard=$HARD_COUNT soft=$SOFT_COUNT" >&2
