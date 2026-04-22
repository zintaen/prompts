# pe-best-practices.md — prompt-engineering rubric for AUDIT.md

**Purpose.** A machine-checkable scorecard that ANALYZER.md applies to every proposed AUDIT.md edit. Each of the 16 practices below is scored 1–5 against the *resulting* AUDIT.md (i.e., the version after the edit lands). The current scores are tracked in `evals/baseline.json` under `pe_scores`.

**Why it exists.** Layer 4 of the regression-protection design (see `AUDIT-DEEP-REVIEW.md` Part 3). The fingerprint gate (Layer 1) and per-rule cells (Layer 2) catch *behavioral* regressions. This file catches *quality* regressions — edits that close a drift gap but degrade the prompt overall (e.g., add 200 lines of restated rules that fragment a single canonical home, or hard-code values that should live in §CONFIG).

**Hard gate.** A proposed edit MUST NOT cause any single practice score to drop by ≥2 vs. the prior baselined version. A drop of 1 is a soft warning that the analyzer must surface in `risk:` of the proposal. A net average drop of ≥0.5 across all 16 practices blocks the edit even if no single practice dropped by ≥2.

**Manual scoring is acceptable.** Until an automated PE-scorer exists, the human reviewer scores each practice during proposal review. The scores get committed to `baseline.json` only when the edit is accepted.

---

## Scoring scale (uniform across all 16)

| Score | Meaning |
|---|---|
| 5 | Best-in-class. Practice is fully and consistently realized. No friction to apply, no edge cases miss it. |
| 4 | Strong. Practice is applied throughout with minor exceptions that are documented or harmless. |
| 3 | Adequate. Practice is mostly applied, but with notable gaps or inconsistencies that don't actively mislead the model. |
| 2 | Weak. Practice is partially applied; gaps cause measurable drift or rework in some runs. |
| 1 | Absent or anti-pattern. Practice is missing or inverted; the prompt actively works against it. |

---

## The 16 practices

### 1. Single canonical home for every rule
**Test.** Pick any rule. Search AUDIT.md for it. Does it appear in exactly one location, with all other references being explicit pointers ("see §X")?
**Anti-pattern.** Same rule restated verbatim in 2+ places. When one drifts, the others lie silently.
**Current score reference.** Pre-AUDIT-CONFIG.md: 2/5. With §CONFIG block landed and inline restatements removed: target 4/5.

### 2. Token efficiency
**Test.** Lines / active rule. Count active rule_ids in `evals/rule-registry.json`. Divide AUDIT.md line count by that. Lower is better.
**Anti-pattern.** Verbose rationale prose between rules; explainers that should live in `AUDIT-REVIEW.md` or `FINETUNE-WORKFLOW.md`, not the spec.
**Current score reference.** 1369 lines / 27 rules ≈ 51 lines/rule. Target ≤40 lines/rule after consolidation.

### 3. Stable anchoring
**Test.** Can a rule be cited durably across reorganizations? Check whether the analyzer cites `R-anti-drift-mirror-state-invariants` (durable) or `§3.m` (breaks on reorder).
**Anti-pattern.** Position-coupled citations everywhere; renumbering §3 silently invalidates 50+ Step 7.5 references.
**Current score reference.** 3/5 today (rule_ids designed but not yet inserted as HTML anchor comments). Target 5/5 once anchors land.

### 4. Variables vs. logic separation
**Test.** Count the number of places where a closed-set value (TYPE3 codes, statuses, MoSCoW levels) appears literally. >1 location per value = anti-pattern.
**Anti-pattern.** TYPE3 enumerated in §1, restated in §3.b, repeated in Step 7.5 examples, mentioned again in §DEFINITIONS.
**Current score reference.** Pre-§CONFIG: 2/5. Post-§CONFIG: target 5/5.

### 5. Model portability
**Test.** Does the prompt rely on Claude-specific behaviors (e.g., "you are Claude", XML tags, specific tool-call syntax)? Run on Gemini, GPT-4o, Copilot — does it still work?
**Anti-pattern.** Hardcoded "Claude will…" or assumed thinking-block availability.
**Current score reference.** 3/5 (some Claude-specific phrasing in §ROLE). Target 4/5 by replacing with model-neutral "the agent".

### 6. Worked examples are present and minimal
**Test.** For every non-trivial rule, is there exactly one short worked example showing pass + fail? Examples should be load-bearing, not decorative.
**Anti-pattern.** No examples at all (model guesses) OR long anecdotal examples that bloat tokens without clarifying the rule.
**Current score reference.** 4/5. Step 7.5 has good worked examples. Some rules in §3 lack them.

### 7. Refusal contract is explicit
**Test.** §ROLE lists the conditions under which the agent refuses or escalates rather than guessing. The list is enumerated, not implied.
**Anti-pattern.** Vague "use good judgment" language instead of named refusal triggers.
**Current score reference.** 5/5. The 7-item refusal contract is one of AUDIT.md's strongest features.

### 8. Anti-gaming protection
**Test.** Are anti-gaming rules (X- prefix in registry) explicitly marked as un-weakenable in ANALYZER.md HARD RULE 4? Does the analyzer refuse to propose edits that collapse them?
**Anti-pattern.** Anti-gaming rules indistinguishable from regular rules; analyzer cheerfully proposes "merging items 30 and 31 to reduce duplication".
**Current score reference.** 5/5. ANALYZER.md HARD RULE 4 explicitly protects §Step 7.5c items 1–5 + all X- rules.

### 9. Self-conformance check exists and is exhaustive
**Test.** Step 7.5 (or equivalent) lists every invariant and forces the agent to check itself before emitting Run Summary. New rules are added to Step 7.5 in the same edit that creates them.
**Anti-pattern.** Step 7.5 drifts behind §3 — new anti-drift rules are added without corresponding self-conformance items.
**Current score reference.** 4/5. §Step 7.5 today is 3 sub-blocks: 7.5a (one consolidated SCHEMA.json conformance pass), 7.5b (23 behavioral/judgment items), 7.5c (5 anti-gaming items). Drift risk: every §CONFIG-inserted rule that cannot be encoded in SCHEMA.json must add a §Step 7.5b or §Step 7.5c item — purely structural rules belong in SCHEMA.json and ride the §Step 7.5a pass.

### 10. Output contract is unambiguous
**Test.** §OUTPUT CONTRACT specifies the exact JSON schema (with required keys), the exact text of the HITL banner, and the order they appear. A second model reading the same prompt produces structurally identical output.
**Anti-pattern.** "Emit a summary at the end" with no schema.
**Current score reference.** 5/5. Run Summary JSON schema is fully specified.

### 11. Anti-drift rules are first-class, not appendix
**Test.** §CRITICAL ANTI-DRIFT RULES sits near the top of the prompt (within first 30% of tokens), is unmissable, and is referenced by Step 7.5.
**Anti-pattern.** Drift protection buried in §3 of an appendix; model never reads it.
**Current score reference.** 4/5. §CRITICAL ANTI-DRIFT RULES is well-placed; numbering bug (§3.a–r skipping §3.i/§3.o twice) is a soft demerit.

### 12. Failure modes are named
**Test.** §WHAT NOT TO DO enumerates the historical failure patterns (TYPE3 invention, deletion-to-pass, fingerprint collision-merging). Each named failure has a corresponding anti-rule.
**Anti-pattern.** Failures only discussed in postmortems; the prompt itself has no negative examples.
**Current score reference.** 4/5. §WHAT NOT TO DO covers most patterns. Could add cross-references to the X- rules.

### 13. Configuration is externalized where appropriate
**Test.** Tier-A vs. Tier-B split is clean: behavior in §CONFIG (in the spec), data in `.audit/config.yaml`. No data hard-coded in prose.
**Anti-pattern.** `max_files: 5000` appears as a magic number in three different sections of the prompt.
**Current score reference.** Pre-AUDIT-CONFIG.md: 2/5. Post-§CONFIG + .audit/config.yaml: target 5/5.

### 14. Determinism cues
**Test.** Prompt explicitly tells the user to set temperature to 0, seed where supported, and warns about which behaviors drift at higher temperatures.
**Anti-pattern.** No mention of temperature; user runs at default 0.7 and is surprised by inconsistent fingerprints.
**Current score reference.** 3/5. PROMPT-INVOCATION.md gotcha #5 mentions it; AUDIT.md itself does not. Target: add a §DETERMINISM section.

### 15. Evidence + redaction are coupled
**Test.** §3.j (evidence required) and §3.k (redaction required) are presented together. The model cannot satisfy one without satisfying the other.
**Anti-pattern.** Evidence rule says "include the line"; redaction rule lives 400 lines later. Model includes raw secrets.
**Current score reference.** 4/5. Coupled in §EVIDENCE REDACTION but the §3.j → §EVIDENCE REDACTION pointer is implicit.

### 16. Mode separation is enforced
**Test.** scan / review / execute / consolidate have distinct §OPERATING MODES rows, distinct allowed actions, and distinct write permissions. The agent refuses cross-mode actions (e.g., executing during scan).
**Anti-pattern.** Modes documented but the agent still proposes a fix mid-scan because the boundary isn't tested.
**Current score reference.** 5/5. §OPERATING MODES table is explicit and the refusal contract enforces it.

---

## Aggregate scoring

```
TOTAL = sum(scores) / 80
```

**Current baseline (2026-04-20, pre-edits):** 63/80 (0.7875)
**Target after AUDIT-DEEP-REVIEW.md + AUDIT-CONFIG.md edits land:** 73/80 (0.9125)

A drop in TOTAL of ≥0.05 vs. the prior baseline blocks the proposal regardless of per-practice scores.

---

## How to score a proposed edit

ANALYZER.md emits proposals to `PROPOSED-EDITS-YYYY-MM-DD.md`. For each top-10 proposal, the analyzer MUST include a `pe_impact:` block:

```yaml
pe_impact:
  before:    # scores at current baseline
    1: 2
    2: 3
    # ... all 16
  after:     # predicted scores after this edit lands
    1: 4
    2: 4
    # ... all 16
  drops_by_2_or_more: []   # MUST be empty or proposal is blocked
  drops_by_1: [5]          # warning items
  net_total_change: +0.0625
```

The human reviewer either accepts the predicted `after:` scores (and they get committed to `baseline.json`) or overrides them with measured scores from a re-evaluation run.

---

## Adding a new practice

If a 17th best practice becomes important (e.g., "context-window awareness" once AUDIT.md exceeds 50% of common context budgets), append it here with the next integer index. Never renumber existing practices — `baseline.json` cells reference them by integer index.

---

## Removing a practice

Set the practice's score to `null` in all future cells and add a `deprecated_at:` annotation here. Do not delete the entry. Historical baselines need stable indices.

---

*End of pe-best-practices.md.*
