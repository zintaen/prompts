#!/usr/bin/env python3
"""
F006 fault_inject.py — invariant load-bearing proof.

For each of the three F006 invariants, mutate the clean output and
confirm the mutation trips the expected hard violation in Step 7.5.
A single mutation that does NOT trip a violation is a fixture bug
(the invariant was never load-bearing).

Invariants:
  I1 (O1 = O-mode-precedence-inline-over-env)
  I2 (C1 = C-exclusions-respected)
  I3 (C2 = C-budgets-respected)

Approach: re-run the clean scan in-memory via build.py's functions,
then apply a minimal mutation to the artifact objects before the
Step-7.5 pass. Each mutation targets exactly one invariant.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
BUILD_PY = RUN_DIR / "build.py"


def _load_build_module():
    spec = importlib.util.spec_from_file_location("f006_build", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def clean_run(mod):
    """Replay the clean scan in memory; return everything Step 7.5 needs."""
    effective = mod.resolve_invocation()
    file_census = mod.enumerate_candidate_files()
    in_scope = [f for f in file_census if not f["excluded"]]
    scan_report = mod.security_scan(in_scope)
    items = mod.compose_items(scan_report["findings"])
    soft = []
    if scan_report["truncated"]:
        soft.append({
            "code": "BUDGET_TRUNCATED",
            "scanner": "security",
            "limit": f"max_files_per_task={mod.BUDGETS['max_files_per_task']}",
            "truncated_count": len(scan_report["truncated"]),
            "advisory": "ok",
        })
    # (Re)emit the .audit/ tree so Step 7.5's artifact grep has content.
    mod.write_audit_tree(items, effective, scan_report, file_census)
    mod.write_banner(items)
    return effective, file_census, in_scope, scan_report, items, soft


def run_step_7_5(mod, effective, scan_report, file_census, items, soft):
    return mod.step_7_5(
        items, effective, scan_report, file_census, soft, mod.AUDIT_ROOT,
    )


# ---- mutations --------------------------------------------------------------

def mutate_I1_mode_provenance(effective):
    """Flip effective mode to 'execute' so inline was not honored."""
    m = copy.deepcopy(effective)
    m["mode"] = "execute"
    m["provenance"]["MODE"] = {
        "value": "execute",
        "source": "env",
    }
    return m


def mutate_I2_leak_excluded_path_into_artifact(mod, file_census):
    """Poke an excluded path into the daily report so exclusion check fires."""
    daily = mod.AUDIT_ROOT / "reports" / "2026" / "04" / f"{mod.REPORT_DATE}.md"
    txt = daily.read_text(encoding="utf-8")
    # Inject a bare excluded-path marker — Step 7.5's subtle-marker grep
    # will trip on this.
    bad = txt + "\n<!-- debug: vendor/fake-lib/secret.js scanned -->\n"
    daily.write_text(bad, encoding="utf-8")


def mutate_I3_strip_budget_soft(soft):
    """Remove the BUDGET_TRUNCATED soft while truncation is still real."""
    return []


# ---- driver -----------------------------------------------------------------

def check(label: str, passed: bool, hard: list, expected_rule: str) -> bool:
    matched = any(v.get("rule") == expected_rule for v in hard)
    ok = (not passed) and matched
    mark = "OK" if ok else "FAIL"
    reason = ""
    if passed:
        reason = "step_7_5 passed (expected fail)"
    elif not matched:
        reason = f"hard didn't include {expected_rule}; got {[v.get('rule') for v in hard]}"
    print(f"  [{mark}] {label}   {reason}")
    return ok


def main() -> int:
    mod = _load_build_module()

    # Clean baseline — must pass.
    eff0, census0, _, scan0, items0, soft0 = clean_run(mod)
    passed0, hard0, _ = run_step_7_5(mod, eff0, scan0, census0, items0, soft0)
    print("Clean baseline:")
    print(f"  step_7_5_passed={passed0} hard={len(hard0)}")
    if not passed0:
        print("  !! clean baseline already failing; invariants cannot be evaluated")
        for v in hard0:
            print(f"     {v}")
        return 2

    results: list[bool] = []

    # -------- I1: mode provenance ----------
    print("\nI1: inline MODE=scan must beat env MODE=execute")
    mod.write_audit_tree(items0, eff0, scan0, census0)  # reset tree
    eff_mut = mutate_I1_mode_provenance(eff0)
    passed, hard, _ = run_step_7_5(mod, eff_mut, scan0, census0, items0, soft0)
    results.append(check("I1 mode mutation → hard violation",
                         passed, hard, "O-mode-precedence-inline-over-env"))

    # -------- I2: exclusions leak ----------
    print("\nI2: excluded paths must never appear in emitted artifacts")
    mod.write_audit_tree(items0, eff0, scan0, census0)  # reset tree
    mutate_I2_leak_excluded_path_into_artifact(mod, census0)
    passed, hard, _ = run_step_7_5(mod, eff0, scan0, census0, items0, soft0)
    results.append(check("I2 excluded-path leak → hard violation",
                         passed, hard, "C-exclusions-respected"))
    mod.write_audit_tree(items0, eff0, scan0, census0)  # restore

    # -------- I3: silent budget truncation ----------
    print("\nI3: truncation without BUDGET_TRUNCATED soft → hard violation")
    mod.write_audit_tree(items0, eff0, scan0, census0)  # reset tree
    soft_mut = mutate_I3_strip_budget_soft(soft0)
    passed, hard, _ = run_step_7_5(mod, eff0, scan0, census0, items0, soft_mut)
    results.append(check("I3 stripped BUDGET_TRUNCATED soft → hard violation",
                         passed, hard, "C-budgets-respected"))

    # -------- summary ----------
    print()
    if all(results):
        print("All I1..I3 invariants are load-bearing.")
        return 0
    print("One or more invariants did NOT trip — fixture is leaky.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
