# .audit/ — Repository Audit State

This directory contains the stateful audit trail for this repository, managed by the AI Repository Audit Agent per `AUDIT.md`.

## What's here

| Path | Purpose |
|------|---------|
| `state/index.json` | Master registry of all findings (append-only) |
| `state/wont-do.json` | Fingerprints the agent will never re-suggest |
| `state/in-flight.json` | Items currently being implemented |
| `reports/YYYY/MM/YYYY-MM-DD.md` | Daily human-readable report |
| `reports/YYYY/MM/YYYY-MM-DD.json` | Machine-readable mirror (regenerated each run) |
| `changelog/CHANGELOG.md` | Human-readable state-change log |
| `changelog/transitions.jsonl` | Machine-readable transition log |
| `config.yaml` | Audit configuration (exclusions, scanner settings, limits) |
| `implementations/` | Diffs, plans, and verification for executed fixes |

## How to use

1. **Scan:** Run `AUDIT.md` in scan mode to discover findings.
2. **Review:** Open today's `.md` report, review PROPOSED items.
3. **Approve:** Set `status: APPROVED` on items you want the agent to fix.
4. **Execute:** Run `AUDIT.md` in execute mode to implement approved fixes.

## Status values

| Status | Meaning |
|--------|---------|
| PROPOSED | Agent discovered; awaiting human review |
| APPROVED | Human approved; ready for agent execution |
| IN_PROGRESS | Agent is actively implementing |
| DONE | Implementation complete and verified |
| DEFERRED | Postponed to a future cycle |
| WONT_DO | Rejected permanently; fingerprint added to wont-do.json |
| REJECTED | Human rejected the finding |

## MoSCoW priorities

| Priority | Meaning |
|----------|---------|
| MUST | Blocks release; mandatory |
| SHOULD | Important but not blocking |
| COULD | Nice to have |
| WONT | Explicitly excluded this cycle |

## Cheat sheet

```
# Run a scan
Tell your agent: "Run AUDIT.md in scan mode."

# Review findings
Open .audit/reports/YYYY/MM/YYYY-MM-DD.md

# Approve a finding
Set status: APPROVED on the item in state/index.json

# Execute approved fixes
Tell your agent: "Run AUDIT.md in execute mode."

# Check current state
Tell your agent: "Run AUDIT.md in review mode."
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Lock file prevents scan | Prior run crashed | Delete `.audit/state/locks/run.lock` |
| Duplicate findings | Fingerprint drift | Run consolidate mode |
| Missing report | Scan interrupted before Step 7 | Re-run scan |
| Stale dates in report | Timezone mismatch | Verify UTC timestamps |
