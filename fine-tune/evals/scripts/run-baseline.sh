#!/usr/bin/env bash
# run-baseline.sh — replay every fixture's build.py (plus fault_inject.py if
# present) and aggregate pass/fail into a baseline-candidate JSON. Does NOT
# overwrite baseline.json.
#
# Usage:
#   run-baseline.sh [--audit-md ../../../AUDIT.md] [--out ../runs/baseline-candidate-<date>.json]
#                   [--fixtures F001,F003,...]
#                   [--skip-faults]
#
# For each fixture under fixtures/, the script looks for the most recent run
# directory under runs/ whose folder name contains the fixture's slug and
# re-runs that run's build.py. If --skip-faults is not set, it also runs
# fault_inject.py in the same directory when it exists.
#
# Output: a JSON file summarizing fixture × {build, fault_inject} outcomes.
#
# Exit code: 0 if every selected fixture's build PASSED (and every fault
# harness that existed passed). Nonzero on any failure.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
EVALS="$(cd "$HERE/.." && pwd)"
AUDIT_MD="$EVALS/../../AUDIT.md"
DATE="$(date -u +%Y-%m-%d)"
OUT="$EVALS/runs/baseline-candidate-${DATE}.json"
ONLY=""
SKIP_FAULTS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --audit-md)    AUDIT_MD="$2"; shift 2 ;;
    --out)         OUT="$2"; shift 2 ;;
    --fixtures)    ONLY="$2"; shift 2 ;;
    --skip-faults) SKIP_FAULTS=1; shift ;;
    -h|--help)     sed -n '1,25p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$AUDIT_MD" ]] || { echo "AUDIT.md not found at $AUDIT_MD" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 required" >&2; exit 2; }
command -v jq       >/dev/null || { echo "jq required" >&2; exit 2; }

FP="sha256:$(shasum -a 256 "$AUDIT_MD" | awk '{print $1}')"

echo "run-baseline.sh"
echo "  AUDIT.md fingerprint: $FP"
echo "  Output candidate:     $OUT"
echo ""

# -- resolve fixture set --
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

# -- accumulators --
RESULTS_JSON="$(mktemp)"
echo '[]' > "$RESULTS_JSON"

OVERALL_OK=1

for fx in "${FIXTURES[@]}"; do
  SLUG="${fx#F[0-9][0-9][0-9]-}"                 # e.g. 'fresh-repo-small'
  FX_NUM="$(echo "$fx" | grep -oE '^F[0-9]{3}')"  # e.g. 'F001'

  # Find the most recent run dir that matches this fixture by slug
  # (grep any build.py that mentions the fixture id, then strip /build.py).
  RUN_DIR="$(grep -rl "$fx" "$EVALS/runs" --include=build.py 2>/dev/null \
             | sort | tail -n1)"
  RUN_DIR="${RUN_DIR%/build.py}"

  if [[ -z "${RUN_DIR:-}" ]]; then
    echo "[$fx] NO-RUN-DIR — no build.py references this fixture"
    OVERALL_OK=0
    jq --arg f "$fx" '. += [{fixture:$f, build:"NO-RUN-DIR", fault_inject:"N/A"}]' \
       "$RESULTS_JSON" > "$RESULTS_JSON.new"; mv "$RESULTS_JSON.new" "$RESULTS_JSON"
    continue
  fi

  echo "[$fx] run_dir=$(realpath --relative-to="$EVALS" "$RUN_DIR")"

  # -- fixture type: resume fixtures mutate pre-existing state and cannot be
  #    cleanly replayed in isolation. Skip the replay and defer to the baseline
  #    cell as authoritative. Do NOT treat as failure.
  FX_TYPE="$(grep -E '^type:' "$EVALS/fixtures/$fx/fixture.yaml" | awk '{print $2}')"
  if [[ "$FX_TYPE" == "resume" ]]; then
    echo "       build=SKIPPED (resume — replay requires pre-seeded state)  fault=N/A"
    jq --arg f "$fx" --arg rd "$(realpath --relative-to="$EVALS" "$RUN_DIR")" \
       '. += [{fixture:$f, run_dir:$rd, build:"SKIPPED-RESUME", fault_inject:"N/A"}]' \
       "$RESULTS_JSON" > "$RESULTS_JSON.new"; mv "$RESULTS_JSON.new" "$RESULTS_JSON"
    continue
  fi

  # -- build.py --
  if (cd "$RUN_DIR" && python3 build.py >/tmp/f_build.$$.log 2>&1); then
    BUILD="PASS"
    # parse capture.json for step_7_5_passed (defensive)
    if [[ -f "$RUN_DIR/capture.json" ]]; then
      STEP=$(jq -r '.step_7_5_passed' "$RUN_DIR/capture.json")
      HARD=$(jq -r '.hard_violation_count' "$RUN_DIR/capture.json")
      if [[ "$STEP" != "true" || "$HARD" != "0" ]]; then
        BUILD="FAIL (step_7_5=$STEP hard=$HARD)"
      fi
    fi
  else
    BUILD="FAIL (exit code)"
    sed -n '1,10p' /tmp/f_build.$$.log | sed 's/^/       /'
  fi
  rm -f /tmp/f_build.$$.log

  # -- fault_inject.py --
  FAULT="N/A"
  if [[ "$SKIP_FAULTS" == "0" && -f "$RUN_DIR/fault_inject.py" ]]; then
    if (cd "$RUN_DIR" && python3 fault_inject.py >/tmp/f_fault.$$.log 2>&1); then
      FAULT="PASS"
    else
      FAULT="FAIL"
      sed -n '1,20p' /tmp/f_fault.$$.log | sed 's/^/       /'
    fi
    rm -f /tmp/f_fault.$$.log
  fi

  echo "       build=$BUILD  fault=$FAULT"
  if [[ "$BUILD" != "PASS" || "$FAULT" == "FAIL" ]]; then
    OVERALL_OK=0
  fi

  jq --arg f "$fx" --arg rd "$(realpath --relative-to="$EVALS" "$RUN_DIR")" \
     --arg b "$BUILD" --arg fa "$FAULT" \
     '. += [{fixture:$f, run_dir:$rd, build:$b, fault_inject:$fa}]' \
     "$RESULTS_JSON" > "$RESULTS_JSON.new"; mv "$RESULTS_JSON.new" "$RESULTS_JSON"
done

# -- emit candidate JSON --
jq -n --arg fp "$FP" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --slurpfile r "$RESULTS_JSON" \
      '{audit_md_version:$fp, generated_at:$ts, results:$r[0]}' \
      > "$OUT"

echo ""
echo "Wrote candidate: $OUT"

# -- finally, cross-check against registry via coverage-sweep --
echo ""
echo "Running coverage-sweep.py..."
python3 "$HERE/coverage-sweep.py" || OVERALL_OK=0

if [[ "$OVERALL_OK" == "1" ]]; then
  echo ""
  echo "run-baseline: ALL GREEN."
  exit 0
fi
echo ""
echo "run-baseline: FAILURES DETECTED — see log above."
exit 1
