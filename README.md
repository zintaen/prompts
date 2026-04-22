# AUDIT.md — self-auditing repo-audit prompt, with a regression harness

> **Visitor-friendly overview:** open `index.html` in a browser for a visual tour — what `AUDIT.md` is, its structure (three-file tripod, rule families, fixtures), how to run it on any repo, and how to fine-tune it safely.
>
> **This README** is the developer-facing fine-tune guide — how to run cycles, keep the regression harness green, and extend the PE rubric.

`AUDIT.md` is a large, opinionated LLM-run codebase auditor. This repo holds:

1. The spec itself — `AUDIT.md` at the root, ~150 KB of canonical rules.
2. Everything needed to fine-tune it safely — under `fine-tune/`.
3. A visitor-facing site — `index.html` at the root.

The fine-tune loop is designed so every edit is grounded in a real drift incident, goes through a proposed-edit queue you review, and is gated by a regression harness that blocks a merge if any previously-passing rule × fixture cell flips to fail. `AUDIT.md`'s own Human-In-The-Loop (HITL) contract is mirrored in how the spec itself evolves.

---

## Repo layout

```
AUDIT.md              ← source of truth (the prompt)
README.md             ← this file (fine-tune guide)
.gitignore
fine-tune/            ← everything needed to fine-tune AUDIT.md
  ├── SCHEMA.json                  authoritative data (closed sets, patterns)
  ├── templates/                   CHEAT-SHEET / TROUBLESHOOTING inlined on bootstrap
  ├── AUDIT-CONFIG.md              configurable vars + § notation
  ├── FINETUNE-WORKFLOW.md         loop design in depth
  ├── PROMPT-INVOCATION.md         prompt templates for invoking the auditor
  ├── ANALYZER.md                  drift-analysis meta-prompt (analyzer pass)
  ├── CROSS-MODEL-RUNBOOK.md       IDE-agnostic runbook for Practice-5 cross-model runs
  ├── AUDIT-EXAMPLES.md            fingerprint-pinned worked examples (review-only)
  └── evals/                       regression harness
      ├── baseline.json            fixture × model × IDE pass/fail matrix
      ├── rule-registry.json       canonical rule list (id, section, fixtures)
      ├── criteria.md              per-cell pass criteria
      ├── pe-best-practices.md     16-practice prompt-engineering rubric
      ├── README.md                harness internals
      ├── fixtures/                F001–F008 (8 deterministic fixtures)
      ├── scripts/                 apply/promote/coverage/flake checks
      └── runs/                    historical captures + merge candidates
```

All commands in this README assume you're `cd`'d to the repo root.

---

## The three-file tripod

The harness lives on three tightly-coupled files that must stay consistent:

| File | Role |
|---|---|
| `AUDIT.md` | The spec — source of truth. Every editable behavior lives here. |
| `fine-tune/evals/rule-registry.json` | Every enforceable rule has a stable `rule_id`, a canonical § section in `AUDIT.md`, a birth fingerprint, and a list of fixtures that exercise it. |
| `fine-tune/evals/baseline.json` | Per-cell (`fixture × model × IDE`) pass/fail ledger at the current `AUDIT.md` fingerprint. Plus the 16-practice PE rubric score. |

A spec edit is safe only if **all three** get updated together. The `coverage-sweep.py` script enforces consistency.

---

## Quick start (any machine, any IDE)

Clone and verify:

```bash
git clone <this-repo> && cd code-audit   # or whatever you named the folder
shasum -a 256 AUDIT.md                   # note the fingerprint
python3 fine-tune/evals/scripts/coverage-sweep.py   # should report PROBLEMS: none
```

If `coverage-sweep` reports `PROBLEMS: none`, the baseline is consistent with the registry and you're ready to fine-tune.

---

## Two ways to fine-tune

### Path A — Autonomous (Claude desktop / Cowork mode)

The simplest path. Claude reads the current state, proposes an edit, applies it with your approval, re-fingerprints, re-runs the regression, and updates the baseline — all in one session.

1. Open Claude desktop (Cowork mode) in this folder.
2. Ask something like:

   > *"Run one fine-tune cycle on AUDIT.md. Target: lift Practice 6 (few-shot examples) from 4/5 to 5/5 in the PE rubric. Propose the edit, show me, apply on approval, re-run regression, update baseline."*

3. Claude will:
   - Read `AUDIT.md`, `rule-registry.json`, `baseline.json`, and `pe-best-practices.md`.
   - Identify the concrete gap (what a 5/5 for Practice 6 requires that a 4/5 doesn't).
   - Draft a `PROPOSED-EDITS-<date>-<scope>.md` with exact WRONG/RIGHT before/after snippets.
   - Pause for your approval.
   - On approval: apply the patch, bump the `AUDIT.md` sha256 fingerprint, update `AUDIT-EXAMPLES.md` header pin, build a baseline merge candidate via `apply-merge-candidate.py`, run `coverage-sweep.py`.
   - Refresh `.auto-memory/audit_md_project_state.md` with the new cycle.

Worked examples of past cycles are in `fine-tune/evals/runs/baseline-merge-candidate-*.json`.

### Path B — Manual (any CLI / IDE)

Use this when you want to drive the audit with a non-Claude model — Cursor + GPT-4.1, Antigravity + Gemini, Copilot, Cline, Continue, Windsurf, Zed AI, etc. This path is how you earn PE Practice 5 (cross-model portability).

Follow `fine-tune/CROSS-MODEL-RUNBOOK.md` end-to-end. Short version:

```bash
# 1. Pick a model + IDE label (held constant across 8 fixtures).
# 2. For each fixture F001…F008:
cd fine-tune/evals/fixtures/F00N-<slug>/
cat fixture.yaml   # read the prompt template and exercises_rules
# Drive the model in your IDE with AUDIT.md + repo/ attached.
# Copy model output to fine-tune/evals/runs/$(date -u +%Y-%m-%d)/<ide>-<model>/F00N-<slug>/
# Write a capture.json (shape in the runbook).

# 3. Hand the 8 capture.json paths to Claude (or build the merge candidate yourself).
python3 fine-tune/evals/scripts/apply-merge-candidate.py \
    --candidate fine-tune/evals/runs/baseline-merge-candidate-<date>.json

# 4. Verify.
python3 fine-tune/evals/scripts/coverage-sweep.py
```

---

## Regression tests — always run

Every fine-tune cycle MUST end with a clean `coverage-sweep`. Run it manually at any time:

```bash
python3 fine-tune/evals/scripts/coverage-sweep.py
```

Expected last line: `PROBLEMS: none — baseline and registry are consistent.`

If it reports problems:

| Problem | Root cause | Fix |
|---|---|---|
| `CLAIM NOT PROVED: rule R-x claims fixture FN but no cell passes` | You promoted a rule with `fixtures_exercising` set, but the fixture hasn't run under any (model, IDE) combination yet | Run the fixture — either Path A REPLAY or Path B manual — and re-apply. |
| `EXERCISES_RULES GAP: fixture FN has cells reporting on rules not listed in exercises_rules[]` | Cell's `rules_exercised` dict mentions a rule the fixture doesn't declare | Add the rule to `baseline.json → fixtures.FN.exercises_rules[]` (NOT fixture.yaml — coverage-sweep reads from baseline). |
| `UNREGISTERED RULE` / `INACTIVE RULE REFERENCED` | Cell references a rule not in registry or marked inactive | Register the rule (with `canonical_section_at_creation` + birth fingerprint) or remove the cell reference. |
| `ZERO PASSES: active rule has zero pass` | Rule was added but never ran green | Exercise the rule in at least one fixture cell. |

In addition to `coverage-sweep`, the harness offers:

- `flake-check.sh` — re-runs a build.py N times; a fixture that isn't deterministic gets flagged.
- `diff-vs-baseline.sh` — structural diff of a capture.json against the baseline cell.
- `promote-baseline.sh` — wraps fingerprint bump + cell refresh; refuses to run if fingerprint is unchanged.
- `run-baseline.sh` — runs all fixtures under the current spec and emits a candidate.

---

## Keeping AUDIT.md optimized as it grows

`AUDIT.md` grows every cycle — more rules, more examples, more cross-references. Three forces keep it from bloating:

1. **Companion extraction.** Review-only collateral (rendered fences, worked examples, long tables) migrates to `fine-tune/AUDIT-EXAMPLES.md`. Enforcement prose stays in `AUDIT.md`. The companion is fingerprint-pinned in its header, so drift is detectable.
2. **Canonical-home rule.** Every rule has exactly one canonical § home. Cross-references use the `§X.y` breadcrumb format. Three-way fragments are flagged by the analyzer and collapsed during the next cycle.
3. **PE rubric pressure.** `fine-tune/evals/pe-best-practices.md` scores `AUDIT.md` against 16 prompt-engineering practices (token efficiency is one of them — Practice 2). Cycles that bloat without a corresponding rule-strength gain cost points, which shows up in `baseline.json → pe_scores`.

When the spec grows past 2000 lines, consider a Practice 2 extraction cycle — Claude can identify review-only fences ripe for migration in one pass.

---

## What 80 is based on, and how to raise the ceiling

`fine-tune/evals/pe-best-practices.md` scores `AUDIT.md` across **16 prompt-engineering practices × 5 points = 80 total**. The ceiling is **not a fixed number** — it's `max = 5 × N_practices`. Add a 17th practice and the ceiling becomes 85; add four and it becomes 100. This is the mechanism for staying current with the field.

Current baseline: **79/80 (0.9875)**. Only Practice 5 (cross-model portability) remains below 5/5.

**Uniform 1–5 score scale (applies to every practice):**

| Score | Meaning |
|---|---|
| **5** | Best-in-class. Observable from the spec without running the audit; exceeds what ≥2 vendor docs converge on. |
| **4** | Strong with one minor exception or one area of intentional scope-out. |
| **3** | Adequate. Does the thing, but has material gaps or edge cases the spec doesn't cover. |
| **2** | Weak. Present but drifting; the anchors partially apply but regressions are plausible. |
| **1** | Absent or anti-pattern. Failing against the practice's 1-anchor. |

**Hard gate:** no single practice may drop ≥2 points vs. prior baseline, and the TOTAL ratio may not drop ≥0.05 across a cycle. Adding a new practice is allowed to dilute the ratio; regressing existing ones is not. This keeps the loop honest: you can't game the rubric without breaking a fixture cell in the coverage-sweep.

---

## Path to 80/80

The only remaining sub-5 practice is **Practice 5 — Cross-model portability** (currently 4/5). Closure is mechanical:

1. **Pick a non-Claude combo.** GPT-5-class + Gemini 2.5-class are the safest first pair. DeepSeek or Llama can follow.
2. **Run a cross-model capture** using the Path B runbook (`fine-tune/CROSS-MODEL-RUNBOOK.md`). Start with fixture **F006** (the dedicated cross-model fixture), then expand to F001–F008 if time permits.
3. **Record `capture.json`** for each combo. The analyzer expects the same schema regardless of model.
4. **Any divergence IS the gap.** Rule numbering variance, registry cell shape, fixture call-order — whatever drifts becomes a targeted edit cycle against `AUDIT.md` (usually tightening vocabulary away from Claude-isms toward "the agent").
5. **Promote to 5/5** once a full F001–F008 sweep passes invariants on ≥2 non-Claude combos. Update `baseline.json → pe_scores[5]` through `apply-merge-candidate.py` — never by hand.

**Effort estimate:** ~2–4 hours for one combo × F006 (the minimum viable closure). ~half a day for two combos × F001–F008 (the confident closure). Path A (Cowork autonomous) can automate the capture; Path B requires a human driver in the non-Claude IDEs.

---

## Keeping the fine-tune loop itself current

> *"How do I keep updated with new best practices of prompt engineering to update the fine-tune flow in the future?"*

The rubric is intentionally **versioned and extensible**. When a new practice emerges in the field, append it:

### Six-step mechanism

1. **Qualify it.** The candidate must appear in ≥2 vendor docs or ≥2 independent reproducible studies. Single-vendor advocacy is noise; multi-vendor convergence is signal.
2. **Append, never renumber.** Add the new entry to `pe-best-practices.md` with the next integer index (17, 18, …). `baseline.json` cells reference practices by integer — renumbering breaks the ledger.
3. **Write the 1/3/5 anchors.** Anchor "5" to a best-in-class observable (not a vibe). "1" is the anti-pattern. "3" is adequate-with-gaps. Keep anchors measurable — "AUDIT.md contains a `§X.y`…" beats "the spec should be clear."
4. **Score honestly.** First score is usually 2–3, not 5. That drop is the point — the ratio in `baseline.json → pe_scores` shows where the work is.
5. **Earn the points.** Edit `AUDIT.md` to hit the 5-anchor. One fine-tune cycle per rubric change — the coverage-sweep + hard-gate invariant keeps you from gaming it.
6. **Update the ceiling.** `max = 5 × N_practices`. 16 → 80. 17 → 85. 20 → 100.

### Candidate new practices (watchlist)

Tracked across Anthropic, OpenAI, and Google docs + recent model cards. Not yet added to the rubric — each needs multi-vendor survival evidence before earning an integer index.

| # | Candidate | What "5" would look like |
|---|---|---|
| **17** | Context-window awareness | Spec degrades gracefully at 8k / 32k / 200k+ contexts; load-bearing rules are front-loaded and critical invariants are repeated near attention anchors. |
| **18** | Reasoning-mode compatibility | Behavior under extended thinking / reasoning modes (o-series, Claude thinking) does not diverge from non-reasoning output. Spec does not suppress or inflate chain-of-thought. |
| **19** | Tool-use invariance | AUDIT.md outputs are identical whether the agent is told to use tools, runs standalone, or runs inside an orchestrator. No rule relies on a specific tool being present. |
| **20** | Groundedness & verifiability | Every claim in the audit output is traceable to a specific rule ID + file path + line range. Hallucinated findings fail the invariant at capture time. |

### Where to watch for new practices

- **Anthropic prompt-engineering docs** — https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview. Primary source; updated when new model generations land.
- **OpenAI prompt engineering guide** — https://platform.openai.com/docs/guides/prompt-engineering. Cross-reference when designing cross-model portability.
- **Google Gemini prompting docs** — https://ai.google.dev/gemini-api/docs/prompting-strategies. Useful for Practice 5 (cross-model) edge cases.
- **Model cards and changelogs** — each new major model release (Claude, GPT, Gemini, DeepSeek, Llama) publishes prompting notes; read them.
- **Academic / applied research** — arXiv `cs.CL` tags on "prompting", "in-context learning", "chain-of-thought robustness", "reasoning model behavior". Filter for reproducible results, not single-benchmark claims.
- **Community patterns that have survived** — watch for patterns that land in multiple vendor docs independently. Anthropic + OpenAI both adopting XML-style role tags is a stronger signal than one vendor advocating a pattern.

Cadence I recommend: a quarterly rubric review. Open `pe-best-practices.md`, scan the sources above, and ask:

1. Has any current practice matured past 1–5 anchors? (If "5" now means something stronger in the field, raise the bar.)
2. Any new practice with survival evidence across ≥2 vendor docs?
3. Any practice that has been proven non-load-bearing? (E.g., a prompt pattern that once helped but modern models now ignore.)

Run one fine-tune cycle per rubric change — add the practice, score honestly (probably starts at 2–3), then earn the points through targeted edits over the next cycles. The regression harness keeps you honest: you can't game the rubric without breaking existing fixture cells.

---

## What NOT to do

Behavior that burned a past cycle, documented here so you don't repeat it:

- **Never hand-edit `baseline.json` cells.** Always route through `apply-merge-candidate.py`. Hand edits are detected by the coverage-sweep + rule-survival invariant.
- **Never drop a rule silently.** `R-*` rules with ≥1 prior pass must retain ≥1 pass. If a rule is truly obsolete, mark `status: retired` in the registry rather than deleting — the pass ledger is evidence.
- **Never omit `audit_md_version_at_creation`.** A new rule's birth fingerprint is FROZEN — it never updates, even when the rule's canonical_section_current moves.
- **Never commit `.audit/` output from a dev repo.** Put `.audit/` in the target repo's `.gitignore`, not this one.
- **Don't drive `AUDIT.md` edits during a capture run.** Fixtures are captured against a specific fingerprint; mid-run spec edits invalidate the capture.

---

## Pointers

- `fine-tune/FINETUNE-WORKFLOW.md` — the full design rationale for the loop.
- `fine-tune/ANALYZER.md` — the analyzer meta-prompt for spotting drift across captures.
- `fine-tune/CROSS-MODEL-RUNBOOK.md` — Path B step-by-step (IDE-agnostic).
- `fine-tune/AUDIT-CONFIG.md` — configurable variables + `§` notation reference.
- `fine-tune/evals/README.md` — harness internals.
- `fine-tune/evals/criteria.md` — what makes a cell pass.
- `fine-tune/evals/pe-best-practices.md` — the 16-practice rubric.

---

## Support

If `AUDIT.md` saved you a review cycle or helped you sharpen an audit pipeline, consider supporting the project:

[☕ Buy me a coffee](https://buymeacoffee.com/zintaen)

Support keeps the fine-tune cycles running — new fixtures, new rubric entries, cross-model sweeps, and keeping the regression harness honest take real time. Every coffee buys a cycle.

---

*Last updated: see `git log -1 -- README.md`. Current `AUDIT.md` fingerprint: run `shasum -a 256 AUDIT.md`.*
