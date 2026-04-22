# Cross-model fixture runbook — Practice 5 → 5/5

**Goal.** Produce one new (model, ide) × F001–F008 cell matrix against the current `AUDIT.md` fingerprint, all `result=pass`, so `pe_scores.5_model_portability` can advance 4 → 5 in `fine-tune/evals/baseline.json`.

**Scope of this runbook.** You drive the 8 fixtures manually in any non-Claude IDE/CLI (Cursor, Google Antigravity, GitHub Copilot, Cline, Continue, Windsurf, Zed AI, etc.); Claude then collates the capture artifacts into a merge candidate and promotes. The only requirement on the IDE is that it can:

1. Send a prompt + attachments to a model of your choice.
2. Let you save the model's output files into a directory on disk.

If an IDE can do both, it works.

---

## 0. Decide model + IDE label (5 min)

- **Model.** Pick **one** model you'll hold constant across all 8 fixtures. Examples: `gpt-4.1`, `gemini-2.5-pro`, `deepseek-v3.1`, `llama-4-maverick`. Write it down exactly as you'll tag the cell — the `model` field in `capture.json` is a string and will be grep'd later.
- **IDE label.** Lowercase, no version — e.g. `cursor`, `antigravity`, `copilot`, `cline`, `continue`, `windsurf`, `zed-ai`. Optionally append `-<date>` if you want to freeze the tool version. Be consistent across all 8 captures.
- **Write both down.** Every `capture.json` uses them verbatim.

> If your IDE offers multiple model backends (Cursor does, Antigravity does), a "cell" is the (model, ide) pair. Using the same IDE with two different models = two separate cell runs.

---

## 1. Prep the workspace (one-time, 10 min)

1. Clone the repo onto the machine you'll run the IDE on. Point the IDE at the root (the one containing `AUDIT.md` and `fine-tune/`).
2. Verify the `AUDIT.md` fingerprint you're testing against:
   ```bash
   shasum -a 256 AUDIT.md
   ```
   Note the 8-char short form (e.g. `sha256:9ea04573`). If it differs mid-run, **stop** — the cells you've already captured are still valid, but new ones must wait for the next fingerprint.
3. Create a run-output root outside the fixture tree (so each fixture's `repo/` stays clean):
   ```bash
   mkdir -p fine-tune/evals/runs/$(date -u +%Y-%m-%d)/<ide>-<model>/
   ```

---

## 2. Run each fixture (repeat 8×, ~15–30 min each)

Same loop for F001–F007. F008 is a short-circuit — see §3.

### 2a. Open the fixture

```bash
cd fine-tune/evals/fixtures/F00N-<slug>/
cat fixture.yaml      # read `exercises_rules` and `invocation.prompt_template`
ls repo/              # this is what the model scans
```

### 2b. Drive the model in your IDE

Paste this prompt (adapted from `fixture.yaml → invocation.prompt_template`):

```
You are the AI Repository Audit Agent. Follow AUDIT.md EXACTLY — no paraphrase, no shortcut.

Repo to scan: fine-tune/evals/fixtures/F00N-<slug>/repo/
Output .audit/ tree to: fine-tune/evals/fixtures/F00N-<slug>/.audit-run-<RUN_ID>/

Constraints:
- temperature=0.0 (or lowest supported); seed=42 if the model takes one
- Do not invent TYPE3 codes. Use the closed 12-code set in AUDIT.md.
- Apply §EVIDENCE REDACTION to every persisted artifact.
- Emit Step 7.5 self-conformance section with hard_violation_count and soft_violation_count.
- Stop when the .audit/ tree is written. Do not ask follow-up questions.

AUDIT.md is the full spec — read it first and conform to it.
```

Attach **both** of these into the model's context (exact attach mechanism depends on IDE — file-pin, @mention, context-upload, or paste):

- `AUDIT.md` (the spec — always)
- The fixture's `repo/` tree (the target)

Additional attachments per fixture:

- **F002** — also attach `fixtures/F002-resume-existing-audit/seed/.audit/` as the prior-state.
- **F003** — also attach its `.audit/` seed in the interrupted-mid-Step-9 shape.

### 2c. Capture the run

When the model finishes:

1. Copy the `.audit/` output tree to `fine-tune/evals/runs/YYYY-MM-DD/<ide>-<model>/F00N-<slug>/`.
2. Run the Step 7.5 self-conformance checker on the output. Easiest route: find the closest reference implementation under `fine-tune/evals/runs/*/run-*-f00N*/build.py` and reuse its Step 7.5 checker block — most of those `build.py` files end with an in-process 7.5 validation that prints `step_7_5_passed=true/false, N hard, M soft`.
3. Write a `capture.json` alongside the copied output. Minimal shape (8 canonical top-level keys):

   ```json
   {
     "run_id": "ft-<UTC-ISO>-<4chars>",
     "fixture": "F00N-<slug>",
     "model": "<model-string>",
     "ide": "<ide-label>",
     "audit_md_version": "sha256:<full-64-hex>",
     "result": "pass",
     "hard_violation_count": 0,
     "soft_violation_count": <observed>,
     "step_7_5_passed": true,
     "rules_exercised": {
       "<rule_id from fixture.yaml exercises_rules>": "pass"
     },
     "violations": [],
     "invariants": [
       {"text": "<invariant description>", "result": "pass", "evidence": "<where/how observed>"}
     ],
     "notes": "Manual <ide> run; temp=0 seed=42 (if supported)."
   }
   ```

   The `rules_exercised` map must include **every** `rule_id` in that fixture's `exercises_rules[]` in `fixture.yaml`. Value is `pass` / `fail` / `not_exercised`. Use `fine-tune/evals/rule-registry.json` to resolve §3.x labels in `fixture.yaml` to canonical `rule_id`s (most §3.x labels map 1:1; e.g. §3.j → `R-anti-drift-type3-closed-set`, §3.m → `R-anti-drift-mirror-state-invariants`). If unsure, dump the registry and grep by `canonical_section_at_creation`.

   `invariants[]` must be an array of `{text, result, evidence}` objects — not a bare-boolean dict (that's a drift class that coverage-sweep catches via `R-anti-drift-invariants-cite-evidence`).

### 2d. Pass criteria (from `fine-tune/evals/criteria.md`)

Your cell is a **pass** only if ALL of these hold (short form):

- Step 7.5 reports zero hard violations.
- `state/index.json` and `daily/YYYY-MM-DD.json` agree on the sorted ID set.
- `state/index.json` root is a **bare array** — not a dict-wrapped shape.
- Every `id` matches `^AUD-(SEC|PRF|REL|QLT|ARC|DEV|DOC|INF|FEA|IDA|REF|TST)-[0-9]{4}$`.
- Every `fingerprint` is `sha256:` + 64 hex — never a semantic slug, placeholder, or zero-hash.
- Every `history[]` entry has exactly `{ts, from, to, by, note}`.
- No invented top-level keys on items (19-key CLOSED set per `R-anti-drift-item-top-keys-closed`).
- Evidence redaction applied — no emails, tokens, SSH keys in any artifact.
- Status values only from the 7-value state machine.
- No helper / generator / revert scripts left at repo root.
- For fault-injection fixtures (F003/F004/F005): also run `fault_inject.py` if present and confirm all invariants trip.

If any of those fails: set `result=fail`, populate `violations[]` with the failing `rule_id` + quote from `AUDIT.md` + offending excerpt. **Don't fudge — a clean fail is more useful than a fake pass.**

### 2e. Fixture-specific gotchas

- **F001 (fresh).** Bootstrap must be performed: README, CHEAT-SHEET, troubleshooting, `fine-tune/SCHEMA.json` if referenced.
- **F002 (resume).** Agent must NOT invent new IDs for items already fingerprinted; NNNN counter continues per day.
- **F003 (interrupt).** Agent detects mid-Step-9 crash and recovers by appending one retrofit transitions row keyed on original ts — does NOT delete items to pass.
- **F004 (trap).** The seeded GDPR finding MUST classify as `type='security'` with `subtype`, NOT as invented `CMP`/`LEG`/`PRIV`.
- **F005 (redaction).** All 7 credential literals redacted; structural names (e.g. `token:` input names) preserved.
- **F006 (config).** Budget + exclusion precedence behaviors verified; `transitions.jsonl` emits the 8-key canonical shape, not a 6-key CRM/ticket shape.
- **F007 (schema).** `SCHEMA.json` conformance across emitted artifacts.

---

## 3. F008 short-circuit

F008 is a meta-fixture — it parses `AUDIT.md §Step 7.5` for 8 sub-block coverage. Its rules:

- `S-step-7-5-sub-block-coverage` — static `AUDIT.md` property, model-independent.
- `P-step-7-5-self-conformance` — model-dependent (does the model emit the self-conformance section correctly when scanning).

For your cell:

- `S-step-7-5-sub-block-coverage: pass` — trivially, since `AUDIT.md` hasn't changed.
- `P-step-7-5-self-conformance: pass` iff your F001 run emitted a Step 7.5 section with zero hard violations.

Write F008 `capture.json` by hand; no separate model run needed.

---

## 4. Hand everything back to Claude

When all 8 `capture.json` files exist, tell Claude:

- Model string + IDE label you used.
- Paths to all 8 `capture.json` files (or just paste their contents).
- Any soft violations or notes worth remembering.

Claude will:

1. Build a single merge candidate with 8 upserts (one per fixture).
2. Dry-run `fine-tune/evals/scripts/apply-merge-candidate.py`; apply in-place.
3. Patch `pe_scores.5_model_portability` 4 → 5 in `baseline.json`, `total` 79 → 80, `ratio` → 1.0, `audit_md_version` unchanged.
4. Run `fine-tune/evals/scripts/coverage-sweep.py` → expect PROBLEMS: none.
5. Refresh `.auto-memory/audit_md_project_state.md` with the new PE ceiling.

If any cell failed, don't throw it out — failed cells are evidence too. Claude will write a failure-annotated candidate and you decide whether it's a spec bug (fix `AUDIT.md`) or a model limitation (document as known-limitation and still promote the passing cells).

---

## 5. Time estimate

- Setup: 15 min.
- Per fixture: 15–30 min model-drive + 5 min capture.
- 8 fixtures × 20 min = ~2.5–3 hours total.
- Merge + promote: ~10 min Claude-side.

Full 4h session to get Practice 5 to 5/5, PE to 80/80.

---

## 6. Invariants you must NOT violate while running

These apply to the spec itself, not just model output. Don't let a manual edit slip in:

- **No `AUDIT.md` edits during the run.** If you find a bug, note it and fix it in a *separate* cycle — not during capture.
- **No hand-editing `baseline.json` cells.** Route everything through `fine-tune/evals/scripts/apply-merge-candidate.py`.
- **Rule-survival invariant.** Every rule with ≥1 prior pass must retain ≥1 pass. If your new cells fail a rule that another cell passes, the rule still survives. If your new cells *pass* a rule that's currently unexercised, that's a coverage gain — flag it in the merge candidate `review_checklist`.

---

*End of runbook.*
