# evals/ — AUDIT.md regression-gate harness

This directory is the regression gate for `AUDIT.md`. Before a proposed edit to `AUDIT.md` is merged, the harness replays a fixed set of fixtures against the *candidate* spec and blocks the merge if any previously-passing fixture × rule cell flips to fail.

It is also the substrate for Layer-2 rule-level regression: every rule in `rule-registry.json` has a stable `rule_id` and a per-cell pass/fail ledger in `baseline.json`, so a rule that silently weakens in a spec edit is caught even when the fixture overall still passes.

Current status (2026-04-23): **5 fixtures, 5 baseline cells, all green, 30 active rules** — 30 covered by ≥1 passing cell, 3 acknowledged coverage gaps (documented per-rule).

---

## The three authoritative files

The harness lives on three tightly-coupled files. Keep them consistent.

| File | Role |
|---|---|
| `AUDIT.md` (parent dir) | The spec. Source of truth for behavior. |
| `rule-registry.json` | Every behavioral rule has a stable `rule_id` here, anchored to an AUDIT.md §-location. `rule_id`s survive §-number reorganization; raw §numbers in captures are a bug. |
| `baseline.json` | Per `(fixture × model × ide × audit_md_version)` cell: overall result + per-`rule_id` pass/fail. This is the ledger regression is measured against. |

`criteria.md` defines what "pass" and "regression" mean; `pe-best-practices.md` is the Layer-4 scorecard for the spec's prompt-engineering quality.

## The five fixtures

Each fixture is a scenario designed to trip a specific class of drift. A "pass" means every invariant the fixture claims to test is demonstrably load-bearing — proved both by the main scan (Step 7.5 self-conformance green) and, for F003/F004/F005, by a fault-injection harness that mutates each invariant and confirms the mutation trips the expected violation.

| Fixture | Type | What it traps |
|---|---|---|
| `F001-fresh-repo-small` | fresh | Baseline end-to-end scan on a small repo. Exercises ID format, type3 closed-set, MoSCoW closed, severity ladder, redaction required, HITL banner, item-schema, daily-report shape, output contract. |
| `F002-resume-existing-audit` | resume | Seeded from F001's output. Exercises canonical 4-key sort, transitions append-only, mirror-state invariants, wont-do tombstones, no status shortcut, fingerprint-based dedupe on rescan. |
| `F003-interrupt-during-persist` | interrupt | Models a crash mid-Step-9: index.json + in-flight.json atomically persisted but transitions.jsonl + CHANGELOG never appended, stale run.lock. Recovery must append exactly one retrofit transitions row keyed on the original timestamp, cite the interrupted run_id in the note, release the lock, and preserve all prior-day reports byte-identical. Invariants I1..I5 each independently verified load-bearing by `fault_inject.py`. |
| `F004-invented-type3-trap` | trap | Plants a GDPR consent-drift finding that naturally tempts `type='compliance'/'privacy'/'gdpr'` and TYPE3=`CMP`/`LEG`/`PRIV`. The correct answer uses canonical `type='security'` with regulatory specificity in `subtype` and prose. Catches field-invention and TYPE3-invention drift. |
| `F005-redaction-patterns-present` | trap | Plants 7 credential literals (stripe, aws, github, slack, jwt, private-key, generic-token) plus a structural-token trap (`token:` / `secret:` input names in a GitHub Action). All 7 literals must be redacted to the canonical `[REDACTED:*]` label; structural names must be preserved. No raw secret may appear anywhere in the `.audit/` tree, banner, or run_summary. |

Fault-injection harnesses accompany fixtures where the invariants are subtle (F003, F004, F005); they prove each invariant is load-bearing by mutating the clean output and confirming the mutation trips exactly the expected hard violation.

---

## Daily runbook

### Running a single fixture
```bash
cd evals/runs/YYYY-MM-DD/run-<timestamp>-<slug>/
python3 build.py                # produces .audit/ tree + capture.json + run_summary.json
python3 fault_inject.py         # if present — confirms each invariant is load-bearing
```
A green `build.py` should print `step_7_5_passed=true, 0 hard, 0 soft`. A green `fault_inject.py` should print `All I1..I5 invariants are load-bearing.` (or the analog for that fixture's invariant set).

### Checking baseline/registry consistency
```bash
python3 evals/scripts/coverage-sweep.py
```
Reports:
- **Problems** — any `fixtures_exercising[]` claim the baseline cells don't back up, any rule referenced in a cell but not registered, any rule referenced as active but actually inactive, any cell exercising rules not in the fixture's declared `exercises_rules[]`.
- **Notes** — rules with no fixture (coverage gaps) and active rules with zero passes (rule-survival risks).
- **Per-rule pass tally** — how many cells prove each rule load-bearing.

Run this after every baseline promotion and before every spec edit; problems must be zero.

### Promoting a new cell
1. Run the fixture end-to-end; confirm `capture.json` has `step_7_5_passed=true`, `hard_violation_count=0`.
2. Run the fault-injection harness if one exists; confirm all scenarios trip as expected.
3. Edit `baseline.json` to add/update the cell under `fixtures.<fixture-id>.cells.<model|ide|audit-md-hash>` with `run_ids`, `rules_exercised`, and a prose `notes`.
4. Update `last_promoted` / `promoted_by` on the top-level object and append a `history[]` entry with a `delta_summary`.
5. Run `coverage-sweep.py`; fix any problems it reports.
6. Have an independent auditor (or subagent) verify PASS by reading the emitted artifacts **without reading build.py or the harness** — this is what catches self-attested PASSes that don't actually reflect the artifacts.

### Adding a new rule
When a spec edit introduces a new behavioral rule:
1. Assign a `rule_id` at birth using the prefix legend in rule-registry.json (`R-` anti-drift, `S-` schema, `P-` procedure, `C-` config, `O-` output, `X-` anti-gaming).
2. Append a registry entry with `canonical_section_at_creation` AND `canonical_section_current` (initially equal; only `_current` changes if AUDIT.md is later reorganized), `gist`, `severity_class`, `fixtures_exercising` (empty list if none yet), `created_at`, and `anti_gaming_protected: true` if it's in the `X-` family.
3. If the rule is meant to be load-bearing, create or extend a fixture so at least one baseline cell has it as `pass`. Until that lands, `fixtures_exercising: []` is honest; listing a fixture that reports `not_exercised` is overclaiming.

### Adding a new fixture
1. Create `fixtures/F00N-<slug>/{repo/,fixture.yaml}` with a minimal repo + metadata.
2. Create `runs/YYYY-MM-DD/run-<ts>-<slug>/build.py` — a self-contained script that reads the seed fixture, produces `.audit/` + `capture.json` + `run_summary.json`, and runs Step 7.5 self-conformance in-process.
3. If the fixture's invariants are subtle (recovery, trap fixtures), add `fault_inject.py` that mutates each invariant and confirms the mutation trips.
4. Promote the cell per the runbook above.
5. Update every `rule_id` this fixture exercises with the new fixture name in its `fixtures_exercising[]`.

### Debugging a regression (baseline cell flips pass → fail)
1. Read the current run's `capture.json`. `violations[]` names each failed rule with an AUDIT.md §-quote and the offending artifact excerpt.
2. Cross-reference each failing `rule_id` against `rule-registry.json`'s `canonical_section_current` (the current location of the spec prose) — that's the live spec anchor. `canonical_section_at_creation` is the historical anchor for when the rule was born.
3. If the regression was triggered by a recent AUDIT.md edit, read `baseline.json`'s `history[]` to find the last green `audit_md_version`, then diff AUDIT.md between that fingerprint and now.
4. If the rule is `anti_gaming_protected: true`, ANALYZER.md HARD RULE 4 forbids weakening it — the edit must be reworked, not the rule.

---

## Invariants the harness itself must hold

These are enforced by `coverage-sweep.py`:

1. Every `rule_id` in any cell's `rules_exercised` must be in `rule-registry.json` with `status: active`.
2. Every fixture in a rule's `fixtures_exercising[]` must exist in `baseline.json` and have at least one cell where that rule reports `pass`.
3. Every rule exercised by any cell must be in that fixture's top-level `exercises_rules[]`.
4. Rule-survival: if a rule had ≥1 pass in any prior-baselined version, it must have ≥1 pass in the current version (enforced separately by `regression_policy.rule_survival_invariant`).

Currently documented coverage gaps (rules with `fixtures_exercising: []`): `O-mode-precedence-inline-over-env`, `C-budgets-respected`, `C-exclusions-respected`. All three have a `coverage_note` explaining the gap and the fixture candidate that would close it.

---

## Files at a glance

```
evals/
├── README.md                     ← this file
├── criteria.md                   ← pass/fail definitions
├── baseline.json                 ← fixture × cell × rule ledger (Layer-2 regression substrate)
├── rule-registry.json            ← stable rule_id registry
├── pe-best-practices.md          ← Layer-4 prompt-engineering scorecard
├── fixtures/
│   ├── F001-fresh-repo-small/
│   ├── F002-resume-existing-audit/
│   ├── F003-interrupt-during-persist/
│   ├── F004-invented-type3-trap/
│   └── F005-redaction-patterns-present/
├── runs/<date>/run-<ts>-<slug>/
│   ├── build.py                  ← scan implementation for this fixture
│   ├── fault_inject.py           ← invariant load-bearing proof (F003/F004/F005)
│   ├── capture.json              ← step_7_5_passed, hard/soft counts, per-rule pass/fail
│   ├── run_summary.json          ← §OUTPUT CONTRACT envelope
│   ├── banner.txt                ← HITL banner (§13)
│   └── .audit/                   ← emitted artifact tree
└── scripts/
    ├── capture-run.sh            ← wrap a manual scan into a captured run
    ├── run-baseline.sh           ← replay all fixtures
    ├── diff-vs-baseline.sh       ← compare a run vs baseline; aborts on fingerprint mismatch
    ├── promote-baseline.sh       ← write the new numbers into baseline.json
    └── coverage-sweep.py         ← integrity check of registry ↔ baseline ↔ fixtures
```

---

*Keep the three authoritative files consistent. Everything else is interpretable from them.*
