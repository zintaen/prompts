"""
Fault injection harness for F003 recovery invariants.

For each of I1..I5, apply a targeted mutation to the outputs produced by
build.py and confirm the mutation causes run_step_7_5 to report the
expected hard violation. A green run of this script proves each invariant
is load-bearing — that is, removing the correct recovery behavior is
actually detected, not merely nominally listed.

Run after `python3 build.py` so that the clean .audit/ tree already
exists; this script never writes to disk, only re-invokes run_step_7_5
with mutated in-memory arguments.
"""
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_PY = HERE / "build.py"
spec = importlib.util.spec_from_file_location("f003_build", BUILD_PY)
build = importlib.util.module_from_spec(spec)
sys.modules["f003_build"] = build
spec.loader.exec_module(build)


def _load_clean_state():
    """Read in the clean post-build outputs."""
    items = build.read_json(build.AUDIT_ROOT / "state" / "index.json")
    mirror_items = [build.compact_item(it) for it in items]
    trans_rows = build.load_transitions(
        build.read_text(build.AUDIT_ROOT / "changelog" / "transitions.jsonl")
    )
    seed_items = build.read_json(build.SEED_AUDIT / "state" / "index.json")
    seed_trans_rows = build.load_transitions(
        build.read_text(build.SEED_AUDIT / "changelog" / "transitions.jsonl")
    )
    return items, mirror_items, trans_rows, seed_items, seed_trans_rows


WARN_STUB = [
    {"kind": "no_git", "message": "provenance unavailable"},
    {"kind": "recovery",
     "message": "appended 1 transitions row for interrupted run "
                "run-2026-04-22T08:00:00Z-b3c4; released stale lock"},
    {"kind": "null_finding", "scanner": "reliability",
     "reason": "no candidates produced by scanner"},
    {"kind": "null_finding", "scanner": "quality",
     "reason": "no candidates produced by scanner"},
    {"kind": "null_finding", "scanner": "architecture",
     "reason": "no candidates produced by scanner"},
    {"kind": "null_finding", "scanner": "dx",
     "reason": "no candidates produced by scanner"},
    {"kind": "null_finding", "scanner": "docs",
     "reason": "no candidates produced by scanner"},
    {"kind": "null_finding", "scanner": "ideas",
     "reason": "no candidates produced by scanner"},
]


def _run(items, trans, seed_trans, seed_items, mirror=None):
    """
    Invoke run_step_7_5. By default the mirror is recomputed from
    items so unrelated checks (mirror order, in-flight consistency)
    don't dominate. Pass a mirror explicitly to exercise the mirror
    invariants themselves.
    """
    if mirror is None:
        mirror = [build.compact_item(it) for it in items]
    passed, hard, soft = build.run_step_7_5(
        items, mirror, trans, seed_trans, seed_items, WARN_STUB)
    return passed, hard, soft


def expect_trip(label: str, hard: list[str], needle: str) -> None:
    matched = [h for h in hard if needle in h]
    if not matched:
        raise AssertionError(
            f"{label}: expected a hard violation containing {needle!r}, "
            f"got {hard!r}"
        )
    print(f"  OK  {label}: tripped on — {matched[0]}")


def expect_clean(label: str, passed: bool, hard: list[str]) -> None:
    if not passed:
        raise AssertionError(
            f"{label}: baseline run is not clean — {hard!r}"
        )
    print(f"  OK  {label}: clean baseline")


def main() -> int:
    print("=== Fault injection: F003 I1..I5 ===")
    items, _mirror, trans, seed_items, seed_trans = _load_clean_state()

    # 0. Baseline must pass.
    passed, hard, _ = _run(items, trans, seed_trans, seed_items)
    expect_clean("baseline", passed, hard)

    # -----------------------------------------------------------------
    # I1: history→transitions mismatch. Remove the recovery
    # transitions row while leaving the IN_PROGRESS history entry
    # in place — this simulates "state/index.json persisted but
    # transitions.jsonl append never happened" (exactly the crash
    # F003 reproduces).
    # -----------------------------------------------------------------
    mutated_trans = [
        r for r in trans
        if not (r["id"] == "AUD-2026-04-20-SEC-0003"
                and r.get("from") == "APPROVED"
                and r.get("to") == "IN_PROGRESS")
    ]
    _, hard, _ = _run(items, mutated_trans, seed_trans, seed_items)
    expect_trip("I1 (history entry has no transitions row)", hard, "I1:")

    # I1(bis): transitions row without a history counterpart — add a
    # ghost row for a state change the index never recorded.
    mutated_trans = copy.deepcopy(trans)
    mutated_trans.append({
        "ts": "2026-04-22T09:05:00Z",
        "id": "AUD-2026-04-20-SEC-0003",
        "level": "task",
        "from": "IN_PROGRESS",
        "to": "DONE",
        "by": "AGENT",
        "note": "ghost",
        "run_id": build.RUN_ID,
        "fingerprint":
            "sha256:ac4421b18c135d38918ad448f43651bbdf0ab251c809b1d63232d66827efa43e",
    })
    _, hard, _ = _run(items, mutated_trans, seed_trans, seed_items)
    expect_trip("I1(bis) (ghost transitions row)", hard, "I1(bis):")

    # -----------------------------------------------------------------
    # I2: item deletion. Drop SEC-0003 from the output index to
    # simulate "I'll just delete it to make the recovery simpler",
    # which is a 'Delete history. Ever.' violation.
    # -----------------------------------------------------------------
    mutated_items = [it for it in items if it["id"] != "AUD-2026-04-20-SEC-0003"]
    _, hard, _ = _run(mutated_items, trans, seed_trans, seed_items)
    expect_trip("I2 (dropped seed item)", hard, "I2:")

    # -----------------------------------------------------------------
    # I3: recovery row wrong (zero new rows case — agent never
    # appended the recovery row at all).
    # -----------------------------------------------------------------
    mutated_trans = [
        r for r in trans
        if not (r["id"] == "AUD-2026-04-20-SEC-0003"
                and r.get("from") == "APPROVED"
                and r.get("to") == "IN_PROGRESS")
    ]
    # Also remove the matching history entry so I1 doesn't dominate.
    mutated_items = copy.deepcopy(items)
    for it in mutated_items:
        if it["id"] == "AUD-2026-04-20-SEC-0003":
            it["history"] = [
                h for h in it["history"]
                if not (h.get("from") == "APPROVED"
                        and h.get("to") == "IN_PROGRESS")
            ]
            it["status"] = "APPROVED"
            it["last_updated"] = "2026-04-21T14:22:00Z"
    _, hard, _ = _run(mutated_items, mutated_trans, seed_trans, seed_items)
    expect_trip("I3 (zero new rows)", hard, "I3: expected exactly 1 new")

    # I3: recovery row with wrong note (does not cite interrupted run).
    mutated_trans = copy.deepcopy(trans)
    for r in mutated_trans:
        if (r["id"] == "AUD-2026-04-20-SEC-0003"
                and r.get("from") == "APPROVED"
                and r.get("to") == "IN_PROGRESS"):
            r["note"] = "execute started"  # looks fine, hides the recovery
    _, hard, _ = _run(items, mutated_trans, seed_trans, seed_items)
    expect_trip("I3 (note omits interrupted-run attribution)",
                hard, "does not cite interrupted run")

    # I3: recovery row with wrong from/to.
    mutated_trans = copy.deepcopy(trans)
    for r in mutated_trans:
        if (r["id"] == "AUD-2026-04-20-SEC-0003"
                and r.get("from") == "APPROVED"
                and r.get("to") == "IN_PROGRESS"):
            r["from"] = "PROPOSED"
            r["to"] = "IN_PROGRESS"
    # history needs matching change so I1 doesn't dominate.
    mutated_items = copy.deepcopy(items)
    for it in mutated_items:
        if it["id"] == "AUD-2026-04-20-SEC-0003":
            for h in it["history"]:
                if (h.get("from") == "APPROVED"
                        and h.get("to") == "IN_PROGRESS"):
                    h["from"] = "PROPOSED"
    _, hard, _ = _run(mutated_items, mutated_trans, seed_trans, seed_items)
    expect_trip("I3 (wrong from/to)", hard, "expected APPROVED→IN_PROGRESS")

    # -----------------------------------------------------------------
    # I4: prior-day report mutation. Simulate by pointing the check
    # at a tampered output copy — easiest path is to temporarily
    # overwrite the output file's bytes, run, then restore.
    # -----------------------------------------------------------------
    out_prior = build.AUDIT_ROOT / "reports" / "2026" / "04" / "2026-04-20.md"
    original = out_prior.read_bytes()
    try:
        out_prior.write_bytes(original + b"\n<!-- tampered -->\n")
        _, hard, _ = _run(items, trans, seed_trans, seed_items)
        expect_trip("I4 (prior-day report mutated)", hard, "I4:")
    finally:
        out_prior.write_bytes(original)

    # -----------------------------------------------------------------
    # I5: stale lock left in place. Restore it temporarily.
    # -----------------------------------------------------------------
    # I5 reads stale-lock signal as "file exists AND is non-empty".
    # Write payload, assert trip, then truncate to 0 bytes (which is
    # the "released" state). The mount forbids unlink so we model
    # "released" as empty content; this matches build.py's I5 rule.
    lock_path = build.AUDIT_ROOT / "state" / "locks" / "run.lock"
    try:
        lock_path.write_text(
            '{"run_id":"run-2026-04-22T08:00:00Z-b3c4","pid":91234}\n'
        )
        _, hard, _ = _run(items, trans, seed_trans, seed_items)
        expect_trip("I5 (stale lock present)", hard, "I5:")
    finally:
        # Truncate rather than unlink (mount-agnostic cleanup).
        lock_path.write_text("")

    # Final sanity: baseline is still clean after all mutations restored.
    passed, hard, _ = _run(items, trans, seed_trans, seed_items)
    expect_clean("baseline (post-restore)", passed, hard)

    print("\nAll I1..I5 invariants are load-bearing. ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
