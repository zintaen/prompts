#!/usr/bin/env bash
# promote-baseline.sh — after a green batch of runs against a new AUDIT.md
# fingerprint, produce a baseline MERGE CANDIDATE for human review.
#
# Design decision: this script intentionally does NOT overwrite baseline.json.
# baseline.json is the authoritative three-file contract partner to AUDIT.md
# and rule-registry.json, and many cells carry hand-authored `_comment` prose
# that describes *why* a cell passes (the load-bearing invariants, the fault
# mutations, the evidence trail). Machine-merging would quietly discard that
# prose, which is exactly the kind of silent regression this whole rig is
# meant to prevent.
#
# Instead we emit evals/runs/baseline-merge-candidate-<TS>.json containing:
#   - header: old_fingerprint, new_fingerprint, promoted_at, delta_summary,
#             proposed_edits_file
#   - upserts[]: one entry per capture.json under --runs-dir, fully resolved:
#                { fixture, cell_key, cell: {...}, was_present, prior_cell }
#   - history_entry: the JSON object to append to baseline.history[]
#
# The reviewer then merges by hand (or via `jq` with eyes open), preserving
# the `_comment` fields they care about.
#
# Usage:
#   promote-baseline.sh --audit-md ../../../AUDIT.md \
#                       --runs-dir ../runs/YYYY-MM-DD \
#                       [--delta-summary "what changed"] \
#                       [--proposed-edits ../PROPOSED-EDITS-YYYY-MM-DD.md] \
#                       [--out ../runs/baseline-merge-candidate-<TS>.json]
#
# Exit codes:
#   0  candidate written
#   1  fingerprint unchanged (nothing to promote)
#   2  arg or prerequisite error

set -euo pipefail

AUDIT_MD=""
RUNS_DIR=""
DELTA=""
PE_FILE=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --audit-md)        AUDIT_MD="$2"; shift 2 ;;
    --runs-dir)        RUNS_DIR="$2"; shift 2 ;;
    --delta-summary)   DELTA="$2"; shift 2 ;;
    --proposed-edits)  PE_FILE="$2"; shift 2 ;;
    --out)             OUT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$AUDIT_MD" ]]   || { echo "--audit-md file not found" >&2; exit 2; }
[[ -d "$RUNS_DIR" ]]   || { echo "--runs-dir not found" >&2; exit 2; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASELINE="$ROOT/baseline.json"
[[ -f "$BASELINE" ]]   || { echo "baseline.json missing at $BASELINE" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq required" >&2; exit 2; }

NEW_FP="sha256:$(shasum -a 256 "$AUDIT_MD" | awk '{print $1}')"
OLD_FP=$(jq -r '.audit_md_version' "$BASELINE")

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SHORT_TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
if [[ -z "$OUT" ]]; then
  OUT="$ROOT/runs/baseline-merge-candidate-${SHORT_TS}.json"
fi
mkdir -p "$(dirname "$OUT")"

if [[ "$NEW_FP" == "$OLD_FP" ]]; then
  echo "AUDIT.md fingerprint unchanged. Nothing to promote." >&2
  echo "  $NEW_FP" >&2
  echo "" >&2
  echo "If you intend to refresh cells in place (same fingerprint), this is" >&2
  echo "not the script for that — that would break the invariant that" >&2
  echo "baseline.json cells are keyed by (fixture, model, ide, audit_md_fp)." >&2
  echo "Instead, author a new fingerprint (edit AUDIT.md) or refresh cells" >&2
  echo "by editing baseline.json directly with a clear reason." >&2
  exit 1
fi

# ---- build per-capture upsert entries ----
UPSERTS_FILE="$(mktemp)"
echo '[]' > "$UPSERTS_FILE"

SHOPT_WAS="$(shopt -p globstar || true)"
shopt -s globstar
CAPS=()
while IFS= read -r -d '' f; do
  CAPS+=("$f")
done < <(find "$RUNS_DIR" -type f -name capture.json -print0)
eval "$SHOPT_WAS"

if [[ "${#CAPS[@]}" -eq 0 ]]; then
  echo "No capture.json files found under $RUNS_DIR." >&2
  exit 2
fi

for cap in "${CAPS[@]}"; do
  fixture=$(jq -r '.fixture_id'        "$cap")
  model=$(  jq -r '.model_id'          "$cap")
  ide=$(    jq -r '.ide_id'            "$cap")
  run_id=$( jq -r '.run_id'            "$cap")
  cap_fp=$( jq -r '.audit_md_version'  "$cap")

  # Skip captures that don't match the new fingerprint — they can't be
  # promoted under this fingerprint without lying.
  if [[ "$cap_fp" != "$NEW_FP" ]]; then
    echo "  skip: $run_id — fingerprint $cap_fp (want $NEW_FP)" >&2
    continue
  fi

  pass=$(jq -r '.step_7_5_passed'         "$cap")
  case "$pass" in
    true)  result="pass" ;;
    false) result="fail" ;;
    *)     result="unknown" ;;
  esac
  hard=$(jq '.hard_violation_count // 0' "$cap")
  soft=$(jq '.soft_violation_count // 0' "$cap")
  rules=$(jq -c '.rules_exercised // {}' "$cap")
  cell_key="${model}|${ide}|${NEW_FP}"

  # Look up any prior cell under the old fingerprint — preserves _comment.
  prior_cell=$(jq -c --arg f "$fixture" --arg m "$model" --arg i "$ide" '
    .fixtures[$f].cells
    | to_entries[]?
    | select(.value.model == $m and .value.ide == $i)
    | .value
  ' "$BASELINE" | head -n1 || true)
  if [[ -z "$prior_cell" ]]; then
    was_present="false"
    prior_cell="null"
  else
    was_present="true"
  fi

  jq --arg fx "$fixture" \
     --arg key "$cell_key" \
     --arg model "$model" \
     --arg ide "$ide" \
     --arg fp "$NEW_FP" \
     --arg rid "$run_id" \
     --arg result "$result" \
     --arg ts "$TS" \
     --argjson hard "$hard" --argjson soft "$soft" \
     --argjson rules "$rules" \
     --arg was_present "$was_present" \
     --argjson prior "$prior_cell" '
     . += [{
       fixture: $fx,
       cell_key: $key,
       was_present: ($was_present == "true"),
       prior_cell: $prior,
       cell: {
         model: $model,
         ide: $ide,
         audit_md_version: $fp,
         result: $result,
         hard_violation_count: $hard,
         soft_violation_count: $soft,
         rules_exercised: $rules,
         run_ids: [$rid],
         last_measured: $ts,
         _comment: (if $prior != null
                    then (($prior._comment // "") +
                          "\n\n(Preserved from prior cell under older fingerprint — human to review.)")
                    else "NEW cell. Human to review: add an explanatory _comment describing why this cell passes under the new fingerprint."
                    end)
       }
     }]' "$UPSERTS_FILE" > "$UPSERTS_FILE.new"
  mv "$UPSERTS_FILE.new" "$UPSERTS_FILE"
done

# ---- emit the merge candidate ----
jq -n \
  --arg old "$OLD_FP" \
  --arg new "$NEW_FP" \
  --arg ts "$TS" \
  --arg delta "$DELTA" \
  --arg pe "$PE_FILE" \
  --slurpfile upserts "$UPSERTS_FILE" '
  {
    kind: "baseline-merge-candidate",
    generated_at: $ts,
    old_fingerprint: $old,
    new_fingerprint: $new,
    delta_summary: (if $delta == "" then null else $delta end),
    proposed_edits_file: (if $pe == "" then null else $pe end),
    upserts: $upserts[0],
    history_entry: {
      audit_md_version: $new,
      promoted_at: $ts,
      delta_summary: (if $delta == "" then null else $delta end),
      proposed_edits_file: (if $pe == "" then null else $pe end)
    },
    review_checklist: [
      "Verify new_fingerprint matches AUDIT.md sha256.",
      "For each upsert with was_present=true: confirm prior_cell._comment content that should carry forward.",
      "For each upsert with was_present=false: author a real _comment describing load-bearing invariants.",
      "Confirm rules_exercised map has no silent coverage loss vs. prior_cell.",
      "Append history_entry to baseline.history[] (append-only; R-anti-drift-history-append-only).",
      "Update baseline.last_promoted and baseline.promoted_by.",
      "Re-run scripts/coverage-sweep.py after merge and confirm PROBLEMS: none."
    ]
  }
' > "$OUT"

rm -f "$UPSERTS_FILE"

echo "Wrote merge candidate: $OUT"
echo "  old fingerprint: $OLD_FP"
echo "  new fingerprint: $NEW_FP"
echo "  upserts:         $(jq '.upserts | length' "$OUT")"
echo ""
echo "This file is a PROPOSAL. baseline.json was NOT modified."
echo "Review, edit the _comment fields by hand, then merge into baseline.json."
exit 0
