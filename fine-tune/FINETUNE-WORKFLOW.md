# AUDIT.md — Fine-Tune Workflow

A continuous-improvement loop for AUDIT.md that runs alongside your normal development. You scan repos with multiple model/IDE combinations during your real work; Claude analyzes the resulting `.audit/` artifacts and proposes targeted edits to AUDIT.md; you approve or reject each proposed edit. The prompt improves over time without manual rule-mining and without growing unboundedly.

**Yes, this is possible** — and the design below is structured exactly the way AUDIT.md itself is structured (HITL approval, append-only history, fingerprinted findings, no auto-merge). You will recognize the loop.

---

## The loop in one diagram

```
┌─ DURING YOUR WORK ───────────────────────────────────────────────┐
│                                                                   │
│  Repo A ─[Cursor + Sonnet]─►   .audit/  ──┐                       │
│  Repo B ─[Copilot + GPT-5]─►   .audit/  ──┤                       │
│  Repo C ─[Gemini]─────────►    .audit/  ──┤  scan artifacts       │
│  Repo D ─[Cline + Haiku]──►    .audit/  ──┤                       │
│                                            │                       │
└────────────────────────────────────────────┼───────────────────────┘
                                              │
                                              ▼
┌─ ANALYSIS PASS (you trigger when ready) ────────────────────────┐
│                                                                   │
│  Cowork + ANALYZER.md  ←──  reads:  AUDIT.md (current)            │
│                                     .audit/ artifacts (per run)   │
│                                     evals/runs/ (history)         │
│                              writes: evals/runs/<run-id>.json     │
│                                     PROPOSED-EDITS-<date>.md      │
│                                                                   │
└────────────────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
┌─ HUMAN REVIEW (you, ~10-30 min/week) ───────────────────────────┐
│                                                                   │
│  Open PROPOSED-EDITS-<date>.md.                                   │
│  Each proposed edit has: status: PROPOSED  →  APPROVED / REJECTED │
│  Set the ones you want.                                           │
│                                                                   │
└────────────────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
┌─ APPLY PASS (Cowork + ANALYZER.md mode=apply) ──────────────────┐
│                                                                   │
│  Apply only APPROVED edits to AUDIT.md.                           │
│  Bump AUDIT.md's schema_version comment (record run-id).          │
│  Re-run eval harness against fixtures/.                           │
│  If pass-rate regressed → revert + log.                           │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## The four invariants that make this safe

These are non-negotiable. Drop any one and the loop becomes a slow self-poisoning system.

1. **Every proposed edit is grounded in a concrete drift incident.** No edit is allowed without a pointer to a specific run, a specific artifact, and a specific failed assertion. The analyzer enforces this.
2. **The human approves every edit.** AUDIT.md mirrors this with its `assignee=AGENT AND status=APPROVED` gate; the loop on AUDIT.md itself uses the same gate. There is no "auto-merge if Claude is confident".
3. **Every edit must pass the eval harness before it lands.** A regression in pass-rate against the fixture repos is a hard block — the edit is reverted and logged for re-thinking, never merged on faith.
4. **No edit deletes or weakens an existing rule unless that rule has zero violations in the last N runs AND the eval pass-rate doesn't move when it's removed.** "Last violation: never seen" is not enough; the rule has to actually not be load-bearing.

---

## What gets captured per scan

For every scan you run on every repo with every model/IDE, you capture a small JSON summary. Most of this is already in the `.audit/` outputs — you just need a thin wrapper that aggregates it for the analyzer.

```jsonc
// evals/runs/2026-04-21-cursor-sonnet-repoA.json
{
  "run_id": "ft-2026-04-21T10:14:01Z-a1b2",
  "audit_md_version": "sha256:9b1c…",   // fingerprint of AUDIT.md at scan time
  "model_id": "claude-sonnet-4.5",       // the model that interpreted AUDIT.md
  "ide_id": "cursor-0.43",
  "repo_id": "repoA",                     // human-friendly repo nickname
  "repo_fingerprint": "git-sha-of-HEAD",
  "scan_started_at": "2026-04-21T10:14:01Z",
  "scan_finished_at": "2026-04-21T10:16:33Z",
  "audit_dir": ".audit/",                 // path snapshot copied into evals/runs/<run-id>/audit/
  "step_7_5_passed": false,
  "violations": [
    { "check": "3.m.1", "severity": "hard",
      "evidence": "mirror items[]=9, state items[]=10",
      "drift_pattern": "mirror-state desync" },
    { "check": "21",    "severity": "hard",
      "evidence": "tasks SEC-0003 and PRF-0007 share identical 5W1H2C5M block",
      "drift_pattern": "5W1H2C5M filler" }
  ],
  "warnings": [
    { "kind": "low_yield", "total_findings": 4, "floor": 8 }
  ],
  "files_scanned": 187,
  "total_findings": 12,
  "by_level": { "EPIC": 2, "STORY": 4, "TASK": 6 },
  "notes": "Free-form: anything weird the human noticed."
}
```

Two things matter here:

- **`audit_md_version`** is a fingerprint of the AUDIT.md the agent read. You want this so when you analyze drift across runs, you can ask: "did this drift happen on the OLD AUDIT.md or the NEW one?" — and you can tell whether your last edit actually fixed something.
- **`model_id` + `ide_id`** are how you slice the data. Sonnet might never violate `3.m.1` while Gemini violates it 60% of the time. That's information about *the rule's wording*, not just the model — the rule may need a more concrete example, or may need to be moved earlier.

The thin wrapper that produces this file is in `fine-tune/evals/scripts/capture-run.sh` (skeleton in `fine-tune/evals/`).

---

## What the analyzer pass does

You hand Claude (in Cowork) the current AUDIT.md, the latest `fine-tune/evals/runs/*.json` files since the last analysis pass, and `ANALYZER.md` as the instruction. Claude does six things, in order:

1. **Aggregate by drift pattern.** Group violations by the `check` field and the `drift_pattern` field. Count per model, per IDE, per AUDIT.md version. Output a drift heatmap.
2. **Identify regressions.** Any violation that occurred in this analysis window AND that AUDIT.md was specifically edited to prevent (per the `fine-tune/evals/runs/edits-applied.jsonl` log) is a regression — flag it loudly.
3. **Identify new patterns.** Any violation not covered by an existing §3 sub-rule, or covered weakly (no example, no anti-pattern shown), is a new pattern. These are the highest-priority candidates for new rules.
4. **Identify stale rules.** Any §3 sub-rule with `last_seen_violation: > 90 days ago` AND no violations in the latest window is a candidate for retirement.
5. **Identify duplications introduced by recent edits.** Run the duplication scanner from `AUDIT-REVIEW.md` to catch any new restatement — proposed edits should never re-introduce duplication.
6. **Propose edits.** For each issue, output a concrete edit: target section, exact replacement text, before/after diff, rationale, and a fingerprint of the source incidents.

Output goes to `PROPOSED-EDITS-<date>.md` with one section per proposed edit, each with a `status: PROPOSED` line ready for you to flip. Same shape as a daily audit report — you already know how to review it.

---

## Handling model disagreement

Different models will violate AUDIT.md in different ways. This is signal, not noise.

| Pattern | What it means | What to do |
|---|---|---|
| One model violates a rule the others follow | The rule wording isn't precise enough for that model — likely missing a concrete WRONG example or buried too deep | Add a WRONG/RIGHT example block; consider promoting the rule earlier in the file |
| All models violate the same rule | The rule is fundamentally unclear OR your scan invocation is leaving the rule out of context | Rewrite the rule; check if AUDIT.md is being truncated by the IDE before reaching the model |
| Only the cheapest/smallest model violates | The rule needs explicit examples that scaffold weaker reasoning | Add examples; do NOT add to the rule's prose length unnecessarily |
| Newer models violate a rule older models followed | Likely an alignment shift or a context-window / formatting change in the IDE | Investigate before patching; the prompt may not be the right place to fix |

The analyzer should report drift broken down by model so you can spot all four patterns.

---

## How edits are applied (and reverted)

The analyzer outputs a unified diff for every proposed edit. The apply pass:

1. Reads `PROPOSED-EDITS-<date>.md` and selects only items with `status: APPROVED`.
2. Applies the diffs in order. If any diff fails to apply (context mismatch), it stops — does not partially apply, does not "best-effort" merge.
3. Bumps the `<!-- audit_md_version: sha256:… -->` header comment in AUDIT.md.
4. Logs the run in `fine-tune/evals/runs/edits-applied.jsonl`:
   ```json
   {"ts":"2026-04-21T16:00:00Z","run_id":"ft-…","applied_edit_ids":["edit-001","edit-003"],"old_fingerprint":"sha256:…","new_fingerprint":"sha256:…","analysis_window":["2026-04-14","2026-04-21"]}
   ```
5. Runs the eval harness against `fine-tune/evals/fixtures/` with the new AUDIT.md.
6. **If the conformance pass-rate dropped on any fixture, revert immediately** (`git revert` the AUDIT.md edit), record the regression in `fine-tune/evals/runs/regressions.jsonl`, and surface it in the next analyzer pass for re-thinking.
7. Otherwise commit AUDIT.md with a message linking the analysis window and the approved edit IDs.

This is exactly the same `PROPOSED → APPROVED → IN_PROGRESS → DONE | REVERTED` shape as AUDIT.md's state machine, applied to AUDIT.md itself.

---

## Cadence

You don't run the loop on every scan. You run it on a window. Suggested:

- **Capture per scan** (cheap — just write the JSON wrapper): every audit run.
- **Analyzer pass** (Claude run, ~5-15 min): weekly, or when you've accumulated ~10–20 runs across diverse models.
- **Apply pass + eval rerun** (~10 min): after each analyzer pass that produced approved edits.
- **Major consolidation** (renumber §3, retire stale rules, schema extraction per `AUDIT-REVIEW.md`): quarterly. This is the only point where you should consider *deleting* rules; otherwise the loop is purely additive (with rare retirement of zero-violation rules).

---

## Applying prompt-engineering best practices over time

The loop above keeps AUDIT.md *correct against observed drift*. The other half of "still optimal" is keeping it well-engineered as the field's best practices evolve. Bake this into the analyzer:

After each analyzer pass, the analyzer also runs a **best-practices audit** against AUDIT.md using the rubric below. Any violation produces a proposed edit alongside the drift-driven ones.

| Best practice | What the analyzer checks |
|---|---|
| Specificity over abstraction | Every behavioral rule has at least one concrete WRONG and RIGHT example |
| Front-loaded safety | Refusal contracts and anti-drift rules appear before procedural detail |
| One canonical home per concept | No concept stated in 3+ places (run the duplication scanner from AUDIT-REVIEW.md) |
| Data vs. behavior separation | Pure-data tables (enums, regex sets, threshold tables) live in `fine-tune/SCHEMA.json` / `config.yaml` — not the prompt |
| Closed sets are explicit | Every "must be one of" list is enumerated with the literal allowed values |
| Negative examples | High-stakes rules show a forbidden output shape, not just the conforming one |
| Internal cross-references | Every "see §X" pointer resolves to an existing section heading (broken refs are bugs) |
| Section ordering | Content is ordered roles → contracts → operating modes → procedures → schemas → reference, not interleaved |
| Token budget | Total prompt size hasn't grown more than 5% per quarter without proportional capability gain (measured by eval pass-rate) |

The analyzer reports a "best-practices score" each pass. A drop in the score is a signal to schedule a consolidation pass, even if no drift is occurring.

---

## What this gives you (and what it doesn't)

**It gives you:**

- A self-improving prompt that gets sharper every week without requiring you to manually mine logs.
- A regression net (the eval harness) that prevents bad edits from sticking.
- A diverse evidence base (multiple models / IDEs / repos) that finds drift no single model would surface.
- An audit trail (`fine-tune/evals/runs/edits-applied.jsonl` + regressions log) that lets you reason about *why* AUDIT.md looks the way it does in 6 months.

**It doesn't give you:**

- **A free lunch on size growth.** The loop will still grow AUDIT.md slowly unless you also schedule the quarterly consolidation pass. Detection of growth is automatic; the decision to retire a rule is yours.
- **Coverage of rules nobody triggers.** You only learn about rules that get violated. A rule that prevents catastrophic but rare drift will never show up in the analyzer's output. Document those rules explicitly as "intentional dark coverage" so you don't retire them in the consolidation pass.
- **Cross-prompt-version comparability without the version fingerprint.** If a scan run isn't tagged with its `audit_md_version`, it can't be assigned to a window — discard it from the eval set, don't guess.

---

## File layout summary

```
code-audit/                              # repo root (3 files only)
├── AUDIT.md                             # the spec under continuous improvement
├── README.md                            # step-by-step fine-tune guide (Path A + Path B)
├── .gitignore
└── fine-tune/
    ├── AUDIT-EXAMPLES.md                # review-only companion (fingerprint-pinned)
    ├── ANALYZER.md                      # the meta-prompt
    ├── CROSS-MODEL-RUNBOOK.md           # generic cross-IDE cross-model fixture sweep
    ├── FINETUNE-WORKFLOW.md             # this file
    ├── AUDIT-CONFIG.md                  # customizable variable documentation
    ├── PROMPT-INVOCATION.md             # trigger prompts + determinism gotchas
    ├── SCHEMA.json                      # 12 pure-data blocks extracted from AUDIT.md
    ├── templates/                       # template files referenced by AUDIT.md
    ├── proposals/                       # queued proposal designs
    ├── proposal-history/                # archived APPLIED-*.md files
    └── evals/
        ├── README.md                    # eval harness overview
        ├── criteria.md                  # what counts as pass / fail
        ├── pe-best-practices.md         # 16-practice rubric (1–5 each)
        ├── rule-registry.json           # active rules with frozen creation fingerprints
        ├── baseline.json                # pass-rate baseline per fixture × model × IDE
        ├── fixtures/                    # F001..F008 representative fixture repos
        │   └── F00N-*/build.py, seed/
        ├── runs/<date>/<ide-model>/     # per-run artifacts (scans + analyzer output)
        │   └── edits-applied.jsonl      # append-only edit history
        └── scripts/
            ├── promote-baseline.sh      # blessed path for baseline.json mutations
            ├── apply-merge-candidate.py # apply merge candidate + rolling .bak-*
            ├── coverage-sweep.py        # integrity check registry ↔ baseline ↔ fixtures
            ├── run-baseline.sh          # harness wrapper
            └── capture-run.sh, diff-vs-baseline.sh, flake-check.sh
```

All fine-tune-loop collateral lives under `fine-tune/`. The repo root intentionally holds only `AUDIT.md`, `README.md`, and `.gitignore` so the spec under audit is the first thing a reader sees.

---

*End of FINETUNE-WORKFLOW.md.*
