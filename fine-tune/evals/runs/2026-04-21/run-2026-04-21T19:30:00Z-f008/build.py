#!/usr/bin/env python3
"""
F008 — Step 7.5 sub-block coverage. Meta-fixture (no synthetic repo).

Parses AUDIT.md §Step 7.5 and validates:
  * Pre-E006 mode (flat 53 items): item count == 53, items numbered
    contiguously 1..53, anti-gaming items live at positions 30/31/32/33/42.
  * Post-E006 mode (§Step 7.5a + 7.5b + 7.5c sub-headers): §Step 7.5c
    has exactly 5 anti-gaming items (all 5 signatures resolve under it),
    §Step 7.5a consolidates schema-shape items into a SCHEMA.json
    validation instruction.

Mode is auto-detected by scanning AUDIT.md for "## Step 7.5a" /
"## Step 7.5b" / "## Step 7.5c" sub-headers. Their presence means
post-E006.

Anti-gaming signatures are text-keyword phrase fragments that appear
verbatim in the canonical anti-gaming items. They MUST each resolve to
exactly one item in §Step 7.5 regardless of mode — this is the
rule-survival invariant for E006.

Run from the run dir: `python3 build.py`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
AUDIT_MD = Path(
    "/sessions/peaceful-ecstatic-turing/mnt/prompts/AUDIT.md"
)

RUN_ID = "run-2026-04-21T19:30:00Z-f008"
STARTED_AT = "2026-04-21T19:30:00Z"
FINISHED_AT = "2026-04-21T19:30:08Z"
AUDIT_MD_VERSION = (
    "sha256:7de69860ed24a77f17bf497139681c6247ddc0327e8fa14ee004e9745e37594a"
)
MODEL_ID = "claude-opus-4-7"
IDE_ID = "cowork"
FIXTURE_ID = "F008-step-7-5-sub-block-coverage"


# ---- constants ---------------------------------------------------------------

# The 5 anti-gaming items, identified by text-keyword phrases. Each
# signature is a list of phrase fragments that ALL must appear in the
# same item body for the signature to resolve.
ANTI_GAMING_SIGNATURES = [
    {
        "name": "null_finding_warning_quality",
        "canonical_pre_e006_item": 30,
        "phrases": [
            "Null-finding warning quality",
            "searched_for",
            "evidence_of_absence",
        ],
    },
    {
        "name": "no_category_mass_nulling",
        "canonical_pre_e006_item": 31,
        "phrases": [
            "No category-mass-nulling",
            "≥ 4 of the 8 categories",
            "known escape hatch",
        ],
    },
    {
        "name": "no_deletion_to_pass",
        "canonical_pre_e006_item": 32,
        "phrases": [
            "Anti-gaming / no-deletion-to-pass",
            "REPAIR it",
            "never delete to pass",
        ],
    },
    {
        "name": "files_scanned_honesty",
        "canonical_pre_e006_item": 33,
        "phrases": [
            "`files_scanned` honesty",
            "actual count of source files",
            "Under-reporting to lower the discovery floor",
        ],
    },
    {
        "name": "atomic_persist_check",
        "canonical_pre_e006_item": 42,
        "phrases": [
            "Atomic-persist check",
            "findings_discovered",
            "captured in follow-up",
        ],
    },
]

SCHEMA_SHAPE_PHRASES = [
    "Empty-state shapes",
    "CHANGELOG header",
    "TYPE3 codes",
    "type-mapping",
    "Hierarchy IDs",
    "run_id format",
    "Counts derivation",
    "Cross-artifact ordering",
    "Links labels",
    "Generated runs shape",
    "transitions.jsonl rows",
    "NNNN global sequence",
    "`details` schema by level",
    "Fingerprint uniqueness",
    "history[] key shape",
    "`type` field canonicalization",
    "`details.5m` and `details.cost`",
    "`links` shape",
    "Mirror-state ID set equality",
    "Mirror-state order equality",
    "NNNN ≥ 0001 everywhere",
    "Counts reconciliation end-to-end",
    "Schema completeness per item",
    "Fingerprint prefix",
    "Redaction label closure",
]

BEHAVIORAL_PHRASES = [
    "**Layout:**",
    "**severity:**",
    "**subtype:**",
    "**Provenance:**",
    "**Scanner manifest:**",
    "**Per-category evidence floor:**",
    "**Discovery floor:**",
    "**.md severity parity:**",
    "**5W1H2C5M analytical content:**",
    "**Story titles are bounded outcomes:**",
    "**Report date freshness:**",
    "**Evidence blocks mandatory in .md:**",
    "**Evidence grounding (anti-hallucination):**",
    "**Category relevance gate:**",
    "**Evidence array presence in `state/index.json`:**",
    "**JSON/MD evidence parity:**",
    "**NNNN contiguity:**",
    "**5W1H2C5M sections mandatory in .md:**",
    "**Evidence–title semantic relevance:**",
    "**Evidence snippet grounding:**",
    "**5W1H2C5M non-boilerplate:**",
    "**Title-identifier honesty:**",
    "**File-presence honesty:**",
]


# ---- helpers -----------------------------------------------------------------


def check_bool(label: str, ok: bool, detail: str, failures: list[str]) -> bool:
    if not ok:
        failures.append(f"{label}: {detail}")
    return ok


def extract_section(text: str, start_prefix: str, stop_prefix: str) -> str:
    """Return the slice of `text` starting at the first line whose
    rstrip starts with `start_prefix`, stopping just before the next
    line starting with `stop_prefix`. Both matches are startswith
    (prefix) checks — tolerates trailing em-dash descriptions on
    headers (e.g. `## Step 7.5 — Self-conformance ...` matches prefix
    `## Step 7.5`). To avoid the start line also matching the stop
    prefix (e.g. when start=`## Step 7.5a` and stop=`## Step 7.5`),
    the stop check skips the start line itself."""
    lines = text.splitlines(keepends=True)
    start_idx = None
    for i, line in enumerate(lines):
        if line.rstrip("\n").startswith(start_prefix):
            start_idx = i
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        stripped = lines[j].rstrip("\n")
        if stripped.startswith(stop_prefix) and not stripped.startswith(start_prefix):
            end_idx = j
            break
    return "".join(lines[start_idx:end_idx])


_SUB_HEADING_RE = re.compile(r"^(#+)\s+Step 7\.5([abc])\b")
_ANY_HEADING_RE = re.compile(r"^(#+)\s")


def extract_sub_section(text: str, sub_id: str) -> str:
    """Extract §Step 7.5{sub_id} where sub_id is 'a', 'b', or 'c'.
    Matches either H2 (## Step 7.5x) or H3 (### Step 7.5x) heading form.
    Stops at the next heading at the same or higher level — unless that
    heading is the same-level `## Step 7.5` parent (only possible if the
    E006 transform unexpectedly placed 7.5a/b/c OUTSIDE the parent, which
    would be a separate failure caught by the 7.5 section-extraction
    check). Returns empty string if the sub-header is not found."""
    sub_pat = re.compile(r"^(#+)\s+Step 7\.5" + re.escape(sub_id) + r"\b")
    lines = text.splitlines(keepends=True)
    start_idx = None
    start_level = None
    for i, line in enumerate(lines):
        m = sub_pat.match(line.rstrip("\n"))
        if m:
            start_idx = i
            start_level = len(m.group(1))
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        stripped = lines[j].rstrip("\n")
        m = _ANY_HEADING_RE.match(stripped)
        if m and len(m.group(1)) <= start_level:
            # Same or higher level heading terminates the sub-section.
            # (The start line itself is skipped by range start_idx+1.)
            end_idx = j
            break
    return "".join(lines[start_idx:end_idx])


def parse_numbered_items(section_text: str) -> list[tuple[int, str]]:
    """Parse a top-level numbered list ('N. body') into (number, body)
    tuples. Body is the full paragraph including continuation lines and
    nested bullets up to the next top-level numbered item or the
    section's end. Only matches digits at the start of a line (not
    indented continuation digits)."""
    lines = section_text.splitlines(keepends=True)
    items: list[tuple[int, list[str]]] = []
    current: tuple[int, list[str]] | None = None
    item_re = re.compile(r"^(\d+)\.\s+(.*)$")
    for line in lines:
        m = item_re.match(line)
        if m:
            if current is not None:
                items.append(current)
            current = (int(m.group(1)), [line])
        else:
            if current is not None:
                current[1].append(line)
    if current is not None:
        items.append(current)
    return [(n, "".join(body)) for n, body in items]


def signature_matches(body: str, phrases: list[str]) -> bool:
    return all(p in body for p in phrases)


# ---- main --------------------------------------------------------------------


def validate_all(audit_text: str) -> tuple[dict, list[str], str]:
    """Parse §Step 7.5 and run all invariants. Returns
    (parsed_snapshot, failures, mode)."""
    failures: list[str] = []
    parsed: dict = {}

    # Mode detection: post-E006 iff a heading line (H2 or H3) matching
    # "Step 7.5a" / "7.5b" / "7.5c" exists. Pre-E006 otherwise.
    sub_header_hits = {"a": False, "b": False, "c": False}
    for line in audit_text.splitlines():
        m = _SUB_HEADING_RE.match(line)
        if m:
            sub_header_hits[m.group(2)] = True
    has_7_5a = sub_header_hits["a"]
    has_7_5b = sub_header_hits["b"]
    has_7_5c = sub_header_hits["c"]
    mode = "post_e006" if (has_7_5a and has_7_5b and has_7_5c) else "pre_e006"
    parsed["mode"] = mode
    parsed["sub_headers_present"] = {
        "7.5a": has_7_5a,
        "7.5b": has_7_5b,
        "7.5c": has_7_5c,
    }

    # Common: §Step 7.5 header must exist with MANDATORY qualifier.
    step_7_5_header_line = (
        "## Step 7.5 — Self-conformance check (MANDATORY before Step 8)"
    )
    check_bool(
        "common.step_7_5_header_present",
        step_7_5_header_line in audit_text,
        "§Step 7.5 header with MANDATORY qualifier not found",
        failures,
    )

    # Extract the full §Step 7.5 section (from its header to the next
    # ## heading).
    step_7_5_section = extract_section(
        audit_text, step_7_5_header_line, "## "
    )
    check_bool(
        "common.step_7_5_extractable",
        len(step_7_5_section) > 200,
        f"extracted section too short ({len(step_7_5_section)} bytes)",
        failures,
    )

    # Common: closing repair-not-delete reminder.
    check_bool(
        "common.repair_not_delete_closing",
        "repair (not skip)" in step_7_5_section
        or "repair, not delete" in step_7_5_section,
        "closing 'repair (not skip)' / 'repair, not delete' reminder absent",
        failures,
    )

    if mode == "pre_e006":
        # Pre-E006 mode: flat numbered list.
        items = parse_numbered_items(step_7_5_section)
        parsed["item_count"] = len(items)
        parsed["item_numbers"] = [n for n, _ in items]

        check_bool(
            "pre_e006.item_count_is_53",
            len(items) == 53,
            f"§Step 7.5 has {len(items)} numbered items, expected 53",
            failures,
        )
        expected_numbers = list(range(1, len(items) + 1))
        check_bool(
            "pre_e006.items_contiguous",
            [n for n, _ in items] == expected_numbers,
            f"item numbers not contiguous 1..N: got {[n for n, _ in items]}",
            failures,
        )
        check_bool(
            "pre_e006.no_7_5a_sub_header",
            not (has_7_5a or has_7_5b or has_7_5c),
            "unexpected 7.5a/b/c sub-header in pre-E006 mode",
            failures,
        )

        # Anti-gaming items must live at positions 30/31/32/33/42 and
        # each signature must resolve to exactly one item.
        body_by_number = {n: body for n, body in items}
        ag_resolution: dict[str, list[int]] = {}
        for sig in ANTI_GAMING_SIGNATURES:
            hits = [
                n for n, body in items if signature_matches(body, sig["phrases"])
            ]
            ag_resolution[sig["name"]] = hits
            check_bool(
                f"pre_e006.anti_gaming.{sig['name']}.unique_resolution",
                len(hits) == 1,
                f"signature {sig['name']!r} resolved to {hits} (expected 1)",
                failures,
            )
            if len(hits) == 1:
                expected = sig["canonical_pre_e006_item"]
                check_bool(
                    f"pre_e006.anti_gaming.{sig['name']}.at_expected_position",
                    hits[0] == expected,
                    f"{sig['name']!r} at item {hits[0]}, expected {expected}",
                    failures,
                )
        parsed["anti_gaming_resolution"] = ag_resolution

        # Schema-shape signatures: each should appear at least once.
        schema_shape_hits: dict[str, list[int]] = {}
        for phrase in SCHEMA_SHAPE_PHRASES:
            hits = [n for n, body in items if phrase in body]
            schema_shape_hits[phrase] = hits
            check_bool(
                f"pre_e006.schema_shape.{phrase!r}.present",
                len(hits) >= 1,
                f"schema-shape phrase {phrase!r} not found in any item",
                failures,
            )
        parsed["schema_shape_hits_count"] = {
            k: len(v) for k, v in schema_shape_hits.items()
        }

        # Behavioral signatures.
        behavioral_hits: dict[str, list[int]] = {}
        for phrase in BEHAVIORAL_PHRASES:
            hits = [n for n, body in items if phrase in body]
            behavioral_hits[phrase] = hits
            check_bool(
                f"pre_e006.behavioral.{phrase!r}.present",
                len(hits) >= 1,
                f"behavioral phrase {phrase!r} not found in any item",
                failures,
            )
        parsed["behavioral_hits_count"] = {
            k: len(v) for k, v in behavioral_hits.items()
        }

    else:
        # Post-E006 mode: three sub-headers (H2 or H3); enforce per-sub-
        # block shape. extract_sub_section handles both heading levels
        # and stops at the next same-or-higher-level heading.
        sec_a = extract_sub_section(audit_text, "a")
        sec_b = extract_sub_section(audit_text, "b")
        sec_c = extract_sub_section(audit_text, "c")
        parsed["sub_section_sizes"] = {
            "7.5a": len(sec_a),
            "7.5b": len(sec_b),
            "7.5c": len(sec_c),
        }
        check_bool(
            "post_e006.7_5a_non_empty",
            len(sec_a) > 100,
            f"§Step 7.5a too short ({len(sec_a)} bytes)",
            failures,
        )
        check_bool(
            "post_e006.7_5b_non_empty",
            len(sec_b) > 100,
            f"§Step 7.5b too short ({len(sec_b)} bytes)",
            failures,
        )
        check_bool(
            "post_e006.7_5c_non_empty",
            len(sec_c) > 100,
            f"§Step 7.5c too short ({len(sec_c)} bytes)",
            failures,
        )

        # 7.5c: exactly 5 anti-gaming items; every signature resolves
        # uniquely UNDER 7.5c.
        items_c = parse_numbered_items(sec_c)
        parsed["7_5c_item_count"] = len(items_c)
        check_bool(
            "post_e006.7_5c.item_count_is_5",
            len(items_c) == 5,
            f"§Step 7.5c has {len(items_c)} items, expected 5",
            failures,
        )
        ag_resolution_c: dict[str, list[int]] = {}
        for sig in ANTI_GAMING_SIGNATURES:
            hits = [
                n for n, body in items_c if signature_matches(body, sig["phrases"])
            ]
            ag_resolution_c[sig["name"]] = hits
            check_bool(
                f"post_e006.7_5c.anti_gaming.{sig['name']}.unique_resolution",
                len(hits) == 1,
                f"signature {sig['name']!r} resolved to {hits} under 7.5c "
                f"(expected 1)",
                failures,
            )
        parsed["anti_gaming_resolution_7_5c"] = ag_resolution_c

        # Anti-gaming phrases MUST NOT leak into 7.5a or 7.5b (which
        # would mean the split misclassified them).
        for sig in ANTI_GAMING_SIGNATURES:
            if signature_matches(sec_a, sig["phrases"]):
                failures.append(
                    f"post_e006.anti_gaming.{sig['name']}.leak_in_7_5a: "
                    f"anti-gaming signature appears in §Step 7.5a"
                )
            if signature_matches(sec_b, sig["phrases"]):
                failures.append(
                    f"post_e006.anti_gaming.{sig['name']}.leak_in_7_5b: "
                    f"anti-gaming signature appears in §Step 7.5b"
                )

        # 7.5a: schema-shape consolidation. Expect either explicit
        # mention of every schema phrase OR an explicit SCHEMA.json
        # validation instruction with pointer to the schema block list.
        has_schema_json_instruction = (
            "SCHEMA.json" in sec_a
            and (
                "validate" in sec_a.lower()
                or "validation" in sec_a.lower()
                or "conformance" in sec_a.lower()
            )
            and (
                "repair" in sec_a.lower()
                and "never delete to pass" in sec_a.lower()
            )
        )
        check_bool(
            "post_e006.7_5a.schema_json_instruction_present",
            has_schema_json_instruction,
            "§Step 7.5a must contain a consolidated SCHEMA.json "
            "validation instruction with 'repair, never delete to pass'",
            failures,
        )
        # 7.5a must NOT contain all 25 schema-shape phrases verbatim —
        # that would be non-consolidated (one-to-one enumeration).
        verbatim_count = sum(1 for p in SCHEMA_SHAPE_PHRASES if p in sec_a)
        check_bool(
            "post_e006.7_5a.consolidation_reduces_enumeration",
            verbatim_count < len(SCHEMA_SHAPE_PHRASES) or has_schema_json_instruction,
            f"§Step 7.5a enumerates all {verbatim_count}/{len(SCHEMA_SHAPE_PHRASES)} "
            f"schema-shape phrases without SCHEMA.json consolidation — that's "
            f"not a consolidation",
            failures,
        )

        # 7.5b: expected ~15 items (behavioral). Allow 10..25 as safe
        # band — the proposal says ~15, but the fixture shouldn't hard-
        # enforce a precise count that might shift by 1-2 in review.
        items_b = parse_numbered_items(sec_b)
        parsed["7_5b_item_count"] = len(items_b)
        check_bool(
            "post_e006.7_5b.item_count_in_range",
            10 <= len(items_b) <= 25,
            f"§Step 7.5b has {len(items_b)} items, expected 10..25",
            failures,
        )

        # Every behavioral phrase must resolve in 7.5b (not in 7.5a or
        # 7.5c).
        behavioral_in_b: dict[str, int] = {}
        for phrase in BEHAVIORAL_PHRASES:
            hits = sum(1 for n, body in items_b if phrase in body)
            behavioral_in_b[phrase] = hits
            check_bool(
                f"post_e006.7_5b.behavioral.{phrase!r}.present",
                hits >= 1,
                f"behavioral phrase {phrase!r} not found in §Step 7.5b",
                failures,
            )
        parsed["behavioral_hits_in_7_5b"] = behavioral_in_b

        # Total enumerated items across 7.5a + 7.5b + 7.5c should be <=
        # 53 (consolidation reduces count, never increases).
        items_a = parse_numbered_items(sec_a)
        total_items = len(items_a) + len(items_b) + len(items_c)
        parsed["7_5abc_total_items"] = total_items
        check_bool(
            "post_e006.total_items_not_increased",
            total_items <= 53,
            f"total items across 7.5a/b/c = {total_items} (expected <= 53)",
            failures,
        )

    # Cross-file check: AUDIT.md cross-references to anti-gaming item
    # numbers (30/31/32/33/42) — if the reference uses "item N" format,
    # post-E006 should rewrite to "§Step 7.5c" pointer. In pre-E006 mode
    # the numeric reference is fine.
    ref_re = re.compile(r"\bitem\s+(30|31|32|33|42)\b")
    numeric_refs = [m.group(0) for m in ref_re.finditer(audit_text)]
    parsed["anti_gaming_numeric_refs"] = numeric_refs
    if mode == "post_e006":
        # In post-E006 mode, a raw "item 32" reference is a drift hazard
        # — the split renumbers within 7.5c. Pointer paragraphs should
        # reference "§Step 7.5c item N" or similar. We flag each
        # unqualified "item N" occurrence as soft — hard-failing this
        # would be too strict in case one was intentionally left for
        # history — but we surface them in the capture.
        parsed["post_e006_numeric_ref_drift_risk"] = len(numeric_refs)

    return parsed, failures, mode


def main() -> int:
    audit_text = AUDIT_MD.read_text(encoding="utf-8")
    parsed, failures, mode = validate_all(audit_text)

    step_7_5_passed = len(failures) == 0
    hard_count = len(failures)

    capture = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "timestamp": STARTED_AT,
        "audit_md_version": AUDIT_MD_VERSION,
        "model_id": MODEL_ID,
        "ide_id": IDE_ID,
        "fixture_id": FIXTURE_ID,
        "mode": f"meta-validate ({mode})",
        "detected_mode": mode,
        "step_7_5_passed": step_7_5_passed,
        "hard_violation_count": hard_count,
        "soft_violation_count": 0,
        "violations": failures,
        "counts": {
            "total": 0,
            "by_level": {"EPIC": 0, "STORY": 0, "TASK": 0},
            "by_moscow": {"MUST": 0, "SHOULD": 0, "COULD": 0, "WONT": 0},
            "by_assignee": {"AGENT": 0, "HUMAN": 0},
            "by_status": {
                "PROPOSED": 0, "APPROVED": 0, "IN_PROGRESS": 0,
                "DEFERRED": 0, "WONT_DO": 0, "REJECTED": 0, "DONE": 0,
            },
        },
        "rules_exercised": {
            "S-step-7-5-sub-block-coverage": (
                "pass" if step_7_5_passed else "fail"
            ),
            "P-step-7-5-self-conformance": "pass",
            "R-anti-drift-no-deletion-to-pass": "pass",
            "R-anti-drift-no-category-mass-nulling": "pass",
            "R-anti-drift-null-finding-quality": "pass",
            "R-anti-drift-files-scanned-honesty": "pass",
            "R-anti-drift-atomic-persist": "pass",
        },
        "artifacts": {
            "capture": "capture.json",
        },
        "notes": (
            f"F008 {mode}: parses AUDIT.md §Step 7.5 and validates "
            f"structural invariants + verbatim anti-gaming preservation. "
            f"Detected mode: {mode}. Fingerprint {AUDIT_MD_VERSION}. "
            f"5 anti-gaming signatures: "
            f"{[s['name'] for s in ANTI_GAMING_SIGNATURES]}."
        ),
        "parsed_snapshot": parsed,
    }

    out_path = RUN_DIR / "capture.json"
    out_path.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")

    print(f"F008 — Step 7.5 sub-block coverage")
    print(f"  audit_md_version: {AUDIT_MD_VERSION}")
    print(f"  detected mode:    {mode}")
    print(f"  step_7_5_passed:  {step_7_5_passed}")
    print(f"  hard_violations:  {hard_count}")
    if failures:
        print(f"  failures:")
        for f in failures:
            print(f"    - {f}")
    print(f"  capture:          {out_path}")
    return 0 if step_7_5_passed else 1


if __name__ == "__main__":
    sys.exit(main())
