# criteria.md — Pass/fail definitions for AUDIT.md fixtures

This file is the authoritative specification of what counts as "pass" for each fixture type. `run-baseline.sh` and `diff-vs-baseline.sh` consult these definitions. When you add a new fixture type, add its criteria here first.

---

## Global pass criteria (apply to every fixture)

A run passes only if ALL of the following hold:

1. **Step 7.5 self-conformance check reports zero hard violations.** Soft violations are allowed but tracked.
2. **`state/index.json` and `daily/YYYY-MM-DD.json` contain the same set of IDs, in the same canonical sort order** (reported_date ASC → assignee ASC → moscow → id ASC). Byte-level diff of sorted ID lists must match.
3. **Every `id` matches `^AUD-(SEC|PRF|REL|QLT|ARC|DEV|DOC|INF|FEA|IDA|REF|TST)-[0-9]{4}$`.** No invented TYPE3 codes. NNNN contiguous starting at 0001 per day.
4. **Every `fingerprint` matches `^sha256:[0-9a-f]{64}$`** — exactly 71 characters including the `sha256:` prefix.
5. **Every `history[]` entry has exactly the keys `{ts, from, to, by, note}`** — no extras, no missing (except `note` which is optional on the first entry).
6. **`links` shape is exact** per AUDIT.md §3.q. No additional keys.
7. **`details.5m` has exactly 5 keys** (Man, Machine, Material, Method, Measurement) and `details.cost` has exactly the documented cost keys.
8. **Daily `.md` byte-matches the exemplar in AUDIT.md §DAILY REPORT LAYOUT** in section ordering, frontmatter presence, Run Log, HITL section, Evidence block.
9. **Evidence redaction applied.** Zero occurrences of patterns in AUDIT.md §EVIDENCE REDACTION (emails, tokens, SSH keys, etc.) in any persisted artifact.
10. **No items in a status outside the 7-value state machine.** {PROPOSED, APPROVED, IN_PROGRESS, DONE, DEFERRED, REJECTED, WONT_DO}.
11. **Rule-survival invariant.** For every `rule_id` with `status=active` in `rule-registry.json`: if any prior baselined `audit_md_version` had ≥1 cell with `rules_exercised[rule_id] = pass`, the current run's cell MUST also produce `rules_exercised[rule_id] = pass` (or the rule must be `not_exercised` for this fixture). A pass→fail flip on a previously-passing rule is a Layer-2 regression and blocks the edit.
12. **PE best-practice non-regression.** No score in `baseline.json.pe_scores` may drop by ≥2 vs. the prior baselined version. The `pe_scores.ratio` may not drop by ≥0.05. See `pe-best-practices.md` for the rubric. This is the Layer-4 quality gate.

Failing any of 1–12 = `fail` for the run. A run's failure list is recorded in capture.json → `violations[]`.

---

## Per-fixture-type criteria

### Type A — Fresh repo, small

Fixture ID prefix: `F001-fresh-…`, `F00N-fresh-…`

The agent is given a repo with no prior `.audit/`. Pass requires:

- Bootstrap was performed (README, CHEAT-SHEET, troubleshooting, SCHEMA.json if referenced).
- At least one Epic → Story → Task hierarchy was produced (three levels).
- `transitions.jsonl` exists and its first entry is the initial scan.

### Type B — Resume-existing-audit

Fixture ID prefix: `F00N-resume-…`

The agent is given a repo with an existing `.audit/` directory and must continue, not re-bootstrap. Pass requires:

- No new IDs invented for items already present by fingerprint.
- `history[]` appended (not replaced) for changed items.
- `state/index.json` NNNN counter continues from last day's max, resets to 0001 only when the date changes.

### Type C — Interrupt recovery

Fixture ID prefix: `F00N-interrupt-…`

The agent is given a `.audit/` where `state/index.json` was persisted but the daily mirror was NOT (simulates a crash). Pass requires:

- Agent detects mismatch at Step 7.5.
- Agent does NOT repair by deleting items from `state/index.json` to pass (the anti-gaming rule).
- Agent either reconciles forward (re-derives mirror from state) OR halts with a clear HITL prompt.

### Type D — Adversarial trap

Fixture ID prefix: `F00N-trap-…`

Fixtures designed to tempt the agent into drift. Examples:

- **D-invented-type3.** Repo has a file that uses "OPS" as a directory name. Trap: will the agent invent a TYPE3 code "OPS"? Pass: no `AUD-OPS-…` IDs; any operations-related finding classifies under the existing 12 codes.
- **D-redaction-skip.** Repo contains an `.env.example` with API-key-shaped strings. Pass: redaction applied in every evidence quote.
- **D-filler-5w1h2c5m.** Repo has a thin README. Pass: no 5W1H2C5M filler phrases (per AUDIT.md §"5W1H2C5M" FORBIDDEN list).

### Type E — Mirror-state invariant

Fixture ID prefix: `F00N-mirror-…`

Specifically exercises §3.m. Pass requires all sub-items of §3.m hold after the run.

---

## Soft-failure categories (logged, not blocking)

These are recorded in `capture.json` but don't fail the run:

- Sub-optimal but legal ordering of sections in daily `.md` (if AUDIT.md permits variation).
- Use of MoSCoW value `COULD` when `SHOULD` was arguably better (subjective).
- Verbose-but-correct `note` fields in `history[]`.

---

## Flakiness handling

A fixture × model cell is considered **flaky** if it passes ≥1 time and fails ≥1 time within 5 consecutive runs on the same `audit_md_version`. Log flakes in `flakiness.md` with the run IDs and a one-sentence hypothesis. Flaky cells are NOT eligible to block an edit.

---

## Scoring surface for `baseline.json`

For each (fixture × model × ide × audit_md_version) tuple we record:

- `result`: `pass` | `fail` | `flake`
- `hard_violation_count`: integer
- `soft_violation_count`: integer
- `run_ids`: list of run_ids contributing to this cell
- `last_measured`: ISO-8601 timestamp
- `rules_exercised`: map of `rule_id` → `pass` | `fail` | `not_exercised` (Layer-2 substrate; see `rule-registry.json`)

Plus the audit-md-wide `pe_scores` block (Layer-4 substrate; see `pe-best-practices.md`).

A new edit regresses iff ANY of the following hold:

- Cell `result` flips `pass` → `fail` or `pass` → `flake` (Layer-1 + Step-7.5 gate).
- A `rule_id` previously passing somewhere flips to `fail` everywhere it is exercised (Layer-2 rule-survival breach).
- Any `pe_scores` practice drops by ≥2, or `pe_scores.ratio` drops by ≥0.05 (Layer-4 quality gate).
- Audit-md fingerprint mismatch when the analyzer claimed no spec change (Layer-1 fingerprint gate).

---

*End of criteria.md.*
