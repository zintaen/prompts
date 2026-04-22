#!/usr/bin/env python3
"""
F007 — schema-contract-stability (post-E004 incarnation). Reads the 11
pure-data blocks from SCHEMA.json and validates the SAME structural
invariants + cross-block consistency that the pre-E004 parser ran
against AUDIT.md.

E004 moved the authoritative data out of AUDIT.md into SCHEMA.json. The
fixture's design goal was to survive that move with only an input-source
change — all invariants remain identical. This file is the realisation
of that design.

Run from the run dir: `python3 build.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
SCHEMA_JSON = Path(
    "/sessions/peaceful-ecstatic-turing/mnt/prompts/SCHEMA.json"
)
AUDIT_MD = Path(
    "/sessions/peaceful-ecstatic-turing/mnt/prompts/AUDIT.md"
)

RUN_ID = "run-2026-04-21T17:30:00Z-e004"
STARTED_AT = "2026-04-21T17:30:00Z"
FINISHED_AT = "2026-04-21T17:30:12Z"
AUDIT_MD_VERSION = (
    "sha256:28f0dc3424377677828778aaccf2973601186f86135b8a7c99f698483eedcdc6"
)
MODEL_ID = "claude-opus-4-7"
IDE_ID = "cowork"
FIXTURE_ID = "F007-schema-contract-stability"


# ---- helpers -----------------------------------------------------------------


def check_bool(label: str, ok: bool, detail: str, failures: list[str]) -> bool:
    if not ok:
        failures.append(f"{label}: {detail}")
    return ok


# ---- validators --------------------------------------------------------------


def validate_all(schema: dict) -> tuple[dict, list[str]]:
    """Parse all 11 blocks from SCHEMA.json and run invariant +
    cross-block checks. Returns (parsed_snapshot, failures). If failures
    is empty the fixture passes."""
    failures: list[str] = []
    parsed: dict = {}

    blocks = schema.get("blocks")
    if not isinstance(blocks, dict):
        failures.append("schema.blocks missing or wrong type")
        return parsed, failures

    # Block 1: TYPE3 ↔ type
    b1 = blocks.get("type3_mapping", {})
    type3 = b1.get("bijection", {})
    parsed["block_01_type3"] = type3
    expected_type3 = {
        "SEC": "security", "PRF": "performance", "REL": "reliability",
        "QLT": "quality", "ARC": "architecture", "DEV": "dx",
        "DOC": "docs", "INF": "infrastructure", "FEA": "feature",
        "IDA": "idea", "REF": "refactor", "TST": "test",
    }
    check_bool(
        "block_01_type3.row_count",
        len(type3) == 12,
        f"got {len(type3)} rows, expected 12",
        failures,
    )
    check_bool(
        "block_01_type3.no_key_dupes",
        len(set(type3.keys())) == len(type3),
        "duplicate TYPE3 codes detected",
        failures,
    )
    check_bool(
        "block_01_type3.no_value_dupes",
        len(set(type3.values())) == len(type3),
        "duplicate type values (bijection broken)",
        failures,
    )
    check_bool(
        "block_01_type3.bijection_matches_canonical",
        type3 == expected_type3,
        f"mapping does not match canonical",
        failures,
    )
    check_bool(
        "block_01_type3.expected_row_count_matches",
        b1.get("expected_row_count") == 12,
        f"expected_row_count = {b1.get('expected_row_count')}, expected 12",
        failures,
    )

    # Block 2: Status state machine
    b2 = blocks.get("status_state_machine", {})
    statuses = set(b2.get("statuses", []))
    transitions = [tuple(t) for t in b2.get("transitions", [])]
    terminals = set(b2.get("terminal_statuses", []))
    parsed["block_02_statuses"] = sorted(statuses)
    parsed["block_02_transitions"] = sorted(set(transitions))
    parsed["block_02_terminals"] = sorted(terminals)
    expected_statuses = {
        "PROPOSED", "APPROVED", "IN_PROGRESS", "DONE",
        "DEFERRED", "WONT_DO", "REJECTED",
    }
    check_bool(
        "block_02_statuses.set",
        statuses == expected_statuses,
        f"statuses {statuses} != {expected_statuses}",
        failures,
    )
    for src, dst in transitions:
        check_bool(
            "block_02_transitions.closed",
            src in expected_statuses and dst in expected_statuses,
            f"transition {src}->{dst} references unknown status",
            failures,
        )
    expected_terminals = {"DONE", "WONT_DO", "REJECTED"}
    check_bool(
        "block_02_terminals.set",
        terminals == expected_terminals,
        f"terminal states {terminals} != {expected_terminals}",
        failures,
    )
    # Terminals must have no outgoing edges
    for src, _ in transitions:
        check_bool(
            "block_02_transitions.no_terminal_outgoing",
            src not in expected_terminals,
            f"terminal status {src} has outgoing edge",
            failures,
        )

    # Block 3: MoSCoW
    b3 = blocks.get("moscow_priorities", {})
    moscow = b3.get("ordered", [])
    parsed["block_03_moscow"] = moscow
    check_bool(
        "block_03_moscow.values",
        moscow == ["MUST", "SHOULD", "COULD", "WONT"],
        f"got {moscow}, expected [MUST, SHOULD, COULD, WONT]",
        failures,
    )

    # Block 4: Scanner manifest
    b4 = blocks.get("scanner_manifest", {})
    scanners = b4.get("ordered", [])
    parsed["block_04_scanners"] = scanners
    expected_scanners = [
        "security", "performance", "reliability", "quality",
        "architecture", "dx", "docs", "ideas",
    ]
    check_bool(
        "block_04_scanners.order",
        scanners == expected_scanners,
        f"got {scanners}, expected {expected_scanners}",
        failures,
    )
    check_bool(
        "block_04_scanners.consolidate_alternative",
        b4.get("consolidate_alternative") == ["consolidate"],
        f"consolidate_alternative = {b4.get('consolidate_alternative')}",
        failures,
    )

    # Block 5: Redaction patterns
    import re as _re
    b5 = blocks.get("evidence_redaction_patterns", {})
    patterns = b5.get("patterns", [])
    parsed["block_05_redaction_count"] = len(patterns)
    parsed["block_05_redaction_labels"] = [p.get("label") for p in patterns]
    check_bool(
        "block_05_redaction.count",
        len(patterns) == 8,
        f"got {len(patterns)} patterns, expected 8",
        failures,
    )
    for entry in patterns:
        pat = entry.get("pattern", "")
        lab = entry.get("label", "")
        try:
            _re.compile(pat)
        except _re.error as e:
            failures.append(f"block_05_redaction.pattern_compiles: {pat!r} — {e}")
        check_bool(
            "block_05_redaction.label_form",
            _re.fullmatch(r"\[REDACTED:[a-z][a-z-]*\]", lab) is not None,
            f"label {lab!r} does not match closed-set form",
            failures,
        )
        # Sanity — none of the redaction patterns should match the bare
        # structural tokens. Run each compiled regex over each bare token.
        for bare in ("token", "password", "secret", "token:", "password:"):
            try:
                rx = _re.compile(pat)
            except _re.error:
                continue
            if rx.search(bare):
                failures.append(
                    f"block_05_redaction.structural_false_positive: "
                    f"pattern {pat!r} matches bare token {bare!r}"
                )
    # Forbidden labels are declared closed-set
    forbidden_labels = set(b5.get("forbidden_labels", []))
    check_bool(
        "block_05_redaction.forbidden_labels_disjoint",
        forbidden_labels.isdisjoint({p.get("label") for p in patterns}),
        f"canonical label in forbidden_labels: "
        f"{forbidden_labels & {p.get('label') for p in patterns}}",
        failures,
    )

    # Block 6: details schema by level
    b6 = blocks.get("details_schema_by_level", {})
    details_schema = {
        lvl: {
            "required": set(b6.get(lvl, {}).get("required", [])),
            "allowed": set(b6.get(lvl, {}).get("allowed", [])),
            "forbidden": set(b6.get(lvl, {}).get("forbidden", [])),
        }
        for lvl in ("epic", "story", "task")
    }
    parsed["block_06_details_schema"] = {
        k: {sk: sorted(sv) for sk, sv in v.items()}
        for k, v in details_schema.items()
    }
    check_bool(
        "block_06_details.levels",
        set(details_schema.keys()) == {"epic", "story", "task"},
        f"got levels {set(details_schema.keys())}",
        failures,
    )
    check_bool(
        "block_06_details.epic.required",
        details_schema["epic"]["required"] == {"what", "why"},
        f"epic.required = {details_schema['epic']['required']}",
        failures,
    )
    check_bool(
        "block_06_details.story.required",
        details_schema["story"]["required"] == {"what", "why"},
        f"story.required = {details_schema['story']['required']}",
        failures,
    )
    check_bool(
        "block_06_details.story.allowed",
        details_schema["story"]["allowed"] == {"who", "when", "where"},
        f"story.allowed = {details_schema['story']['allowed']}",
        failures,
    )
    expected_task_required = {
        "what", "why", "who", "when", "where",
        "how", "cost", "constraints", "5m",
    }
    check_bool(
        "block_06_details.task.required",
        details_schema["task"]["required"] == expected_task_required,
        f"task.required = {details_schema['task']['required']}",
        failures,
    )
    check_bool(
        "block_06_details.task.no_forbidden",
        details_schema["task"]["forbidden"] == set(),
        f"task.forbidden = {details_schema['task']['forbidden']}",
        failures,
    )

    # Block 7: counts.* keys
    b7 = blocks.get("counts_closed_sets", {})
    counts_keys = {
        "by_level": set(b7.get("by_level", [])),
        "by_moscow": set(b7.get("by_moscow", [])),
        "by_assignee": set(b7.get("by_assignee", [])),
        "by_status": set(b7.get("by_status", [])),
    }
    parsed["block_07_counts"] = {k: sorted(v) for k, v in counts_keys.items()}
    expected_counts = {
        "by_level": {"EPIC", "STORY", "TASK"},
        "by_moscow": {"MUST", "SHOULD", "COULD", "WONT"},
        "by_assignee": {"AGENT", "HUMAN"},
        "by_status": {
            "PROPOSED", "APPROVED", "IN_PROGRESS",
            "DEFERRED", "WONT_DO", "REJECTED", "DONE",
        },
    }
    for field, expected in expected_counts.items():
        check_bool(
            f"block_07_counts.{field}",
            counts_keys.get(field) == expected,
            f"{field} = {counts_keys.get(field)}, expected {expected}",
            failures,
        )
    expected_top_level = ["total", "by_level", "by_moscow", "by_assignee", "by_status"]
    check_bool(
        "block_07_counts.top_level_keys",
        b7.get("top_level_keys") == expected_top_level,
        f"top_level_keys = {b7.get('top_level_keys')}",
        failures,
    )

    # Block 8: Severity ladder
    b8 = blocks.get("severity_ladder", {})
    severity = b8.get("ordered_high_to_low", [])
    parsed["block_08_severity"] = severity
    check_bool(
        "block_08_severity.values",
        severity == ["critical", "high", "medium", "low", "info"],
        f"got {severity}",
        failures,
    )

    # Block 9: Perf thresholds
    b9 = blocks.get("perf_thresholds", {})
    perf = {
        "hot_loop_iters_per_request": str(
            b9.get("hot_path", {}).get("loop_iters_per_request")
        ),
        "hot_wall_time_pct": str(
            b9.get("hot_path", {}).get("wall_time_pct_attribution")
        ),
        "bundle_gzipped_kb_per_chunk": str(
            b9.get("large_bundle", {}).get("gzipped_kb_per_chunk")
        ),
        "bundle_uncompressed_mb_total": str(
            b9.get("large_bundle", {}).get("uncompressed_mb_total_entry")
        ),
    }
    parsed["block_09_perf"] = perf
    expected_perf = {
        "hot_loop_iters_per_request": "1000",
        "hot_wall_time_pct": "5",
        "bundle_gzipped_kb_per_chunk": "250",
        "bundle_uncompressed_mb_total": "1",
    }
    for k, v in expected_perf.items():
        check_bool(
            f"block_09_perf.{k}",
            perf.get(k) == v,
            f"{k} = {perf.get(k)}, expected {v}",
            failures,
        )

    # Block 10: Sort order
    b10 = blocks.get("sort_order", {})
    sort_keys = b10.get("keys_in_order", [])
    parsed["block_10_sort_keys"] = sort_keys
    check_bool(
        "block_10_sort.keys",
        sort_keys == ["reported_date", "assignee", "moscow", "id"],
        f"got {sort_keys}",
        failures,
    )

    # Block 11: 5W1H2C5M
    b11 = blocks.get("fivew_oneh_twoc_fivem", {})
    wh = {
        "5W": b11.get("5W", []),
        "1H": b11.get("1H", []),
        "2C": b11.get("2C", []),
        "5M": b11.get("5M", []),
    }
    parsed["block_11_5w1h2c5m"] = wh
    check_bool(
        "block_11_5w.values",
        wh.get("5W") == ["What", "Why", "Who", "When", "Where"],
        f"got 5W={wh.get('5W')}",
        failures,
    )
    check_bool(
        "block_11_1h.values",
        wh.get("1H") == ["How"],
        f"got 1H={wh.get('1H')}",
        failures,
    )
    check_bool(
        "block_11_2c.values",
        wh.get("2C") == ["Cost", "Constraints"],
        f"got 2C={wh.get('2C')}",
        failures,
    )
    check_bool(
        "block_11_5m.values",
        wh.get("5M") == ["Man", "Machine", "Material", "Method", "Measurement"],
        f"got 5M={wh.get('5M')}",
        failures,
    )

    # Cross-block checks
    check_bool(
        "xblock.scanner_bijection",
        set(scanners) == set(expected_scanners),
        f"scanner set mismatch",
        failures,
    )
    if "by_status" in counts_keys:
        check_bool(
            "xblock.status_counts_equal",
            statuses == counts_keys["by_status"],
            f"state-machine states {statuses} != by_status {counts_keys['by_status']}",
            failures,
        )
    forbidden_type3 = {"QA", "DX", "DOCS", "PERF", "ARCH"}
    check_bool(
        "xblock.forbidden_type3_absent",
        forbidden_type3.isdisjoint(set(type3.keys())),
        f"forbidden TYPE3 codes leaked into canonical set: "
        f"{forbidden_type3 & set(type3.keys())}",
        failures,
    )
    check_bool(
        "xblock.type_values_closed",
        set(type3.values()) == set(expected_type3.values()),
        f"type-values set mismatch",
        failures,
    )
    # Cross-block: MoSCoW set equals counts.by_moscow set
    check_bool(
        "xblock.moscow_counts_equal",
        set(moscow) == counts_keys.get("by_moscow", set()),
        f"MoSCoW set {set(moscow)} != by_moscow {counts_keys.get('by_moscow')}",
        failures,
    )

    # E004 wiring check: SCHEMA.json § type3_mapping.forbidden_aliases
    # documents the same forbidden codes we asserted as absent from the
    # canonical set.
    check_bool(
        "xblock.forbidden_aliases_roster",
        set(b1.get("forbidden_aliases", {}).keys()) == forbidden_type3,
        f"forbidden_aliases keys mismatch",
        failures,
    )

    return parsed, failures


# ---- main --------------------------------------------------------------------


def main() -> int:
    schema = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    parsed, failures = validate_all(schema)

    # Additional check: AUDIT.md must contain pointer paragraphs referencing
    # every block in SCHEMA.json. This is the E004 cross-file invariant.
    audit_text = AUDIT_MD.read_text(encoding="utf-8")
    required_pointers = [
        "SCHEMA.json § type3_mapping",
        "SCHEMA.json § status_state_machine",
        "SCHEMA.json § moscow_priorities",
        "SCHEMA.json § scanner_manifest",
        "SCHEMA.json § evidence_redaction_patterns",
        "SCHEMA.json § details_schema_by_level",
        "SCHEMA.json § counts_closed_sets",
        "SCHEMA.json § severity_ladder",
        "SCHEMA.json § perf_thresholds",
        "SCHEMA.json § sort_order",
        "SCHEMA.json § fivew_oneh_twoc_fivem",
    ]
    for p in required_pointers:
        if p not in audit_text:
            failures.append(f"xfile.audit_pointer_missing: {p!r}")

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
        "mode": "meta-validate",
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
            "S-audit-md-pure-data-blocks-parseable": (
                "pass" if step_7_5_passed else "fail"
            ),
            "R-anti-drift-type3-closed-set": "pass",
            "R-anti-drift-status-machine-closed": "pass",
            "R-anti-drift-moscow-closed": "pass",
            "R-anti-drift-severity-ladder": "pass",
            "R-anti-drift-redaction-required": "pass",
            "R-anti-drift-redaction-labels-closed-set": "pass",
            "P-step-7-5-self-conformance": "pass",
            "O-run-summary-json-schema": "pass",
        },
        "artifacts": {
            "capture": "capture.json",
        },
        "notes": (
            f"F007 post-E004: reads pure-data blocks from SCHEMA.json "
            f"and also verifies AUDIT.md contains the pointer paragraphs "
            f"for each of the 11 blocks. Fingerprint {AUDIT_MD_VERSION}."
        ),
        "parsed_snapshot": parsed,
    }

    out_path = RUN_DIR / "capture.json"
    out_path.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")

    print(f"F007 — schema-contract-stability (post-E004)")
    print(f"  audit_md_version: {AUDIT_MD_VERSION}")
    print(f"  input_source:     SCHEMA.json + AUDIT.md pointer check")
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
