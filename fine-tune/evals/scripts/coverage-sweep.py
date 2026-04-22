"""
Fixture / rule coverage sweep.

For every rule in rule-registry.json, verify:
  (a) every fixture listed in fixtures_exercising[] has a 'pass' entry for
      that rule in baseline.json's corresponding cell, and
  (b) every fixture listed in fixtures_exercising[] actually exists in
      baseline.json's fixtures map.

For every rule appearing in any baseline cell's rules_exercised dict:
  (c) the rule is present in rule-registry.json with status=active.

Also flag:
  (d) every fixture whose 'exercises_rules' list is not a superset of the
      union of rule_ids in any of its cells' rules_exercised map.
  (e) any rule with status=active and empty fixtures_exercising[].
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]

def load_json(p: Path) -> dict:
    return json.loads(p.read_text())


def main() -> int:
    registry = load_json(EVALS / "rule-registry.json")
    baseline = load_json(EVALS / "baseline.json")

    registered_ids = {r["rule_id"]: r for r in registry["rules"]}
    active_ids = {rid for rid, r in registered_ids.items() if r.get("status") == "active"}

    fixtures = baseline["fixtures"]
    fixture_ids = set(fixtures.keys())

    problems: list[str] = []
    notes: list[str] = []

    # --------------------------------------------------------------
    # (a) + (b): per-rule side — every rule's claimed fixtures must
    # exist in baseline and have a 'pass' entry for that rule.
    # --------------------------------------------------------------
    for rid, rule in registered_ids.items():
        if rule.get("status") != "active":
            continue
        claimed = rule.get("fixtures_exercising", [])
        if not claimed:
            notes.append(f"COVERAGE GAP: rule {rid} has no fixtures — no baseline proves it load-bearing")
            continue
        for fix in claimed:
            if fix not in fixture_ids:
                problems.append(
                    f"UNKNOWN FIXTURE: rule {rid} lists fixtures_exercising={fix!r}, "
                    f"but no such fixture in baseline.json")
                continue
            # For each cell in this fixture, require a pass for this rule.
            # (All current cells are the single canonical one — just verify
            # at least one cell reports 'pass'.)
            cells = fixtures[fix].get("cells", {})
            passes = 0
            for ckey, cell in cells.items():
                exercised = cell.get("rules_exercised", {})
                if exercised.get(rid) == "pass":
                    passes += 1
            if passes == 0:
                problems.append(
                    f"CLAIM NOT PROVED: rule {rid} claims fixture {fix} "
                    f"but no cell in that fixture reports 'pass' for it")

    # --------------------------------------------------------------
    # (c): per-baseline side — every rule mentioned in any cell must
    # be registered and active.
    # --------------------------------------------------------------
    for fix, body in fixtures.items():
        for ckey, cell in body.get("cells", {}).items():
            exercised = cell.get("rules_exercised", {})
            for rid, status in exercised.items():
                if rid == "_comment":
                    continue
                if rid not in registered_ids:
                    problems.append(
                        f"UNREGISTERED RULE: fixture {fix} / cell {ckey} "
                        f"references {rid!r} but it is not in rule-registry.json")
                elif rid not in active_ids:
                    problems.append(
                        f"INACTIVE RULE REFERENCED: fixture {fix} / cell {ckey} "
                        f"references {rid!r} which is status!=active in registry")

    # --------------------------------------------------------------
    # (d): each fixture's exercises_rules[] should include every rule
    # its cells actually report on.
    # --------------------------------------------------------------
    for fix, body in fixtures.items():
        declared = set(body.get("exercises_rules", []))
        cell_rule_union: set[str] = set()
        for cell in body.get("cells", {}).values():
            for rid in cell.get("rules_exercised", {}):
                if rid != "_comment":
                    cell_rule_union.add(rid)
        missing = cell_rule_union - declared
        extra = declared - cell_rule_union
        if missing:
            problems.append(
                f"EXERCISES_RULES GAP: fixture {fix} has cells reporting on "
                f"rules not listed in its exercises_rules[]: {sorted(missing)}")
        if extra:
            notes.append(
                f"EXERCISES_RULES EXTRA: fixture {fix} declares "
                f"{sorted(extra)} in exercises_rules[] but no cell exercises them")

    # --------------------------------------------------------------
    # (e): rules with active status but no fixtures_exercising.
    # (Covered by the note emission in (a).)
    # --------------------------------------------------------------

    # --------------------------------------------------------------
    # Rule-survival invariant cross-check
    # --------------------------------------------------------------
    # For every active rule, there should be at least one cell with pass.
    rule_pass_count: dict[str, int] = {rid: 0 for rid in active_ids}
    for body in fixtures.values():
        for cell in body.get("cells", {}).values():
            for rid, status in cell.get("rules_exercised", {}).items():
                if status == "pass" and rid in rule_pass_count:
                    rule_pass_count[rid] += 1
    zero_pass = [rid for rid, n in rule_pass_count.items() if n == 0]
    if zero_pass:
        for rid in zero_pass:
            notes.append(
                f"ZERO PASSES: active rule {rid} has zero 'pass' across all baseline cells")

    # --------------------------------------------------------------
    # Emit report
    # --------------------------------------------------------------
    print("=" * 72)
    print("FIXTURE / RULE COVERAGE SWEEP")
    print("=" * 72)
    print(f"Registered rules (active): {len(active_ids)}")
    print(f"Fixtures in baseline:      {len(fixture_ids)}")
    n_cells = sum(len(b.get("cells", {})) for b in fixtures.values())
    print(f"Baseline cells:            {n_cells}")
    print()

    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  ✗ {p}")
        print()
    else:
        print("PROBLEMS: none — baseline and registry are consistent.")
        print()

    if notes:
        print(f"NOTES ({len(notes)}):")
        for n in notes:
            print(f"  · {n}")
        print()

    # Per-rule pass tally table
    print("PER-RULE PASS TALLY:")
    w = max(len(r) for r in active_ids)
    for rid in sorted(active_ids):
        n = rule_pass_count[rid]
        mark = "  " if n > 0 else "⚠ "
        print(f"  {mark}{rid:<{w}}  passes={n}")

    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
