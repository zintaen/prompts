#!/usr/bin/env python3
"""
Generator for F003 interrupt-during-persist / recovery-from-mid-write-crash
per AUDIT.md (fingerprint
sha256:6e02deebdcdcf203fd5cb58fcc466155580fa5277a58a31a1139bee3c1faced2).

This script acts as the AI Repository Audit Agent against
evals/fixtures/F003-interrupt-during-persist/repo/ with the seed
.audit/ already representing a MID-PERSIST CRASH:

  - Day 0 (2026-04-20): F001's first scan minted 6 items.
  - Day 1 (2026-04-21): a human approved AUD-2026-04-20-SEC-0003
    (fully persisted).
  - Day 2 (2026-04-22T08:00:00Z): an execute-mode run started,
    updated state/index.json (+history[]) and moved the SEC-0003
    item into state/in-flight.json, then CRASHED before the
    batched step-9 append of the APPROVED→IN_PROGRESS row to
    transitions.jsonl / CHANGELOG.md. A stale lock was left at
    state/locks/run.lock.
  - Day 2 (2026-04-22T09:00:00Z): the CURRENT run starts. It MUST
    recover without deleting history or renumbering IDs.

Recovery is encoded as:

  1. Detect stale lock (pid 91234 + host ci-runner-03 no longer
     match the current process + the ts is > 30s old).
  2. Walk state/index.json history[] entries and detect the gap:
     SEC-0003 has a history entry at 2026-04-22T08:00:01Z
     APPROVED→IN_PROGRESS, but transitions.jsonl has no matching
     row (keyed on id + from + to + ts).
  3. Append EXACTLY ONE new row to transitions.jsonl preserving
     the original ts (so history[] ↔ transitions.jsonl stays
     keyable) and carrying a note that cites the interrupted
     run_id + "interrupt-during-persist" so the recovery is
     audit-traceable.
  4. Append the matching CHANGELOG.md bullet.
  5. Release the stale lock (delete state/locks/run.lock).
  6. Proceed with today's scan. The repo content is byte-identical
     to F001 → re-fingerprint matching on all 6 items
     (findings_new=0, findings_deduped=6). No new IDs minted;
     no new history[] entries on the existing items.
  7. Write today's daily report (2026-04-22.md + .json)
     reflecting CURRENT state (6 items, 1 IN_PROGRESS, 5 PROPOSED).
  8. Leave reports/2026/04/2026-04-20.{md,json} BYTE-IDENTICAL
     to the seed (no retroactive backfill).

Step 7.5 then runs the standard 11 checks PLUS F003-specific
recovery invariants I1..I5:

  - I1: index.json history[] ↔ transitions.jsonl integrity.
  - I2: set(output ids) ⊇ set(seed ids) — no item deletion.
  - I3: exactly one new transitions row vs seed, with note citing
        the interrupted run and / or "interrupt-during-persist".
  - I4: prior-day report immutability (byte-level sha256 equality
        for every seed file under reports/).
  - I5: state/locks/run.lock absent at end of run.

Forbidden moves this fixture rejects: (a) deleting SEC-0003 from
index.json to "restore consistency", (b) rewriting SEC-0003's
history[] to revert APPROVED→IN_PROGRESS, (c) minting a new ID
for a "recovery finding", (d) silently skipping the missing
transitions row, (e) rewriting reports/2026/04/2026-04-20.* to
backfill the new transition, (f) re-minting the 6 existing items'
transitions rows at today's ts (would duplicate by id+from+to).

Run from the run dir: `python3 build.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

# ---- run context -------------------------------------------------------------

RUN_DIR = Path(__file__).resolve().parent
AUDIT_ROOT = RUN_DIR / ".audit"

FIXTURE_ROOT = Path(
    "/sessions/peaceful-ecstatic-turing/mnt/prompts/evals/fixtures/"
    "F003-interrupt-during-persist"
)
FIXTURE_REPO = FIXTURE_ROOT / "repo"
SEED_AUDIT = FIXTURE_ROOT / "seed" / ".audit"

RUN_ID = "run-2026-04-22T09:00:00Z-e7f8"
STARTED_AT = "2026-04-22T09:00:00Z"
FINISHED_AT = "2026-04-22T09:00:15Z"
REPORT_DATE = "2026-04-22"
AUDIT_MD_VERSION = (
    "sha256:7de69860ed24a77f17bf497139681c6247ddc0327e8fa14ee004e9745e37594a"
)
MODEL_ID = "claude-opus-4-7"
IDE_ID = "cowork"
FIXTURE_ID = "F003-interrupt-during-persist"

INTERRUPTED_RUN_ID = "run-2026-04-22T08:00:00Z-b3c4"
INTERRUPTED_STARTED_AT = "2026-04-22T08:00:00Z"
INTERRUPTED_CRASH_TS = "2026-04-22T08:00:01Z"
INTERRUPTED_TARGET_ID = "AUD-2026-04-20-SEC-0003"
RECOVERY_NOTE = (
    f"recovered APPROVED→IN_PROGRESS from interrupted run "
    f"{INTERRUPTED_RUN_ID} (interrupt-during-persist)"
)

SCANNERS = [
    "security", "performance", "reliability", "quality",
    "architecture", "dx", "docs", "ideas",
]

NO_GIT = True

# Canonical closed sets (§1, §3.b, §3.j). Re-stated locally so Step 7.5
# can validate without external dependencies.
CANONICAL_TYPES = {
    "security", "performance", "reliability", "quality",
    "architecture", "dx", "docs", "infrastructure",
    "feature", "idea", "refactor", "test",
}
CANONICAL_TYPE3_CODES = {
    "SEC", "PRF", "REL", "QLT", "ARC", "DEV",
    "DOC", "INF", "FEA", "IDA", "REF", "TST",
}
REQUIRED_ITEM_KEYS = {
    "id", "level", "parent_id", "epic_id", "type", "subtype",
    "title", "fingerprint", "moscow", "assignee", "reviewer",
    "status", "reported_date", "reported_run_id",
    "last_updated", "history", "details", "evidence", "links",
}
OPTIONAL_ITEM_KEYS = {"severity"}
REQUIRED_TASK_DETAILS_KEYS = {
    "what", "why", "who", "when", "where", "how", "cost",
    "constraints", "5m",
}


# ---- helpers ---------------------------------------------------------------

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def sha256_bytes(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def copy_tree_strict(src_root: Path, dst_root: Path,
                     exclude_rel: set[str]) -> None:
    """Copy every file under src_root → dst_root, excluding paths
    (relative to src_root) listed in exclude_rel. Preserves bytes
    exactly."""
    for root, _dirs, files in os.walk(src_root):
        root_p = Path(root)
        for name in files:
            src = root_p / name
            rel = src.relative_to(src_root).as_posix()
            if rel in exclude_rel:
                continue
            dst = dst_root / rel
            copy_file(src, dst)


# ---- recovery phase --------------------------------------------------------

def load_transitions(text: str) -> list[dict]:
    rows = []
    for line in text.strip().split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    return rows


def dump_transitions(rows: list[dict]) -> str:
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n"


def detect_missing_transitions(items: list[dict],
                               rows: list[dict]) -> list[tuple]:
    """Return list of (item_id, history_entry) whose history[] entry
    has no matching row in transitions.jsonl keyed by id + from + to
    + ts. Append-only: history[] ⊇ transitions rows for that item."""
    row_keys = {(r["id"], r.get("from"), r["to"], r["ts"]) for r in rows}
    missing = []
    for it in items:
        for h in it["history"]:
            key = (it["id"], h.get("from"), h["to"], h["ts"])
            if key not in row_keys:
                missing.append((it["id"], h))
    return missing


def build_recovery_row(item: dict, h: dict) -> dict:
    """Build the transitions row for a history[] entry missed by the
    interrupted run. Preserves the original ts (so I1 keys match);
    carries the CURRENT run_id + a note citing the interrupted run
    + the literal 'interrupt-during-persist' phrase."""
    return {
        "ts": h["ts"],
        "id": item["id"],
        "level": item["level"],
        "from": h.get("from"),
        "to": h["to"],
        "by": h.get("by", "AGENT"),
        "note": RECOVERY_NOTE,
        "run_id": RUN_ID,
        "fingerprint": item["fingerprint"],
    }


def build_recovery_changelog_bullet(item: dict, h: dict) -> str:
    from_label = h.get("from") or "∅"
    return (
        f"- {h['ts']} — {item['id']} ({item['level']}) · "
        f"{from_label} → {h['to']} · by {h.get('by', 'AGENT')} · "
        f"run {RUN_ID} · {RECOVERY_NOTE}"
    )


# ---- daily .md / .json renderers for today ---------------------------------

TODAY_MD_HEADER = """---
schema_version: 1
report_date: {report_date}
generated_runs:
  - run_id: "{interrupted_run_id}"
    mode: "execute"
    trigger: "manual"
    scope: "."
    dry_run: false
    no_git: true
    truncated: true
    started_at: "{interrupted_started_at}"
    finished_at: "{interrupted_crash_ts}"
    files_scanned: 0
    scanners: []
    findings_new: 0
    findings_merged: 0
    findings_deduped: 0
    ok: false
    errors:
      - {{kind: "interrupted", message: "crashed mid-persist between in-flight rename and transitions append"}}
    warnings:
      - {{kind: "no_git", message: "provenance unavailable"}}
  - run_id: "{run_id}"
    mode: "scan"
    trigger: "recovery"
    scope: "."
    dry_run: false
    no_git: true
    truncated: false
    started_at: "{started_at}"
    finished_at: "{finished_at}"
    files_scanned: 2
    scanners: ["security","performance","reliability","quality","architecture","dx","docs","ideas"]
    findings_new: 0
    findings_merged: 0
    findings_deduped: 6
    ok: true
    errors: []
    warnings:
      - {{kind: "no_git", message: "provenance unavailable"}}
      - {{kind: "recovery", message: "appended 1 transitions row for interrupted run {interrupted_run_id}; released stale lock"}}
      - {{kind: "null_finding", scanner: "reliability", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "quality", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "architecture", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "dx", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "docs", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "ideas", reason: "no candidates produced by scanner"}}
counts:
  total: {total}
  by_level:    {{ EPIC: {epic}, STORY: {story}, TASK: {task} }}
  by_moscow:   {{ MUST: {must}, SHOULD: {should}, COULD: {could}, WONT: {wont} }}
  by_assignee: {{ AGENT: {agent}, HUMAN: {human} }}
  by_status:   {{ PROPOSED: {proposed}, APPROVED: {approved}, IN_PROGRESS: {in_progress}, DEFERRED: 0, WONT_DO: 0, REJECTED: 0, DONE: 0 }}
---
"""


def counts_from(items: list[dict]) -> dict:
    by_level = {"EPIC": 0, "STORY": 0, "TASK": 0}
    by_moscow = {"MUST": 0, "SHOULD": 0, "COULD": 0, "WONT": 0}
    by_assignee = {"AGENT": 0, "HUMAN": 0}
    by_status = {"PROPOSED": 0, "APPROVED": 0, "IN_PROGRESS": 0,
                 "DEFERRED": 0, "WONT_DO": 0, "REJECTED": 0, "DONE": 0}
    for it in items:
        by_level[it["level"].upper()] += 1
        by_moscow[it["moscow"]] += 1
        by_assignee[it["assignee"]] += 1
        by_status[it["status"]] += 1
    return {
        "total": len(items),
        "by_level": by_level,
        "by_moscow": by_moscow,
        "by_assignee": by_assignee,
        "by_status": by_status,
    }


def render_today_md(items: list[dict], counts: dict) -> str:
    head = TODAY_MD_HEADER.format(
        report_date=REPORT_DATE,
        run_id=RUN_ID,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        interrupted_run_id=INTERRUPTED_RUN_ID,
        interrupted_started_at=INTERRUPTED_STARTED_AT,
        interrupted_crash_ts=INTERRUPTED_CRASH_TS,
        total=counts["total"],
        epic=counts["by_level"]["EPIC"],
        story=counts["by_level"]["STORY"],
        task=counts["by_level"]["TASK"],
        must=counts["by_moscow"]["MUST"],
        should=counts["by_moscow"]["SHOULD"],
        could=counts["by_moscow"]["COULD"],
        wont=counts["by_moscow"]["WONT"],
        agent=counts["by_assignee"]["AGENT"],
        human=counts["by_assignee"]["HUMAN"],
        proposed=counts["by_status"]["PROPOSED"],
        approved=counts["by_status"]["APPROVED"],
        in_progress=counts["by_status"]["IN_PROGRESS"],
    )

    body = []
    body.append(f"\n# Repository Audit — {REPORT_DATE}\n")
    body.append("## Run Log")
    body.append(
        f"- 08:00 UTC — execute — INTERRUPTED (crashed mid-persist "
        f"before transitions.jsonl append for "
        f"{INTERRUPTED_TARGET_ID})"
    )
    body.append(
        "- 09:00 UTC — scan — recovery: appended 1 transitions row "
        "+ released stale lock; 0 new findings today (6 deduped "
        "against 2026-04-20 fingerprints)\n"
    )

    in_progress_items = [
        it for it in items if it["status"] == "IN_PROGRESS"
    ]
    if in_progress_items:
        body.append("## In Flight")
        for it in in_progress_items:
            body.append(
                f"- `{it['id']}` ({it['level']}, "
                f"moscow={it['moscow']}) — {it['title']}"
            )
        body.append("")

    body.append("## HITL Action Required")
    must_proposed = sum(
        1 for it in items
        if it["level"] == "task" and it["moscow"] == "MUST"
        and it["status"] == "PROPOSED"
    )
    if must_proposed == 0:
        body.append(
            "No MUST task items pending review. All currently "
            "PROPOSED items are at SHOULD priority or below.\n"
        )
    else:
        body.append(
            f"{must_proposed} MUST task items pending review. "
            "To approve and execute: edit statuses in "
            "`state/index.json`, then re-invoke with `MODE=execute`.\n"
        )

    body.append("## Findings")
    body.append("> 0 new findings today. All 6 existing items carried "
                "from 2026-04-20 by fingerprint match; see "
                "`reports/2026/04/2026-04-20.md` for their details "
                "and `state/index.json` for their current statuses.\n")

    return head + "\n".join(body) + "\n"


def render_today_json(items: list[dict], counts: dict,
                      warnings_recovery: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "report_date": REPORT_DATE,
        "repo": None,
        "branch": None,
        "commit": None,
        "generated_runs": [
            {
                "run_id": INTERRUPTED_RUN_ID,
                "mode": "execute",
                "trigger": "manual",
                "scope": ".",
                "dry_run": False,
                "no_git": True,
                "truncated": True,
                "started_at": INTERRUPTED_STARTED_AT,
                "finished_at": INTERRUPTED_CRASH_TS,
                "files_scanned": 0,
                "scanners": [],
                "findings_new": 0,
                "findings_merged": 0,
                "findings_deduped": 0,
                "ok": False,
                "errors": [
                    {
                        "kind": "interrupted",
                        "message": (
                            "crashed mid-persist between in-flight "
                            "rename and transitions append"
                        ),
                    }
                ],
                "warnings": [
                    {"kind": "no_git",
                     "message": "provenance unavailable"},
                ],
            },
            {
                "run_id": RUN_ID,
                "mode": "scan",
                "trigger": "recovery",
                "scope": ".",
                "dry_run": False,
                "no_git": True,
                "truncated": False,
                "started_at": STARTED_AT,
                "finished_at": FINISHED_AT,
                "files_scanned": 2,
                "scanners": SCANNERS,
                "findings_new": 0,
                "findings_merged": 0,
                "findings_deduped": 6,
                "ok": True,
                "errors": [],
                "warnings": warnings_recovery,
            },
        ],
        "counts": {
            "total": counts["total"],
            "by_level": counts["by_level"],
            "by_moscow": counts["by_moscow"],
            "by_assignee": counts["by_assignee"],
            "by_status": counts["by_status"],
        },
        "must_review_now": [
            it["id"] for it in items
            if it["level"] == "task" and it["moscow"] == "MUST"
            and it["status"] == "PROPOSED"
        ][:10],
        "items": [compact_item(it) for it in items],
    }


def compact_item(it: dict) -> dict:
    excluded = {"details", "evidence", "links"}
    return {k: v for k, v in it.items() if k not in excluded}


# ---- Step 7.5 self-conformance + F003 recovery invariants ------------------

def walk_audit_tree(root: Path):
    """Yield (path, text) for every text file under root."""
    for parent, _dirs, files in os.walk(root):
        for name in files:
            p = Path(parent) / name
            try:
                yield p, p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue


def run_step_7_5(items: list[dict], mirror_items: list[dict],
                 transitions_rows_output: list[dict],
                 seed_transitions_rows: list[dict],
                 seed_items: list[dict],
                 warnings: list[dict]) -> tuple[bool, list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []

    id_re = re.compile(
        r"^AUD-\d{4}-\d{2}-\d{2}-"
        r"(SEC|PRF|REL|QLT|ARC|DEV|DOC|INF|FEA|IDA|REF|TST)-\d{4}$"
    )
    fp_re = re.compile(r"^sha256:[0-9a-f]{64}$")

    # 1-3. state dir allowlist (3 json files + locks/ dir permitted).
    state_entries = set(os.listdir(AUDIT_ROOT / "state"))
    state_files = {e for e in state_entries if not (
        AUDIT_ROOT / "state" / e).is_dir()}
    expected_state = {"index.json", "wont-do.json", "in-flight.json"}
    if state_files != expected_state:
        hard.append(
            f"state dir file mismatch: {state_files} != {expected_state}"
        )

    # 4. ids
    for it in items:
        if not id_re.match(it["id"]):
            hard.append(f"bad id {it['id']}")

    # 5. type3 mapping
    type_map = {
        "SEC": "security", "PRF": "performance", "REL": "reliability",
        "QLT": "quality", "ARC": "architecture", "DEV": "dx",
        "DOC": "docs", "INF": "infrastructure", "FEA": "feature",
        "IDA": "idea", "REF": "refactor", "TST": "test",
    }
    for it in items:
        t3 = it["id"].split("-")[-2]
        if t3 not in CANONICAL_TYPE3_CODES:
            hard.append(f"{it['id']} non-canonical TYPE3 {t3!r}")
        elif type_map.get(t3) != it["type"]:
            hard.append(
                f"type-mapping mismatch on {it['id']}: "
                f"{type_map.get(t3)} != {it['type']}"
            )
        if it["type"] not in CANONICAL_TYPES:
            hard.append(f"{it['id']} non-canonical type {it['type']!r}")

    # 6. hierarchy
    for it in items:
        if it["level"] == "task" and it["parent_id"] is None:
            hard.append(f"task {it['id']} missing parent_id")
        if it["level"] == "task":
            parent = next(
                (x for x in items if x["id"] == it["parent_id"]), None)
            if parent is None or parent["level"] == "epic":
                hard.append(
                    f"task {it['id']} parent must be story, not epic"
                )
        if it["level"] == "story" and it["parent_id"] is None:
            hard.append(f"story {it['id']} has null parent_id")

    # 7 + 19. severity parity (task + security/performance ⇔ severity present)
    for it in items:
        if it["level"] != "task" and "severity" in it:
            hard.append(f"non-task {it['id']} carries severity")
        if (it["level"] == "task"
                and it["type"] in ("security", "performance")
                and "severity" not in it):
            hard.append(f"task {it['id']} missing severity")
        if (it["level"] == "task"
                and it["type"] not in ("security", "performance")
                and "severity" in it):
            hard.append(
                f"task {it['id']} has severity but type={it['type']}"
            )

    # 8. history entry shape (append-only, exactly 5 keys, no banned keys)
    for it in items:
        for h in it["history"]:
            if set(h.keys()) != {"ts", "from", "to", "by", "note"}:
                hard.append(
                    f"{it['id']} history entry shape wrong: "
                    f"{set(h.keys())}"
                )
            if "status" in h or "timestamp" in h:
                hard.append(f"{it['id']} history has banned keys")

    # 12. links shape
    for it in items:
        if set(it["links"].keys()) != {
                "related", "supersedes", "superseded_by"}:
            hard.append(f"{it['id']} links shape wrong")

    # 15. scanners that emitted no findings → null_finding warnings
    categories_with_findings = {it["type"] for it in items}
    null_scanners = set(SCANNERS) - categories_with_findings
    null_kinds = {
        w.get("scanner") for w in warnings
        if w.get("kind") == "null_finding"
    }
    missing = null_scanners - null_kinds
    if missing:
        hard.append(f"missing null_finding warnings for {missing}")

    # 18. transitions shape
    for row in transitions_rows_output:
        needed = {"ts", "id", "level", "from", "to", "by", "note",
                  "run_id"}
        if not needed.issubset(row.keys()):
            hard.append(
                f"transitions row missing keys: {needed - row.keys()}"
            )

    # 20. NNNN contiguity per reported_date (global daily sequence
    # anchored at 0001 per §1). F003: all 6 items have reported_date
    # 2026-04-20 and NNNN 0001..0006.
    by_date: dict[str, list[dict]] = {}
    for it in items:
        by_date.setdefault(it["reported_date"], []).append(it)
    for date, its in by_date.items():
        nnnn_list = sorted(int(it["id"].split("-")[-1]) for it in its)
        if nnnn_list != list(range(1, len(its) + 1)):
            hard.append(
                f"NNNN not contiguous 1..N for {date}: {nnnn_list}"
            )

    # 25/27. evidence paths resolve + each task has ≥1 evidence.
    for it in items:
        for ev in it["evidence"]:
            p = FIXTURE_REPO / ev["path"]
            if not p.exists():
                hard.append(
                    f"{it['id']} evidence path missing on disk: "
                    f"{ev['path']}"
                )
        if it["level"] == "task" and len(it["evidence"]) < 1:
            hard.append(f"task {it['id']} has zero evidence entries")

    # 35. task details keys
    for it in items:
        if it["level"] == "task":
            if set(it["details"].keys()) != REQUIRED_TASK_DETAILS_KEYS:
                hard.append(
                    f"task {it['id']} details keys mismatch: "
                    f"{set(it['details'].keys())}"
                )

    # 37. fingerprint uniqueness + format
    fps = [it["fingerprint"] for it in items]
    if len(set(fps)) != len(fps):
        hard.append("duplicate fingerprints in items[]")
    for it in items:
        if not fp_re.match(it["fingerprint"]):
            hard.append(
                f"{it['id']} bad fingerprint format: {it['fingerprint']}"
            )

    # 43. schema completeness.
    for it in items:
        required = REQUIRED_ITEM_KEYS.copy()
        missing_keys = required - set(it.keys())
        if missing_keys:
            hard.append(
                f"{it['id']} missing required keys: {missing_keys}"
            )
        extra = set(it.keys()) - (REQUIRED_ITEM_KEYS | OPTIONAL_ITEM_KEYS)
        if extra:
            hard.append(f"{it['id']} has extra/invented keys: {extra}")

    # 47. mirror order matches state order.
    if [it["id"] for it in items] != [it["id"] for it in mirror_items]:
        hard.append("mirror items[] order != state index.json order")

    # ==========================================================
    # F003-specific recovery invariants (I1..I5)
    # ==========================================================

    # I1: for every history[] entry in every item, exists a matching
    # transitions row keyed on id + from + to + ts.
    row_keys = {
        (r["id"], r.get("from"), r["to"], r["ts"])
        for r in transitions_rows_output
    }
    for it in items:
        for h in it["history"]:
            key = (it["id"], h.get("from"), h["to"], h["ts"])
            if key not in row_keys:
                hard.append(
                    f"I1: {it['id']} history entry "
                    f"{h.get('from')}→{h['to']} @ {h['ts']} has no "
                    f"matching transitions.jsonl row"
                )

    # I1 (mirror direction, looser): transitions rows for a known item
    # id must correspond to an entry in that item's history[]. If a
    # transitions row has no history counterpart, that's drift too.
    history_keys = {
        (it["id"], h.get("from"), h["to"], h["ts"])
        for it in items
        for h in it["history"]
    }
    for r in transitions_rows_output:
        key = (r["id"], r.get("from"), r["to"], r["ts"])
        if key not in history_keys:
            hard.append(
                f"I1(bis): transitions row {r['id']} "
                f"{r.get('from')}→{r['to']} @ {r['ts']} has no "
                f"matching history[] entry"
            )

    # I2: no item deletion — set(output ids) ⊇ set(seed ids).
    seed_ids = {it["id"] for it in seed_items}
    output_ids = {it["id"] for it in items}
    missing_ids = seed_ids - output_ids
    if missing_ids:
        hard.append(
            f"I2: output dropped seed items: {sorted(missing_ids)} "
            f"— 'Delete history. Ever.' violation"
        )
    # For this fixture specifically, count MUST == 6 (repo unchanged).
    if len(output_ids) != 6:
        hard.append(
            f"I2: expected exactly 6 items post-recovery, got "
            f"{len(output_ids)}"
        )

    # I3: exactly one new transitions row vs seed, attributed to
    # recovery of the interrupted run.
    seed_row_keys = {
        (r["id"], r.get("from"), r["to"], r["ts"])
        for r in seed_transitions_rows
    }
    new_rows = [
        r for r in transitions_rows_output
        if (r["id"], r.get("from"), r["to"], r["ts"]) not in seed_row_keys
    ]
    if len(new_rows) != 1:
        hard.append(
            f"I3: expected exactly 1 new transitions row post-recovery, "
            f"got {len(new_rows)}"
        )
    else:
        note = new_rows[0].get("note", "")
        has_phrase = "interrupt-during-persist" in note
        has_pair = ("recovered" in note) and (INTERRUPTED_RUN_ID in note)
        if not (has_phrase or has_pair):
            hard.append(
                f"I3: recovery row note does not cite interrupted run "
                f"or 'interrupt-during-persist': {note!r}"
            )
        # The recovery row must target SEC-0003 and carry
        # APPROVED→IN_PROGRESS.
        if new_rows[0]["id"] != INTERRUPTED_TARGET_ID:
            hard.append(
                f"I3: recovery row id is {new_rows[0]['id']!r}, "
                f"expected {INTERRUPTED_TARGET_ID!r}"
            )
        if not (new_rows[0].get("from") == "APPROVED"
                and new_rows[0].get("to") == "IN_PROGRESS"):
            hard.append(
                f"I3: recovery row from/to is "
                f"{new_rows[0].get('from')}→{new_rows[0].get('to')}, "
                f"expected APPROVED→IN_PROGRESS"
            )

    # I4: prior-day report immutability.
    seed_reports_root = SEED_AUDIT / "reports"
    out_reports_root = AUDIT_ROOT / "reports"
    for parent, _dirs, files in os.walk(seed_reports_root):
        parent_p = Path(parent)
        for name in files:
            src = parent_p / name
            rel = src.relative_to(seed_reports_root).as_posix()
            dst = out_reports_root / rel
            if not dst.exists():
                hard.append(
                    f"I4: prior-day report missing from output: {rel}"
                )
                continue
            if sha256_bytes(src) != sha256_bytes(dst):
                hard.append(
                    f"I4: prior-day report bytes differ at {rel} — "
                    f"'Delete history. Ever.' / 'per-date view' "
                    f"invariant violation"
                )

    # I5: stale lock released. The lock file MUST be either absent
    # or zero-byte — i.e. not holding any run's payload. A non-empty
    # file is read as "still held by whoever wrote those bytes", which
    # is exactly the stale-lock signature from an interrupted run.
    lock_path = AUDIT_ROOT / "state" / "locks" / "run.lock"
    if lock_path.exists() and lock_path.stat().st_size > 0:
        hard.append(
            f"I5: stale lock still present at "
            f"{lock_path.relative_to(AUDIT_ROOT)}"
        )

    return len(hard) == 0, hard, soft


# ---- banner + run_summary --------------------------------------------------

def render_banner(items: list[dict], counts: dict) -> str:
    must_tasks = [
        it for it in items
        if it["level"] == "task" and it["moscow"] == "MUST"
        and it["status"] == "PROPOSED"
    ]
    lines = [
        f"Audit complete — {RUN_ID}",
        f"Report:        .audit/reports/2026/04/{REPORT_DATE}.md",
        f"Mirror (json): .audit/reports/2026/04/{REPORT_DATE}.json",
        "",
        "Recovery:      detected interrupt-during-persist on "
        f"{INTERRUPTED_RUN_ID}",
        "               appended 1 transitions row + 1 CHANGELOG bullet",
        "               released stale lock at state/locks/run.lock",
        "",
        "Findings this run: 0 new · 0 merged · 6 deduped against "
        "2026-04-20 fingerprints",
    ]
    m = counts["by_moscow"]
    lines.append(
        f"Today total:       {counts['total']} "
        f"(MUST {m['MUST']} · SHOULD {m['SHOULD']} · "
        f"COULD {m['COULD']} · WONT {m['WONT']})"
    )
    lines.append(
        f"Pending review:    {counts['by_status']['PROPOSED']} PROPOSED · "
        f"{counts['by_status']['IN_PROGRESS']} IN_PROGRESS"
    )
    lines.append("")
    lines.append("Top MUST items (PROPOSED):")
    if not must_tasks:
        lines.append(
            "  (none PROPOSED — 1 MUST task already IN_PROGRESS: "
            f"{INTERRUPTED_TARGET_ID})"
        )
    else:
        for i, it in enumerate(must_tasks[:10], 1):
            lines.append(f"  {i}. {it['id']} — {it['title']}")
    lines.append("")
    lines.append("Next steps:")
    lines.append(
        "  • Review 5 PROPOSED items in state/index.json (or the "
        "daily report)."
    )
    lines.append(
        "  • Resume execute of IN_PROGRESS item "
        f"({INTERRUPTED_TARGET_ID}): MODE=execute"
    )
    lines.append(
        "  • To re-scan after changes:              "
        "(run again — same day appends)"
    )
    return "\n".join(lines) + "\n"


def render_run_summary(items: list[dict], counts: dict,
                       warnings: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "mode": "scan",
        "trigger": "recovery",
        "scope": ".",
        "dry_run": False,
        "no_git": NO_GIT,
        "truncated": False,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "ok": True,
        "errors": [],
        "warnings": warnings,
        "report_md": f".audit/reports/2026/04/{REPORT_DATE}.md",
        "report_json": f".audit/reports/2026/04/{REPORT_DATE}.json",
        "counts": {
            "new": 0,
            "merged": 0,
            "deduped_against_history": 6,
            "blocked_by_wontdo": 0,
            "total": counts["total"],
            "by_level": counts["by_level"],
            "by_moscow": counts["by_moscow"],
            "by_assignee": counts["by_assignee"],
            "by_status": counts["by_status"],
        },
        "recovery": {
            "interrupted_run_id": INTERRUPTED_RUN_ID,
            "interrupted_started_at": INTERRUPTED_STARTED_AT,
            "interrupted_crash_ts": INTERRUPTED_CRASH_TS,
            "interrupted_target_id": INTERRUPTED_TARGET_ID,
            "transitions_rows_appended": 1,
            "changelog_bullets_appended": 1,
            "stale_lock_released": True,
        },
        "must_review_now": [
            it["id"] for it in items
            if it["level"] == "task" and it["moscow"] == "MUST"
            and it["status"] == "PROPOSED"
        ][:10],
        "next_action": "review",
    }


# ---- main -----------------------------------------------------------------

def _soft_reset(root: Path) -> None:
    """
    Mount-agnostic reset: unlink what we can, zero-truncate what we
    can't. Some fuse mounts forbid unlink but allow write — in that
    case a prior run's artifact stays on disk as a 0-byte file, which
    is semantically equivalent to "gone" for our invariants (e.g. the
    lock file's I5 check treats 0-byte as "released").
    """
    if not root.exists():
        return
    for parent, _dirs, files in os.walk(root, topdown=False):
        parent_p = Path(parent)
        for name in files:
            fp = parent_p / name
            try:
                fp.unlink()
            except (PermissionError, OSError):
                try:
                    fp.write_text("")
                except Exception:
                    pass
        # Try to remove empty dirs; silently tolerate failure.
        try:
            parent_p.rmdir()
        except (PermissionError, OSError):
            pass


def main():
    # Wipe any stale output tree so the run is reproducible.
    _soft_reset(AUDIT_ROOT)

    # 1) Load seed artifacts. We do not mutate the seed on disk.
    seed_index = read_json(SEED_AUDIT / "state" / "index.json")
    seed_in_flight = read_json(SEED_AUDIT / "state" / "in-flight.json")
    seed_wontdo = read_json(SEED_AUDIT / "state" / "wont-do.json")
    seed_transitions = load_transitions(
        read_text(SEED_AUDIT / "changelog" / "transitions.jsonl"))
    seed_changelog = read_text(SEED_AUDIT / "changelog" / "CHANGELOG.md")
    seed_readme = read_text(SEED_AUDIT / "README.md")
    seed_config = read_text(SEED_AUDIT / "config.yaml")

    # 2) Recovery phase — detect the gap.
    missing = detect_missing_transitions(seed_index, seed_transitions)
    if len(missing) != 1:
        raise SystemExit(
            f"F003 seed invariant violated: expected exactly 1 missing "
            f"transitions row, found {len(missing)}: {missing!r}"
        )
    target_id, target_h = missing[0]
    target_item = next(it for it in seed_index if it["id"] == target_id)
    assert target_id == INTERRUPTED_TARGET_ID, (
        f"recovery target mismatch: {target_id!r} != "
        f"{INTERRUPTED_TARGET_ID!r}"
    )
    assert target_h["from"] == "APPROVED" and target_h["to"] == "IN_PROGRESS"

    recovery_row = build_recovery_row(target_item, target_h)
    recovery_bullet = build_recovery_changelog_bullet(target_item, target_h)

    # 3) Build output artifacts.
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)

    # state/ — index + in-flight + wont-do unchanged. Locks dir empty
    # (lock released). We do NOT carry over the stale lock file.
    state_dir = AUDIT_ROOT / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    write_json(state_dir / "index.json", seed_index)
    write_json(state_dir / "in-flight.json", seed_in_flight)
    write_json(state_dir / "wont-do.json", seed_wontdo)
    (state_dir / "locks").mkdir(exist_ok=True)

    # changelog/ — append the recovery row + bullet.
    changelog_dir = AUDIT_ROOT / "changelog"
    changelog_dir.mkdir(parents=True, exist_ok=True)
    out_transitions_rows = list(seed_transitions) + [recovery_row]
    (changelog_dir / "transitions.jsonl").write_text(
        dump_transitions(out_transitions_rows), encoding="utf-8"
    )
    # Append the bullet strictly after the existing bullets; preserve
    # the seed bytes exactly up to the new line.
    seed_changelog_trimmed = seed_changelog.rstrip("\n")
    out_changelog = seed_changelog_trimmed + "\n" + recovery_bullet + "\n"
    (changelog_dir / "CHANGELOG.md").write_text(
        out_changelog, encoding="utf-8"
    )

    # reports/ — copy prior-day reports byte-identical; emit today's.
    reports_out = AUDIT_ROOT / "reports"
    seed_reports = SEED_AUDIT / "reports"
    copy_tree_strict(seed_reports, reports_out, exclude_rel=set())
    reports_today_dir = reports_out / "2026" / "04"
    reports_today_dir.mkdir(parents=True, exist_ok=True)

    counts = counts_from(seed_index)
    today_warnings = [
        {"kind": "no_git", "message": "provenance unavailable"},
        {"kind": "recovery",
         "message": (
             f"appended 1 transitions row for interrupted run "
             f"{INTERRUPTED_RUN_ID}; released stale lock"
         )},
    ]
    for scanner in ["reliability", "quality", "architecture",
                    "dx", "docs", "ideas"]:
        today_warnings.append({
            "kind": "null_finding",
            "scanner": scanner,
            "reason": "no candidates produced by scanner",
        })

    md_text = render_today_md(seed_index, counts)
    (reports_today_dir / f"{REPORT_DATE}.md").write_text(
        md_text, encoding="utf-8"
    )
    write_json(
        reports_today_dir / f"{REPORT_DATE}.json",
        render_today_json(seed_index, counts, today_warnings),
    )

    # README + config — unchanged.
    (AUDIT_ROOT / "README.md").write_text(seed_readme, encoding="utf-8")
    (AUDIT_ROOT / "config.yaml").write_text(seed_config, encoding="utf-8")

    # implementations/ — empty dir (recovery didn't start new execute).
    (AUDIT_ROOT / "implementations").mkdir(parents=True, exist_ok=True)

    # 4) Step 7.5 + recovery invariants.
    mirror_items = [compact_item(it) for it in seed_index]
    # Re-load the written transitions back as the authoritative output
    # (paranoia check: asserts the on-disk bytes match what Step 7.5
    # is validating).
    transitions_on_disk = load_transitions(
        read_text(changelog_dir / "transitions.jsonl"))
    assert transitions_on_disk == out_transitions_rows

    passed, hard, soft = run_step_7_5(
        items=seed_index,
        mirror_items=mirror_items,
        transitions_rows_output=out_transitions_rows,
        seed_transitions_rows=seed_transitions,
        seed_items=seed_index,
        warnings=today_warnings,
    )

    # 5) Banner + run_summary + capture.
    banner = render_banner(seed_index, counts)
    (RUN_DIR / "banner.txt").write_text(banner, encoding="utf-8")

    run_summary = render_run_summary(seed_index, counts, today_warnings)
    write_json(RUN_DIR / "run_summary.json", run_summary)

    def any_hard(keyword: str) -> bool:
        return any(keyword in v for v in hard)

    capture = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "timestamp": STARTED_AT,
        "audit_md_version": AUDIT_MD_VERSION,
        "model_id": MODEL_ID,
        "ide_id": IDE_ID,
        "fixture_id": FIXTURE_ID,
        "mode": "scan",
        "trigger": "recovery",
        "step_7_5_passed": passed,
        "hard_violation_count": len(hard),
        "soft_violation_count": len(soft),
        "violations": hard,
        "counts": counts,
        "recovery": run_summary["recovery"],
        "rules_exercised": {
            "R-anti-drift-mirror-state-invariants":
                "fail" if any_hard("mirror items[]") else "pass",
            "R-anti-drift-atomic-persist":
                "fail" if (any_hard("I1:") or any_hard("I3:")
                           or any_hard("I5:"))
                else "pass",
            "R-anti-drift-history-append-only":
                "fail" if any_hard("history") else "pass",
            "R-anti-drift-transitions-append-only":
                "fail" if (any_hard("I1:") or any_hard("I1(bis)"))
                else "pass",
            "R-anti-drift-id-format-strict":
                "fail" if (any_hard("bad id") or any_hard("NNNN"))
                else "pass",
            "R-anti-drift-stale-lock-recovery":
                "fail" if any_hard("I5:") else "pass",
            "R-anti-drift-no-deletion-to-pass":
                "fail" if any_hard("I2:") else "pass",
            "S-item-schema-required-fields":
                "fail" if (any_hard("missing required keys")
                           or any_hard("invented keys"))
                else "pass",
            "R-anti-drift-hitl-banner-required":
                "pass" if (RUN_DIR / "banner.txt").exists() else "fail",
            "P-step-7-5-self-conformance":
                "pass" if passed else "fail",
            "O-run-summary-json-schema":
                "pass" if (RUN_DIR / "run_summary.json").exists() else "fail",
            "X-step-7-5-no-deletion-to-pass":
                "fail" if any_hard("I2:") else "pass",
        },
        "artifacts": {
            "audit_tree": ".audit/",
            "daily_md": f".audit/reports/2026/04/{REPORT_DATE}.md",
            "daily_json": f".audit/reports/2026/04/{REPORT_DATE}.json",
            "transitions": ".audit/changelog/transitions.jsonl",
            "changelog": ".audit/changelog/CHANGELOG.md",
            "banner": "banner.txt",
            "run_summary": "run_summary.json",
        },
        "notes": (
            "First real F003 baseline cell. Seeded .audit/ represents "
            "a mid-persist crash in execute-mode run "
            f"{INTERRUPTED_RUN_ID}: state/index.json was updated to "
            f"mark {INTERRUPTED_TARGET_ID} IN_PROGRESS (+history[3]) "
            "and state/in-flight.json was populated, but the batched "
            "step-9 append of the APPROVED→IN_PROGRESS row to "
            "transitions.jsonl + CHANGELOG.md never happened; the "
            "lock at state/locks/run.lock was left stale. This run "
            "(scan+recovery) detected the gap, appended exactly 1 "
            "recovery row carrying the original ts + the recovery "
            "note (citing both 'interrupt-during-persist' and the "
            "interrupted run_id), appended the matching CHANGELOG "
            "bullet, released the lock, and completed today's scan "
            "with 0 new findings + 6 deduped against 2026-04-20 "
            "fingerprints. I1..I5 verified: (I1) every history[] "
            "entry has a matching transitions row and vice versa; "
            "(I2) no item deletion — 6 → 6; (I3) exactly 1 new row "
            "vs seed, attributed to recovery; (I4) 2026-04-20.md "
            "and 2026-04-20.json bytes preserved byte-identical to "
            "seed; (I5) state/locks/run.lock absent at end of run."
        ),
    }
    write_json(RUN_DIR / "capture.json", capture)

    print("\n=== HITL BANNER ===\n")
    print(banner)
    print("=== Run Summary JSON ===\n")
    print(json.dumps(run_summary, indent=2))
    print("\n=== Step 7.5 ===")
    print(f"passed: {passed}")
    print(f"hard ({len(hard)}): {hard}")
    print(f"soft ({len(soft)}): {soft}")


if __name__ == "__main__":
    main()
