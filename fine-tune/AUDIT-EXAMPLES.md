# AUDIT-EXAMPLES.md — Review-only companion to AUDIT.md

This file holds illustrative examples and reference material for HUMANS
reviewing AUDIT.md outputs. It is **NOT** loaded into the agent prompt at
scan-time.

All contract definitions — rules, schemas, state machines, enforcement
semantics — live in AUDIT.md. This file only expands selected examples that
would otherwise bloat the agent's run-time context.

When AUDIT.md changes, this file MUST be reviewed for drift from the new
contract. A future F009 meta-fixture may formalize the drift check; for now
the check is manual and happens during the PE rubric pass.

**Current AUDIT.md fingerprint this file was synchronized against:**
`sha256:a3c86e129e0a6ca8a03a05b35c131722c022dd54162ec6205f939e757cde4f5d`

> Companion-file naming note: the historical findings report at
> `AUDIT-REVIEW.md` is the pre-v2 review time-capsule (pinned to
> `sha256:11ea48c9…`). This file uses `AUDIT-EXAMPLES.md` to avoid that
> collision; they are unrelated documents.

---

## Daily report worked example — Epic/Story/Task rendering

Rendered example of a single Epic → Story → Task chain as it appears in the
daily report, demonstrating the §ITEM SCHEMA and §Step 7.5a (SCHEMA.json
conformance) contracts in context. The YAML frontmatter, Run Log, HITL
Action Required banner, Findings heading, and sort/cross-day notes all live
inside AUDIT.md § DAILY REPORT LAYOUT and are not duplicated here — only the
item-level rendering is shown below.

````markdown
### EPIC AUD-2026-04-18-SEC-0001 — Harden authentication surface
- type: security · moscow: MUST · assignee: AGENT · reported: 2026-04-18 08:00 · status: PROPOSED

**Links**
- (epic-level; no parent)

---

#### STORY AUD-2026-04-18-SEC-0002 — Add CSRF protection to mutating routes
- type: security · moscow: MUST · assignee: AGENT · reported: 2026-04-18 08:00 · status: PROPOSED

**Links**
- Epic: `AUD-2026-04-18-SEC-0001`

---

##### TASK AUD-2026-04-18-SEC-0003 — Set SameSite=Lax on session cookie
- type: security · severity: high · moscow: MUST · assignee: AGENT · reported: 2026-04-18 08:00 · status: PROPOSED · last_updated: 2026-04-18 08:00

**5W1H2C5M**
- **What:** Session cookie missing SameSite → CSRF vector.
- **Why:** Browser default differs; cross-origin POST can carry the cookie.
- **Who:** All authenticated end-users.
- **When:** Before 2026-04-25 release.
- **Where:** `src/server/session.ts:42-48`
- **How:** Pass `{ sameSite: "lax", secure: true, httpOnly: true }`; add integration test.
- **Cost:** ~1h eng; risk low; blast radius single module.
- **Constraints:** Must not break OAuth callback on `/auth/callback`.
- **5M**
  - **Man:** 1 backend dev + peer review.
  - **Machine:** No infra change.
  - **Material:** No new deps.
  - **Method:** Direct edit + integration test asserting cookie attributes.
  - **Measurement:** Test passes; e2e login green; no new 4xx in staging.

**Evidence**
- `src/server/session.ts:42-48` — `res.cookie('sid', token)` (no options object).

**Links**
- Epic: `AUD-2026-04-18-SEC-0001` · Story: `AUD-2026-04-18-SEC-0002`

<!-- Links block (mandatory on every item — canonical spec in §Step 7.5a (SCHEMA.json conformance — Links labels)). Labels are LEVEL NAMES (Epic/Story), never "Parent:". Separator is " · " (U+00B7). IDs in backticks. -->

---

### EPIC AUD-2026-04-18-PRF-0007 — …
…
````

### Notes for reviewers

- The stub `### EPIC AUD-2026-04-18-PRF-0007 — …` at the end illustrates
  that the report is not one-epic-only: additional top-level epics repeat
  the same three-deep structure.
- Separator style `---` between same-level items is mandatory and comes
  from §ITEM SCHEMA. Do NOT change it here without updating the contract.
- The Links block is mandatory on every item at every level. At the epic
  level it reads `(epic-level; no parent)`; below epic level parents are
  labelled by level name (`Epic:`, `Story:`), never `Parent:`.
- IDs are backticked (`` `AUD-...` ``); the separator between Links entries
  is the interpunct `·` (U+00B7), flanked by spaces.

---

## Daily report frontmatter exemplar

Rendered exemplar of the YAML frontmatter + `# Repository Audit — …` heading
+ `## Run Log` + `## HITL Action Required` + `## Findings` intro as they
appear at the top of the daily report, showing all 17 `generated_runs[]`
fields and the five `counts` sub-maps in one place. AUDIT.md § DAILY REPORT
LAYOUT owns the enforcement surface (schema, section ordering, counts
derivation rule); this example shows the shape in a complete rendered
document.

````markdown
<!-- EXEMPLAR — your output should match this shape -->
---
schema_version: 1
report_date: 2026-04-18
generated_runs:
  # Each entry: ALL 17 fields (§Step 7.5a (SCHEMA.json conformance — generated_runs shape)). Same shape as the .json mirror — do not abbreviate.
  - run_id: "run-2026-04-18T08:00:01Z-a1b2"
    mode: "scan"
    trigger: "scheduled"
    scope: "."
    dry_run: false
    no_git: false
    truncated: false
    started_at: "2026-04-18T08:00:01Z"
    finished_at: "2026-04-18T08:01:47Z"
    files_scanned: 263
    scanners: ["security","performance","reliability","quality","architecture","dx","docs","ideas"]
    findings_new: 12
    findings_merged: 0
    findings_deduped: 3
    ok: true
    errors: []
    warnings: []
  - run_id: "run-2026-04-18T14:23:01Z-c3d4"
    mode: "scan"
    trigger: "manual"
    scope: "."
    dry_run: false
    no_git: false
    truncated: false
    started_at: "2026-04-18T14:23:01Z"
    finished_at: "2026-04-18T14:24:18Z"
    files_scanned: 263
    scanners: ["security","performance","reliability","quality","architecture","dx","docs","ideas"]
    findings_new: 6
    findings_merged: 5
    findings_deduped: 8
    ok: true
    errors: []
    warnings: []
counts:
  total: 23
  by_level:    { EPIC: 4, STORY: 8, TASK: 11 }
  by_moscow:   { MUST: 4, SHOULD: 7, COULD: 10, WONT: 2 }
  by_assignee: { AGENT: 16, HUMAN: 7 }
  by_status:   { PROPOSED: 18, APPROVED: 3, IN_PROGRESS: 0, DEFERRED: 1, WONT_DO: 1, REJECTED: 0, DONE: 0 }
# Every by_* map must sum to total. See "Counts aggregation rule" in §OUTPUT CONTRACT.
# All seven by_status keys are MANDATORY, even when zero (§Step 7.5a (SCHEMA.json conformance — counts derivation) + §OUTPUT CONTRACT counts derivation rule).
---

# Repository Audit — 2026-04-18

## Run Log
- 08:00 UTC — scheduled — 12 new, 0 merged, 3 deduped against history
- 14:23 UTC — manual    — 6 new, 5 merged, 8 deduped

## HITL Action Required
4 MUST task items pending review. To approve and execute: edit statuses below, then run with `MODE=execute`.

<!-- HITL count = task-only MUST+PROPOSED (see §REVIEW PROCEDURE). Phrasing MUST include "task". Empty state: literal sentence "No MUST task items pending review. All findings are SHOULD/COULD priority — no human action required to proceed." The heading is always present. -->

## Findings
> Sorted by reported_date ASC → assignee ASC → MoSCoW priority → id ASC.
> **Cross-day note:** because `reported_date` is the primary key and is calendar-day granular (YYYY-MM-DD), items naturally bucket by day in the sorted view — older days appear first, today's findings appear last within their day-bucket. Within a day-bucket, the secondary keys (assignee → moscow → id) determine order. Do NOT inject a "newest-first" override or sub-sort by `last_updated`; the four keys above are total and final.
````

The individual item-level rendering (Epic → Story → Task with full 5W1H2C5M,
Evidence, Links) continues at § "Daily report worked example — Epic/Story/Task
rendering" above.

---

## HITL banner exemplar

Rendered exemplar of the HITL banner that §13 prints before the Run Summary
on every `scan`. AUDIT.md § 13 owns the enforcement surface (heading, exact
format, empty-state rules, MANDATORY closing); this fence shows the fully
populated shape.

```
Audit complete — run-2026-04-18T14:23:01Z-c3d4
Report:        .audit/reports/2026/04/2026-04-18.md
Mirror (json): .audit/reports/2026/04/2026-04-18.json

Findings this run: 6 new · 5 merged · 8 deduped
Today total:       23 (MUST 4 · SHOULD 7 · COULD 10 · WONT 2)
Pending review:    18 PROPOSED

Top MUST items:
  1. AUD-2026-04-18-SEC-0003 — Set SameSite=Lax on session cookie
  2. AUD-2026-04-18-SEC-0011 — Rotate leaked Stripe key (commit a1b2c3d)
  3. AUD-2026-04-18-SEC-0014 — Add rate limit on /auth/login
  4. AUD-2026-04-18-PRF-0019 — Fix N+1 on /api/orders list

Next steps:
  • Review and update statuses in the report (or in index.json).
  • To execute approved AGENT items:    MODE=execute
  • To re-scan after changes:           (run again — same day appends)
```

---

## HITL banner empty-state renderings

Rendered empty-state variants called out by §13 § "Empty-state variants".
AUDIT.md owns the rules (when each variant applies and the MANDATORY closing
at the end of §13); the fences below show the literal rendered shapes.

### MUST empty form — zero MUST items in the entire index

```
Top MUST items:
  (none — no MUST findings in scope this run)
```

### Total empty form — zero items of any priority in the entire index

```
Today total:       0 (none)
```

(The `Pending review:` line has no separate fence — per §13, it simply
renders with a literal `0 PROPOSED` value when zero items are pending
review. The line must still appear.)

---

*End of AUDIT-EXAMPLES.md.*
