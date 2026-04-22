# AUDIT-CONFIG.md — § notation explained, and every customizable variable gathered

**Purpose.** Answer two questions about `AUDIT.md`:

1. What is `§` and why does it appear so often?
2. Should user-customizable variables stay in AUDIT.md? If so, where — and how to arrange them so tuning the spec to a new team or codebase takes minutes, not archaeology.

---

## Part 1 — What is `§`?

`§` is the **section sign** (Unicode U+00A7, "section"). It's the centuries-old convention in legal and technical documents for "Section". In AUDIT.md it's used as a lightweight, machine-stable cross-reference marker:

- `§3.m` means *"Section 3, sub-rule m"*.
- `§ITEM SCHEMA` means *"the section whose heading is ITEM SCHEMA"*.
- `§Step 7.5a` means *"the Step 7.5a sub-block (Schema conformance)"*; `§Step 7.5b item 12` means *"the 12th item in the Step 7.5b behavioral-checks list"*.

Why it's used instead of "see Section 3.m":

- **Dense.** One character instead of eight; saves tokens in the prompt.
- **Greppable.** `grep -n '§3.m' AUDIT.md` finds every reference in milliseconds, across an IDE, across a terminal, across a file browser search.
- **Unambiguous.** Plain English cross-references ("the earlier rule about mirrors") depend on the reader tracking context; `§3.m` doesn't.
- **Tradition.** Lawyers, RFC authors, and ISO standards all use it. When a prompt reads like a spec, models tend to treat it like one.

There are **89 occurrences** of `§` in the current AUDIT.md. They aren't decorative — they're the referencing spine that lets rules point to each other without restating content.

**Caveat — position coupling.** Today every `§` reference is position-coupled: `§3.m` means "whatever the m-th sub-rule of §3 currently is". If you renumber §3, every `§3.m` citation downstream silently re-aims. `AUDIT-DEEP-REVIEW.md` Part 2 proposes adding stable `rule_id` anchors (e.g. `R-anti-drift-mirror-state-invariants`) alongside the § references, so references survive reorganization. Short-term: keep `§3.m` readable for humans. Long-term: `rule_id` is the machine anchor.

---

## Part 2 — Should customizable variables stay in AUDIT.md?

**Short answer: customizable knobs stay *cited* in AUDIT.md but *defined* in one clearly labeled place.**

Two principles:

1. **Behavior belongs in the spec. Data belongs in a config.** The spec says *"assign `type=security` items to `AGENT` by default unless overridden."* That's behavior. The actual default-table is data — it lives in `.audit/config.yaml`. The spec references the config by name; it does not transcribe the values.
2. **Single source of truth.** Today AUDIT.md has the defaults *both* in §14 CONFIGURATION (as a YAML block) and implicitly in §BUDGETS & LIMITS (as a separate YAML block). §14 even has a comment `"See §BUDGETS & LIMITS for canonical values; keys repeated here so config.yaml parses standalone."` That's an acknowledged duplication. The fix is to pick one home and link to it.

### Recommended arrangement

Two tiers:

**Tier A — In-prompt knobs (stay in AUDIT.md, hoisted to a single §CONFIG section near the top).** These are values the model needs to know *before* it can follow the spec, because they show up in ID formats, state machines, and sort order:

- The 12 canonical TYPE3 codes (`SEC, PRF, REL, QLT, ARC, DEV, DOC, INF, FEA, IDA, REF, TST`).
- The 7-status state machine (`PROPOSED, APPROVED, IN_PROGRESS, DONE, DEFERRED, REJECTED, WONT_DO`).
- The 4 MoSCoW values (`MUST, SHOULD, COULD, WONT`).
- The 5 severity levels (`low, medium, high, critical` + `none`).
- The canonical sort-order keys (`reported_date ASC → assignee ASC → moscow → id ASC`).
- The `.audit/` directory layout skeleton (so the model knows where to write).
- The 8 redaction label → regex map.
- The 5W1H2C5M framework fields.

These are "what the agent IS". Moving them to an external YAML would force the agent to fetch YAML at bootstrap before it knows what an ID looks like — an awkward bootstrap.

**Tier B — External knobs (live in `.audit/config.yaml`, referenced by name from AUDIT.md).** These are values a team tunes per repo:

- `exclusions.paths` and `exclusions.globs` (what to skip).
- `scanners.*.enabled` (which scanner categories are active).
- `scanners.*.severity_threshold` (noise floor per scanner).
- `scanners.ideas.max_per_run` (how loud the idea-generator is).
- `defaults.assignee_by_type` (who owns which finding type).
- `defaults.moscow_default_by_type`.
- `defaults.review_threshold` (which MoSCoW tier triggers human review).
- `limits.*` (all numeric budgets: runtime, file counts, finding caps, line caps).
- `execute.require_human_approval` (safety bit).
- `execute.block_types` (which finding types cannot be auto-executed).
- `execute.require_tests`, `execute.require_diff_preview`.
- `redaction.extra_patterns` (team-specific secret patterns).

These are "how the agent BEHAVES for this team". A new team customizes them without touching the spec.

---

## Part 3 — The proposed §CONFIG block (drop-in for AUDIT.md)

Here is the Tier-A block, arranged for easy customization. Drop this near the top of AUDIT.md, right after §QUICKSTART and before §CRITICAL ANTI-DRIFT RULES. Every sub-table carries a `config_key` that a YAML file or `fine-tune/SCHEMA.json` can mirror.

```markdown
# §CONFIG — Canonical identities (the agent IS these)

These values define the agent's vocabulary. Changing any of them is a major version bump: every downstream rule, every state file, every fingerprint depends on them. They live here because the agent needs them at bootstrap; they are NOT in `.audit/config.yaml`.

If you fork AUDIT.md for a different team or domain, customize this block first. Everything else in the spec is expressed in terms of these.

## §CONFIG.1 — TYPE3 codes (closed set; `config_key: type_codes`)

| TYPE3 | Canonical `type` value |
|-------|-----------------------|
| SEC   | security              |
| PRF   | performance           |
| REL   | reliability           |
| QLT   | quality               |
| ARC   | architecture          |
| DEV   | dx                    |
| DOC   | docs                  |
| INF   | infrastructure        |
| FEA   | feature               |
| IDA   | idea                  |
| REF   | refactor              |
| TST   | test                  |

**Forbidden synonyms (always fail conformance):** `QA→QLT`, `DX→DEV`, `DOCS→DOC`, `PERF→PRF`, `ARCH→ARC`. TYPE3 is exactly 3 characters.

## §CONFIG.2 — Status state machine (closed set; `config_key: statuses`)

| Status | Meaning |
|---|---|
| PROPOSED | Agent discovered; no human review yet |
| APPROVED | Human flipped for agent execution |
| IN_PROGRESS | Agent executing; lock acquired |
| DONE | Agent completed; implementation persisted |
| DEFERRED | Human parked; may revisit |
| REJECTED | Human rejected; may re-propose later (not the same as WONT_DO) |
| WONT_DO | Terminal; blocks re-proposal via `wont-do.json` fingerprint |

## §CONFIG.3 — MoSCoW (closed set; `config_key: moscow`)

`MUST, SHOULD, COULD, WONT`. Interpreted per this decade's convention.

## §CONFIG.4 — Severity ladder (closed set; `config_key: severity_levels`)

`low < medium < high < critical`. `none` is reserved for non-severity-bearing types (docs, idea, feature, dx, refactor) and is required to be absent, not `null`.

## §CONFIG.5 — Canonical sort order (closed ordering; `config_key: sort_keys`)

1. `reported_date` ASC
2. `assignee` ASC
3. `moscow` (MUST < SHOULD < COULD < WONT)
4. `id` ASC

## §CONFIG.6 — Redaction labels and patterns (closed set; `config_key: redaction_patterns`)

| Pattern | Label |
|---|---|
| `AKIA[0-9A-Z]{16}` | `[REDACTED:aws-key]` |
| `(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])` | `[REDACTED:possible-aws-secret]` |
| `(?i)(api[_-]?key\|token\|secret)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{20,}['"]?` | `[REDACTED:token]` |
| `sk_live_[0-9a-zA-Z]{24,}` | `[REDACTED:stripe-key]` |
| `xox[abprs]-[A-Za-z0-9-]{10,}` | `[REDACTED:slack-token]` |
| `gh[pousr]_[A-Za-z0-9]{36,}` | `[REDACTED:github-token]` |
| `-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----` | `[REDACTED:private-key]` |
| `eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+` | `[REDACTED:jwt]` |

Structural tokens (timestamps, run_ids, fingerprints, git shas, file paths, line numbers) are NEVER redacted — only the literal secret bytes. Custom patterns: append to `.audit/config.yaml → redaction.extra_patterns`.

## §CONFIG.7 — 5W1H2C5M framework fields (closed set; `config_key: 5w1h2c5m`)

- 5W: `what, why, who, when, where`
- 1H: `how`
- 2C: `cost, constraints`
- 5M: `man, machine, material, method, measurement`

Forbidden filler phrases (never pass conformance): see `fine-tune/SCHEMA.json#/forbidden_5w1h2c5m_phrases`.

## §CONFIG.8 — `.audit/` directory layout (closed; `config_key: audit_layout`)

```
.audit/
├── state/
│   ├── index.json                  # authoritative item list
│   ├── wont-do.json                # fingerprint tombstones
│   └── locks/run.lock              # single-run lock
├── daily/
│   └── YYYY-MM-DD.{md,json}        # human + machine daily mirror
├── reports/YYYY/MM/                # rotated old dailies (via consolidate)
├── evidence/                       # per-item evidence files (redacted)
├── implementations/                # per-task implementation bundles (execute mode)
├── changelog/transitions-YYYY.jsonl  # rotated transitions
├── transitions.jsonl               # current-year transitions (append-only)
└── config.yaml                     # Tier-B knobs (team-tunable)
```

## §CONFIG.9 — ID format (closed; `config_key: id_format`)

`AUD-YYYY-MM-DD-<TYPE3>-<NNNN>`
- `TYPE3` per §CONFIG.1
- `NNNN` is a global daily counter, contiguous from 0001, NO per-category reset, NO offset start
- Example: `AUD-2026-04-20-SEC-0001`

## §CONFIG.10 — Fingerprint format (closed; `config_key: fingerprint_format`)

`sha256:<64-lowercase-hex>` — exactly 71 characters. Never a placeholder.

---
```

**That's Tier A.** Dropping this block at the top has two effects:

1. A new user who wants to fork AUDIT.md for a different domain (e.g., "Financial Compliance Audit Agent" instead of "Repository Audit Agent") edits one section — `§CONFIG` — and the rest of the spec follows automatically.
2. The scattered references throughout the spec can now say *"per §CONFIG.1"* instead of restating the 12 codes every time. This is exactly the "single canonical home" fix that `AUDIT-REVIEW.md` recommended.

---

## Part 4 — Tier B: what stays in `.audit/config.yaml`

The existing §14 CONFIGURATION block already defines this. Keep it, but:

1. **Remove duplicated numeric limits.** §BUDGETS & LIMITS and §14 `limits:` are the same values restated. Delete from §BUDGETS & LIMITS; replace with a one-liner: *"Numeric limits live in `.audit/config.yaml → limits`. See §14 for defaults."*
2. **Add a header comment to `.audit/config.yaml`** pointing back to AUDIT.md §14 for documentation. This is how the user discovers what each knob does without re-reading the whole spec.
3. **Validate against a schema.** The values in `.audit/config.yaml` should be validated against a machine-readable schema (e.g., `.audit/config.schema.json`) so a typo like `assignee_by_type: { security: agent }` (lowercase) is caught at load time, not at first scan.

### Recommended `.audit/config.yaml` structure, annotated

```yaml
# .audit/config.yaml — TEAM-TUNABLE KNOBS
# Spec reference: AUDIT.md §14 CONFIGURATION
# Canonical identities (TYPE3 codes, statuses, MoSCoW, etc.) live in AUDIT.md §CONFIG
# and cannot be overridden here. If you need to fork the vocabulary, fork AUDIT.md.
schema_version: 1

exclusions:
  # Paths and globs excluded from scanning. Supports repo-relative.
  paths: ["node_modules", "vendor", "dist", "build", ".git", ".next", "target"]
  globs: ["**/*.min.js", "**/*.snap", "**/*.lock", "**/*.map"]

scanners:
  # Toggle scanner categories and set noise floors.
  security:     { enabled: true, severity_threshold: low }
  performance:  { enabled: true }
  reliability:  { enabled: true }
  quality:      { enabled: true }
  architecture: { enabled: true }
  dx:           { enabled: true }
  docs:         { enabled: true }
  ideas:        { enabled: true, max_per_run: 15 }

defaults:
  # Which finding types are agent-owned vs human-owned by default.
  # Override per-item via the item's `assignee` field.
  assignee_by_type:
    security: AGENT
    performance: AGENT
    reliability: AGENT
    quality: AGENT
    refactor: AGENT
    docs: AGENT
    dx: AGENT
    test: AGENT
    architecture: HUMAN
    feature: HUMAN
    idea: HUMAN
    infrastructure: HUMAN

  # Default MoSCoW per type.
  moscow_default_by_type:
    security: MUST
    performance: SHOULD
    reliability: SHOULD
    others: COULD

  # MoSCoW threshold at which items are surfaced in the HITL banner.
  review_threshold: SHOULD

limits:
  # Numeric budgets. Exceeding max_runtime triggers graceful truncation.
  max_runtime_minutes: 20
  max_files_scanned: 5000
  max_file_size_mb: 1
  max_findings_per_run: 50
  max_lines_changed_per_task: 200
  max_files_per_task: 10
  large_repo_threshold_files: 10000

execute:
  # Hard safety bits. Flipping require_human_approval to false is NOT recommended.
  require_human_approval: true
  block_types: [feature, idea, infrastructure]
  require_tests: true
  require_diff_preview: true

redaction:
  # Custom regex patterns additional to AUDIT.md §CONFIG.6.
  # Patterns here extend — never override — the canonical list.
  extra_patterns: []
  # Example:
  # extra_patterns:
  #   - pattern: "ACME-[A-Z0-9]{32}"
  #     label:   "[REDACTED:acme-internal-token]"
```

---

## Part 5 — Migration from the current AUDIT.md

Concrete steps:

1. **Add the §CONFIG block** at the top of AUDIT.md (between §QUICKSTART and §CRITICAL ANTI-DRIFT RULES). Copy from Part 3 above.
2. **Remove inline restatements** of TYPE3 codes, statuses, MoSCoW, severity, sort keys, redaction patterns from every other location — replace with pointers like *"per §CONFIG.1"*. This is exactly the "pick canonical home" fix from `AUDIT-REVIEW.md`.
3. **Edit §BUDGETS & LIMITS** down to a pointer: *"All numeric limits: see `.audit/config.yaml → limits` (defaults documented in §14 CONFIGURATION)."*
4. **Edit §14 CONFIGURATION** to include the annotated version of `config.yaml` in Part 4. Add the "Canonical identities live in §CONFIG" disclaimer at the top.
5. **Ship `.audit/config.schema.json`** alongside AUDIT.md so new repos can validate their `config.yaml`.
6. **Run the eval gate** after each step. Any per-rule regression per `fine-tune/evals/rule-registry.json` blocks the step.

Expected net line change: **-120 to -180 lines** (you pick up back the restatements and the §BUDGETS duplication, with small additions for the §CONFIG block itself).

---

## Part 6 — Customization checklist (the user-facing bit)

A new team adopting AUDIT.md for their repo now has a clear, time-boxed path:

- [ ] **Forking the spec for a new domain?** Edit §CONFIG (Tier A). Every rule will follow.
- [ ] **Tuning scan noise?** Edit `.audit/config.yaml → scanners.*.severity_threshold` and `.audit/config.yaml → scanners.ideas.max_per_run`.
- [ ] **Changing who owns what?** Edit `.audit/config.yaml → defaults.assignee_by_type`.
- [ ] **Team has custom secret format?** Append to `.audit/config.yaml → redaction.extra_patterns`.
- [ ] **Scanning a large monorepo?** Raise `limits.large_repo_threshold_files` and set `exclusions.paths` appropriately.
- [ ] **Hardening?** Keep `execute.require_human_approval: true` and prune `execute.block_types` only deliberately.

Nothing on this list requires editing AUDIT.md itself.

---

*End of AUDIT-CONFIG.md.*
