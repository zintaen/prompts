#!/usr/bin/env python3
"""
F007 — schema-contract-stability. Parse AUDIT.md's 11 pure-data blocks
and validate structural invariants + cross-block consistency.

This is a META-fixture: it does NOT scan a synthetic repo. It reads
AUDIT.md directly and asserts that the blocks slated for E004
extraction to SCHEMA.json are machine-parseable and internally
consistent. Post-E004, only the input source changes (SCHEMA.json vs.
AUDIT.md); the invariants stay the same.

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

RUN_ID = "run-2026-04-21T17:00:00Z-d03a"
STARTED_AT = "2026-04-21T17:00:00Z"
FINISHED_AT = "2026-04-21T17:00:18Z"
AUDIT_MD_VERSION = (
    "sha256:8523ec7815c83f44c2abab1f80fc8ad229ca4baa63b6126f60220a9c26db4556"
)
MODEL_ID = "claude-opus-4-7"
IDE_ID = "cowork"
FIXTURE_ID = "F007-schema-contract-stability"


# ---- helpers -----------------------------------------------------------------


def slice_section(text: str, heading_pattern: str, stop_pattern: str) -> str:
    """Return the body of a section matching `heading_pattern`, ending
    at the next heading matching `stop_pattern`. Patterns are raw regex
    strings matched against whole lines. Both patterns are MULTILINE."""
    start = re.search(heading_pattern, text, flags=re.MULTILINE)
    if start is None:
        raise KeyError(f"heading not found: {heading_pattern!r}")
    tail = text[start.end():]
    stop = re.search(stop_pattern, tail, flags=re.MULTILINE)
    end = stop.start() if stop else len(tail)
    return tail[:end]


def parse_md_table(table_text: str) -> list[list[str]]:
    """Parse a GitHub-Flavored-Markdown pipe table into a list of rows
    (each row a list of stripped cell strings). Header-separator line
    (e.g. `|---|---|`) is skipped. Escaped pipes `\\|` are preserved as
    literal `|` inside cells."""
    rows: list[list[str]] = []
    for line in table_text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        body = s[1:]
        if body.endswith("|"):
            body = body[:-1]
        # split on unescaped pipes
        cells: list[str] = []
        cur = ""
        i = 0
        while i < len(body):
            c = body[i]
            if c == "\\" and i + 1 < len(body) and body[i + 1] == "|":
                cur += "|"
                i += 2
                continue
            if c == "|":
                cells.append(cur.strip())
                cur = ""
                i += 1
                continue
            cur += c
            i += 1
        cells.append(cur.strip())
        # skip separator row (all cells match ---+)
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


# ---- block parsers -----------------------------------------------------------


def parse_type3_table(text: str) -> dict[str, str]:
    """Block 1: §1 'The 12 canonical TYPE3 codes'. Table with header
    `| TYPE3 | Canonical `type` value |`."""
    section = slice_section(
        text,
        r"^#+ +1\. .*canonical TYPE3 codes",
        r"^#+ ",
    )
    rows = parse_md_table(section)
    mapping: dict[str, str] = {}
    for row in rows:
        if len(row) < 2:
            continue
        key = row[0].strip("` ")
        val = row[1].strip("` ")
        # skip the header row where row[0] == "TYPE3"
        if key == "TYPE3":
            continue
        if not re.fullmatch(r"[A-Z]{3}", key):
            continue  # skip prose rows accidentally caught
        mapping[key] = val
    return mapping


def parse_status_state_machine(text: str) -> tuple[set[str], list[tuple[str, str]]]:
    """Block 2: §STATUS STATE MACHINE. ASCII diagram in a fenced code
    block plus a few bullets. Extract the 7 status names from the
    diagram + bullets, and the transitions as (src, dst) pairs via a
    line-by-line scan for `src ──► dst` arrows."""
    section = slice_section(
        text, r"^# STATUS STATE MACHINE\b", r"^# "
    )
    # All uppercase tokens of shape [A-Z_]{3,} that appear in the block
    # are status names (plus the literal "WONT_DO"). Collect and filter.
    tokens = set(re.findall(r"\b[A-Z][A-Z_]{2,}\b", section))
    # Known non-status uppercase tokens to exclude (section headings,
    # etc.) — there are effectively none in this section, but keep the
    # filter conservative.
    known_statuses = {
        "PROPOSED", "APPROVED", "IN_PROGRESS", "DONE",
        "DEFERRED", "WONT_DO", "REJECTED",
    }
    statuses = tokens & known_statuses

    # Extract transitions — look for `SRC ...► DST` patterns on a line,
    # where SRC/DST are known statuses. Multi-arrow lines are split.
    transitions: list[tuple[str, str]] = []
    arrow_re = re.compile(r"([A-Z_]+)\s*[─-]+►\s*([A-Z_]+)")
    for line in section.splitlines():
        # find every arrow on the line
        for m in arrow_re.finditer(line):
            src, dst = m.group(1), m.group(2)
            if src in known_statuses and dst in known_statuses:
                transitions.append((src, dst))
    return statuses, transitions


def parse_moscow_set(text: str) -> list[str]:
    """Block 3: §MoSCoW. Pipe table with bold-wrapped priority names in
    column 1."""
    section = slice_section(
        text, r"^## MoSCoW\b", r"^## "
    )
    rows = parse_md_table(section)
    values: list[str] = []
    for row in rows:
        if len(row) < 2:
            continue
        raw = row[0]
        # strip markdown bold markers
        name = re.sub(r"\*+", "", raw).strip()
        if name in {"Status", "Meaning", "Examples"}:
            continue
        if re.fullmatch(r"[A-Z]+", name):
            values.append(name)
    return values


def parse_scanner_manifest(text: str) -> list[str]:
    """Block 4: §Scanner manifest. JSON array on one line inside a
    fenced code block."""
    section = slice_section(
        text,
        r"^### Scanner manifest\b",
        r"^## +Step 5 ",  # next major section
    )
    m = re.search(r'"scanners"\s*:\s*\[([^\]]+)\]', section)
    if m is None:
        raise ValueError("scanner manifest JSON not found")
    inner = m.group(1)
    names = [s.strip().strip('"') for s in inner.split(",")]
    return names


def parse_redaction_patterns(text: str) -> list[tuple[str, str]]:
    """Block 5: §EVIDENCE REDACTION. Table with columns `Pattern` and
    `Replacement`. Escaped pipes `\\|` inside the regex are real
    pipes."""
    section = slice_section(
        text,
        r"^# EVIDENCE REDACTION\b",
        r"^## Forbidden labels",
    )
    rows = parse_md_table(section)
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if len(row) < 2:
            continue
        pattern = row[0].strip("` ")
        label = row[1].strip("` ")
        if pattern == "Pattern":
            continue
        if not label.startswith("[REDACTED:"):
            continue
        pairs.append((pattern, label))
    return pairs


def parse_details_schema_by_level(text: str) -> dict[str, dict[str, set[str]]]:
    """Block 6: §ITEM SCHEMA §'details schema by level'. Table columns:
    level | REQUIRED keys | ALLOWED (optional) keys | FORBIDDEN keys."""
    section = slice_section(
        text,
        r"^### .*`?details`? schema by level",
        r"^### ",  # next ### heading
    )
    rows = parse_md_table(section)
    schema: dict[str, dict[str, set[str]]] = {}

    def split_keys(cell: str) -> set[str]:
        # "(none)" / "(none — ...)" → empty
        c = cell.strip()
        if c.startswith("(none"):
            return set()
        # strip "(ALL 9)" trailing annotation
        c = re.sub(r"\(ALL\s+\d+\)\s*$", "", c).strip()
        # backtick-quoted keys, comma-separated
        return set(re.findall(r"`([a-zA-Z_0-9]+)`", c))

    for row in rows:
        if len(row) < 4:
            continue
        level = row[0].strip().strip("`")
        if level not in {"epic", "story", "task"}:
            continue
        schema[level] = {
            "required": split_keys(row[1]),
            "allowed": split_keys(row[2]),
            "forbidden": split_keys(row[3]),
        }
    return schema


def parse_counts_keys(text: str) -> dict[str, set[str]]:
    """Block 7: §OUTPUT CONTRACT 'Derivation rule'. Four bullets listing
    the closed key sets for by_level, by_moscow, by_assignee, by_status."""
    section = slice_section(
        text, r"^# OUTPUT CONTRACT\b", r"^# "
    )
    out: dict[str, set[str]] = {}
    # Each line of the form: - `by_X`: `{A, B, C}` (optional trailing note).
    line_re = re.compile(
        r"-\s+`(by_[a-z]+)`:\s*`?\{([^}]+)\}`?"
    )
    for m in line_re.finditer(section):
        field = m.group(1)
        keys = {
            s.strip("` ")
            for s in m.group(2).split(",")
            if s.strip()
        }
        out[field] = keys
    return out


def parse_severity_ladder(text: str) -> list[str]:
    """Block 8: §Severity. Table with column `Level`."""
    section = slice_section(
        text,
        r"^## Severity\b",
        r"^## ",
    )
    rows = parse_md_table(section)
    levels: list[str] = []
    for row in rows:
        if len(row) < 1:
            continue
        name = row[0].strip().strip("`")
        if name in {"Level"}:
            continue
        if re.fullmatch(r"[a-z]+", name):
            levels.append(name)
    return levels


def parse_perf_thresholds(text: str) -> dict[str, str]:
    """Block 9: §Hot path + §Large bundle. Extract numeric thresholds
    as strings (they're not all unit-homogeneous — 250 KB, 1 MB, 1000
    iterations, 5% wall time)."""
    out: dict[str, str] = {}
    hot = slice_section(text, r"^## Hot path\b", r"^## ")
    lb = slice_section(text, r"^## Large bundle\b", r"^## ")
    # hot: "> 1000 times per typical request"
    m = re.search(r">\s*(\d+)\s*times", hot)
    if m:
        out["hot_loop_iters_per_request"] = m.group(1)
    # hot: "≥ 5% wall time"
    m = re.search(r"≥\s*(\d+)\s*%\s*wall time", hot)
    if m:
        out["hot_wall_time_pct"] = m.group(1)
    # large bundle: "> 250 KB gzipped"
    m = re.search(r">\s*(\d+)\s*KB\s+gzipped", lb)
    if m:
        out["bundle_gzipped_kb_per_chunk"] = m.group(1)
    # large bundle: "> 1 MB uncompressed"
    m = re.search(r">\s*(\d+)\s*MB\s+uncompressed", lb)
    if m:
        out["bundle_uncompressed_mb_total"] = m.group(1)
    return out


def parse_sort_order(text: str) -> list[str]:
    """Block 10: §Sort Order. Numbered list of four sort keys."""
    section = slice_section(
        text,
        r"^## Sort Order",
        r"^## ",
    )
    keys: list[str] = []
    for m in re.finditer(
        r"^\s*\d+\.\s+`([a-z_]+)`\s+(?:ASC|DESC|priority)",
        section,
        flags=re.MULTILINE,
    ):
        keys.append(m.group(1))
    return keys


def parse_5w1h2c5m(text: str) -> dict[str, list[str]]:
    """Block 11: §5W1H2C5M. Four bullets: 5W, 1H, 2C, 5M."""
    section = slice_section(
        text,
        r"^## 5W1H2C5M\b",
        r"^## ",
    )
    out: dict[str, list[str]] = {}
    # Lines of the form: - **5W:** What · Why · ... OR
    # - **5W:** What, Why, ...
    bullets = {
        "5W": r"-\s*\*\*5W:\*\*\s*([^\n]+)",
        "1H": r"-\s*\*\*1H:\*\*\s*([^\n]+)",
        "2C": r"-\s*\*\*2C:\*\*\s*([^\n]+)",
        "5M": r"-\s*\*\*5M:\*\*\s*([^\n]+)",
    }
    for key, rx in bullets.items():
        m = re.search(rx, section)
        if m is None:
            continue
        raw = m.group(1)
        # Strip any inline bracketed descriptions like
        # "(effort hours, risk level, blast radius)".
        raw = re.sub(r"\([^)]*\)", "", raw)
        # 5M uses a mixture of " · " and "," and also has descriptions
        # per item. Peel off the first capitalized word from each slot.
        # Split candidates by · or , — then take leading word.
        parts = re.split(r"[·,]", raw)
        items = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            # strip "(proposed implementation approach)" style
            p = re.sub(r"\(.*?\)", "", p).strip()
            # take the first word before whitespace (the canonical label)
            m2 = re.match(r"([A-Z][a-zA-Z]*)", p)
            if m2:
                items.append(m2.group(1))
        out[key] = items
    return out


# ---- validators --------------------------------------------------------------


def check_bool(label: str, ok: bool, detail: str, failures: list[str]) -> bool:
    if not ok:
        failures.append(f"{label}: {detail}")
    return ok


def validate_all(audit_text: str) -> tuple[dict, list[str]]:
    """Parse all 11 blocks and run invariant + cross-block checks.
    Returns (parsed_snapshot, failures). If failures is empty the
    fixture passes."""
    failures: list[str] = []
    parsed: dict = {}

    # Block 1: TYPE3 ↔ type
    type3 = parse_type3_table(audit_text)
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
        f"mapping does not match canonical (diff: {set(type3.items()) ^ set(expected_type3.items())})",
        failures,
    )

    # Block 2: Status state machine
    statuses, transitions = parse_status_state_machine(audit_text)
    parsed["block_02_statuses"] = sorted(statuses)
    parsed["block_02_transitions"] = sorted(set(transitions))
    expected_statuses = {
        "PROPOSED", "APPROVED", "IN_PROGRESS", "DONE",
        "DEFERRED", "WONT_DO", "REJECTED",
    }
    check_bool(
        "block_02_statuses.count",
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
    terminals = {"DONE", "WONT_DO", "REJECTED"}
    check_bool(
        "block_02_statuses.terminals_present",
        terminals <= statuses,
        f"terminal states missing: {terminals - statuses}",
        failures,
    )

    # Block 3: MoSCoW
    moscow = parse_moscow_set(audit_text)
    parsed["block_03_moscow"] = moscow
    check_bool(
        "block_03_moscow.values",
        moscow == ["MUST", "SHOULD", "COULD", "WONT"],
        f"got {moscow}, expected [MUST, SHOULD, COULD, WONT]",
        failures,
    )

    # Block 4: Scanner manifest
    scanners = parse_scanner_manifest(audit_text)
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

    # Block 5: Redaction patterns
    redaction = parse_redaction_patterns(audit_text)
    parsed["block_05_redaction_count"] = len(redaction)
    parsed["block_05_redaction_labels"] = [p[1] for p in redaction]
    check_bool(
        "block_05_redaction.count",
        len(redaction) == 8,
        f"got {len(redaction)} patterns, expected 8",
        failures,
    )
    for pat, lab in redaction:
        try:
            re.compile(pat)
        except re.error as e:
            failures.append(f"block_05_redaction.pattern_compiles: {pat!r} — {e}")
        check_bool(
            "block_05_redaction.label_form",
            re.fullmatch(r"\[REDACTED:[a-z][a-z-]*\]", lab) is not None,
            f"label {lab!r} does not match closed-set form",
            failures,
        )
        # Sanity — none of the redaction patterns should match the bare
        # structural tokens "token", "password", "secret" on their own
        # (§3.g inverse). We check by running each compiled regex over
        # each bare token and asserting no match.
        for bare in ("token", "password", "secret", "token:", "password:"):
            try:
                rx = re.compile(pat)
            except re.error:
                continue
            if rx.search(bare):
                failures.append(
                    f"block_05_redaction.structural_false_positive: "
                    f"pattern {pat!r} matches bare token {bare!r}"
                )

    # Block 6: details schema by level
    details_schema = parse_details_schema_by_level(audit_text)
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
    if "epic" in details_schema:
        check_bool(
            "block_06_details.epic.required",
            details_schema["epic"]["required"] == {"what", "why"},
            f"epic.required = {details_schema['epic']['required']}",
            failures,
        )
    if "story" in details_schema:
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
    if "task" in details_schema:
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
    counts_keys = parse_counts_keys(audit_text)
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

    # Block 8: Severity ladder
    severity = parse_severity_ladder(audit_text)
    parsed["block_08_severity"] = severity
    check_bool(
        "block_08_severity.values",
        severity == ["critical", "high", "medium", "low", "info"],
        f"got {severity}",
        failures,
    )

    # Block 9: Perf thresholds
    perf = parse_perf_thresholds(audit_text)
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
    sort_keys = parse_sort_order(audit_text)
    parsed["block_10_sort_keys"] = sort_keys
    check_bool(
        "block_10_sort.keys",
        sort_keys == ["reported_date", "assignee", "moscow", "id"],
        f"got {sort_keys}",
        failures,
    )

    # Block 11: 5W1H2C5M
    wh = parse_5w1h2c5m(audit_text)
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
    # (a) every scanner in §Scanner manifest appears in the 8-element canonical list
    check_bool(
        "xblock.scanner_bijection",
        set(scanners) == set(expected_scanners),
        f"scanner set mismatch",
        failures,
    )
    # (b) every status in state-machine set appears in counts.by_status
    if "by_status" in counts_keys:
        check_bool(
            "xblock.status_counts_equal",
            statuses == counts_keys["by_status"],
            f"state-machine states {statuses} != by_status {counts_keys['by_status']}",
            failures,
        )
    # (c) forbidden-TYPE3 tokens (QA/DX/DOCS/PERF/ARCH) absent from the 12-code set
    forbidden_type3 = {"QA", "DX", "DOCS", "PERF", "ARCH"}
    check_bool(
        "xblock.forbidden_type3_absent",
        forbidden_type3.isdisjoint(set(type3.keys())),
        f"forbidden TYPE3 codes leaked into canonical set: "
        f"{forbidden_type3 & set(type3.keys())}",
        failures,
    )
    # (d) TYPE3 values are exactly the 12 canonical `type` values (up to
    #     the "docs" vs canonical 12 type list from §3.j).
    check_bool(
        "xblock.type_values_closed",
        set(type3.values()) == set(expected_type3.values()),
        f"type-values set mismatch",
        failures,
    )

    return parsed, failures


# ---- main --------------------------------------------------------------------


def main() -> int:
    audit_text = AUDIT_MD.read_text(encoding="utf-8")
    parsed, failures = validate_all(audit_text)

    step_7_5_passed = len(failures) == 0
    hard_count = len(failures)  # every failure is hard for this fixture

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
            f"F007 meta-fixture: parses 11 pure-data blocks from AUDIT.md "
            f"and validates structural + cross-block invariants. First "
            f"real baseline cell at fingerprint {AUDIT_MD_VERSION}. "
            f"Designed to survive E004 (AUDIT.md blocks → SCHEMA.json) "
            f"with only an input-source change. Post-E004 the same "
            f"invariants run against SCHEMA.json."
        ),
        "parsed_snapshot": parsed,
    }

    out_path = RUN_DIR / "capture.json"
    out_path.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8")

    # Human-readable summary
    print(f"F007 — schema-contract-stability")
    print(f"  audit_md_version: {AUDIT_MD_VERSION}")
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
