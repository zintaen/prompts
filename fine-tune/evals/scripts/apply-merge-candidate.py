#!/usr/bin/env python3
"""apply-merge-candidate.py — generalize the E007 one-shot `_merge_e007.py`.

Accepts any `baseline-merge-candidate-*.json` emitted by `promote-baseline.sh`
and merges it into `baseline.json` with:

  - short-key translation (cell keys use `sha256:XXXXXXXX`, stored
    `audit_md_version` is the full 71-char string)
  - `notes` carry-forward from the prior cell under the old fingerprint
    (translating from `_comment` if the candidate emitted that — `notes` is
    the field name used inside `baseline.json` cells; `_comment` is what
    `promote-baseline.sh` writes into the candidate)
  - rule-survival preservation: the `rules_exercised` map gets the canonical
    `_comment` preamble prepended so coverage-sweep.py keeps its invariant
  - history append-only: a new entry is appended to `baseline.history[]`,
    existing entries are never mutated (per R-anti-drift-history-append-only)
  - `last_promoted` and `promoted_by` are stamped on the baseline root

By default writes to `baseline.json.new` for human inspection, so a reviewer
can diff before swapping. Use `--in-place` to write directly to
`baseline.json` (still backs up to `baseline.json.bak-pre-<label>` first).

Usage (typical):
  apply-merge-candidate.py \\
      --candidate fine-tune/evals/runs/baseline-merge-candidate-<date>.json \\
      --promoted-by "E008 hand-merge (fingerprint-format collapse)" \\
      --delta-summary "E002: collapse fingerprint-format to §Fingerprint normalization; -30 lines"

Exit codes:
  0  merge written
  2  precondition failure (fingerprint mismatch, shape error, missing files)
  3  rule-survival regression detected (merge NOT written)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
from datetime import datetime, timezone

RULES_EXERCISED_COMMENT = (
    "Per-rule pass/fail. Each entry: rule_id -> 'pass' | 'fail' | "
    "'not_exercised'. The 'rule survival invariant' (criteria.md §11) requires "
    "that any rule with at least one pass in any prior baselined version MUST "
    "have at least one pass in the current version."
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "baseline.json"


def die(msg: str, code: int = 2) -> None:
    sys.stderr.write(f"apply-merge-candidate.py: {msg}\n")
    sys.exit(code)


def short_fp(full: str) -> str:
    """Translate `sha256:<64hex>` to the 16-char short form `sha256:<8hex>`.
    baseline.json cell keys use the short form for readability; the stored
    `audit_md_version` is the full form."""
    if not full.startswith("sha256:") or len(full) != 71:
        die(f"not a valid full fingerprint: {full!r}")
    return full[: len("sha256:") + 8]  # sha256: + 8 hex chars


def find_prior_cell(
    cells: dict, model: str, ide: str
) -> tuple[str | None, dict | None]:
    """Find the most recent cell in `cells` matching (model, ide). Returns
    (cell_key, cell) or (None, None). 'Most recent' is defined by
    `last_measured` if present, else by alphabetical key order."""
    matches = [
        (k, v)
        for k, v in cells.items()
        if v.get("model") == model and v.get("ide") == ide
    ]
    if not matches:
        return None, None
    # Sort by last_measured desc, then key desc
    matches.sort(
        key=lambda kv: (kv[1].get("last_measured", ""), kv[0]),
        reverse=True,
    )
    return matches[0]


def carry_forward_notes(
    prior_notes: str,
    new_fp_short: str,
    promoted_at: str,
    note_preamble: str | None,
) -> str:
    """Build the new cell's `notes` field by prepending a carry-forward
    preamble and including the prior cell's notes verbatim for traceability.
    """
    default_preamble = (
        f"Refreshed under new fingerprint {new_fp_short} on {promoted_at}."
    )
    preamble = note_preamble or default_preamble
    if prior_notes:
        return (
            f"{preamble}\n\n"
            "Prior note carried forward for traceability:\n"
            f"{prior_notes}"
        )
    return preamble + "\n\n(No prior note to carry forward.)"


def check_rule_survival(
    prior_cell: dict | None, new_rules: dict
) -> list[str]:
    """Return a list of rule_ids that REGRESS from pass (prior) to not-pass
    (new). Empty list means no regression."""
    if prior_cell is None:
        return []
    prior_rules = prior_cell.get("rules_exercised", {})
    regressions = []
    for rule_id, prior_status in prior_rules.items():
        if rule_id == "_comment":
            continue
        if prior_status != "pass":
            continue
        new_status = new_rules.get(rule_id, "not_exercised")
        if new_status != "pass":
            regressions.append(f"{rule_id}: prior=pass, new={new_status}")
    return regressions


def build_new_cell(
    upsert: dict,
    new_fp_full: str,
    new_fp_short: str,
    promoted_at: str,
    prior_cell: dict | None,
    note_preamble: str | None,
) -> dict:
    """Assemble a baseline.json cell matching the conventions already in use
    (field `notes`, rules_exercised with _comment at the front)."""
    cell = upsert["cell"]
    rules = dict(cell.get("rules_exercised", {}))
    # Strip any existing _comment before prepending our canonical one.
    rules.pop("_comment", None)
    rules_ordered = {"_comment": RULES_EXERCISED_COMMENT, **rules}

    prior_notes = ""
    if prior_cell:
        # baseline.json cells store the prose under `notes`, but the
        # candidate (from promote-baseline.sh) stores it under `_comment`
        # in the `prior_cell` field. Accept either.
        prior_notes = prior_cell.get("notes") or prior_cell.get("_comment") or ""

    new_notes = carry_forward_notes(
        prior_notes=prior_notes,
        new_fp_short=new_fp_short,
        promoted_at=promoted_at,
        note_preamble=note_preamble,
    )

    return {
        "model": cell["model"],
        "ide": cell["ide"],
        "result": cell["result"],
        "hard_violation_count": cell.get("hard_violation_count", 0),
        "soft_violation_count": cell.get("soft_violation_count", 0),
        "rules_exercised": rules_ordered,
        "run_ids": cell.get("run_ids", []),
        "last_measured": cell.get("last_measured") or promoted_at,
        "notes": new_notes,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--candidate", required=True, help="path to baseline-merge-candidate-*.json")
    p.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="path to baseline.json (default: fine-tune/evals/baseline.json)")
    p.add_argument("--promoted-by", required=True, help="short label stamped on baseline.promoted_by and included in history[]")
    p.add_argument("--delta-summary", default=None, help="override candidate.delta_summary for the history entry")
    p.add_argument("--proposed-edits", default=None, help="override candidate.proposed_edits_file for the history entry")
    p.add_argument("--net-line-delta", type=int, default=None, help="optional int to record in history[].net_line_delta")
    p.add_argument("--note-preamble", default=None, help="custom preamble string for the cell notes field (default: generic 'Refreshed under fingerprint X on TS.')")
    p.add_argument("--in-place", action="store_true", help="overwrite baseline.json directly (backs up first). Default writes to baseline.json.new")
    p.add_argument("--dry-run", action="store_true", help="print plan, do not write anything")
    p.add_argument("--allow-rule-regression", action="store_true", help="proceed even if a rule regresses from pass to non-pass in any upserted cell (NOT RECOMMENDED; breaks rule-survival invariant)")
    args = p.parse_args()

    cand_path = pathlib.Path(args.candidate)
    base_path = pathlib.Path(args.baseline)
    if not cand_path.exists():
        die(f"candidate not found: {cand_path}")
    if not base_path.exists():
        die(f"baseline not found: {base_path}")

    candidate = json.loads(cand_path.read_text())
    baseline = json.loads(base_path.read_text())

    # ---- shape validation ----
    if candidate.get("kind") != "baseline-merge-candidate":
        die(f"candidate.kind != 'baseline-merge-candidate' (got {candidate.get('kind')!r})")
    for k in ("old_fingerprint", "new_fingerprint", "upserts"):
        if k not in candidate:
            die(f"candidate missing required field: {k}")
    if not candidate["upserts"]:
        die("candidate.upserts is empty; nothing to merge")

    # ---- fingerprint gate ----
    if baseline.get("audit_md_version") != candidate["old_fingerprint"]:
        die(
            f"fingerprint mismatch: baseline.audit_md_version="
            f"{baseline.get('audit_md_version')!r} vs "
            f"candidate.old_fingerprint={candidate['old_fingerprint']!r}.\n"
            "Refusing to merge — the candidate was computed against a different "
            "base."
        )

    new_fp_full = candidate["new_fingerprint"]
    new_fp_short = short_fp(new_fp_full)
    promoted_at = candidate.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- plan cells + rule-survival pre-check ----
    print(f"merging candidate: {cand_path.name}")
    print(f"  old fingerprint: {candidate['old_fingerprint']}")
    print(f"  new fingerprint: {new_fp_full}")
    print(f"  short key form:  {new_fp_short}")
    print(f"  upserts:         {len(candidate['upserts'])}")
    print(f"  promoted_by:     {args.promoted_by}")
    print()

    all_regressions: list[tuple[str, list[str]]] = []
    planned_cells: list[tuple[str, str, dict]] = []  # (fixture, new_key, new_cell)

    for up in candidate["upserts"]:
        fixture = up["fixture"]
        cell = up["cell"]
        model = cell["model"]
        ide = cell["ide"]

        fixture_block = baseline.setdefault("fixtures", {}).get(fixture)
        if fixture_block is None:
            die(f"fixture {fixture!r} not in baseline.fixtures — refusing to add a new fixture silently; add it by hand first")

        existing_cells = fixture_block.setdefault("cells", {})
        _, prior_cell = find_prior_cell(existing_cells, model, ide)

        regressions = check_rule_survival(prior_cell, cell.get("rules_exercised", {}))
        if regressions:
            all_regressions.append((fixture, regressions))

        new_key = f"{model}|{ide}|{new_fp_short}"
        if new_key in existing_cells:
            print(f"  WARNING: {fixture}[{new_key}] already exists — will overwrite")
        new_cell = build_new_cell(
            upsert=up,
            new_fp_full=new_fp_full,
            new_fp_short=new_fp_short,
            promoted_at=promoted_at,
            prior_cell=prior_cell,
            note_preamble=args.note_preamble,
        )
        planned_cells.append((fixture, new_key, new_cell))
        print(f"  plan: {fixture}[{new_key}] result={new_cell['result']} hard={new_cell['hard_violation_count']} soft={new_cell['soft_violation_count']}")

    if all_regressions:
        print("\nrule-survival regressions detected:", file=sys.stderr)
        for fx, regs in all_regressions:
            print(f"  {fx}:", file=sys.stderr)
            for r in regs:
                print(f"    - {r}", file=sys.stderr)
        if not args.allow_rule_regression:
            sys.stderr.write(
                "\nRefusing to merge. Use --allow-rule-regression to override "
                "(violates criteria.md §11; coverage-sweep.py will flag PROBLEMS).\n"
            )
            return 3
        sys.stderr.write("\n--allow-rule-regression is set; proceeding anyway.\n")

    # ---- commit cells to baseline object ----
    for fixture, new_key, new_cell in planned_cells:
        baseline["fixtures"][fixture]["cells"][new_key] = new_cell

    baseline["audit_md_version"] = new_fp_full
    baseline["last_promoted"] = promoted_at
    baseline["promoted_by"] = args.promoted_by

    history = baseline.setdefault("history", [])
    hist_entry = {
        "audit_md_version": new_fp_full,
        "promoted_at": promoted_at,
        "delta_summary": args.delta_summary or candidate.get("delta_summary"),
        "proposed_edits_file": args.proposed_edits or candidate.get("proposed_edits_file"),
    }
    if args.net_line_delta is not None:
        hist_entry["net_line_delta"] = args.net_line_delta
    history.append(hist_entry)

    total_cells = sum(len(f["cells"]) for f in baseline["fixtures"].values())

    if args.dry_run:
        print(f"\n[dry-run] would write baseline with {total_cells} total cells, {len(history)} history entries")
        return 0

    # ---- write output ----
    if args.in_place:
        label = args.promoted_by.split()[0].lower().replace("/", "-")
        backup = base_path.with_suffix(base_path.suffix + f".bak-pre-{label}")
        shutil.copy2(base_path, backup)
        print(f"\nbacked up previous baseline to: {backup}")
        out_path = base_path
    else:
        out_path = base_path.with_suffix(base_path.suffix + ".new")

    out_path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {out_path}")
    print(f"  audit_md_version: {new_fp_full}")
    print(f"  history entries:  {len(history)}")
    print(f"  total cells:      {total_cells}")
    if not args.in_place:
        print(
            "\nThis is a PROPOSAL. baseline.json was NOT modified.\n"
            "Review, then either rename baseline.json.new → baseline.json\n"
            "or re-run with --in-place."
        )
    print("\nNext: run `fine-tune/evals/scripts/coverage-sweep.py` and confirm PROBLEMS: none.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
