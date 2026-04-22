# Audit System

This directory is managed by an AI Repository Audit Agent. Daily scans land in `reports/<YYYY>/<MM>/<date>.md`. Nothing else in the repository is modified without explicit human approval.

## The loop (ASCII diagram)

```text
SCAN → PROPOSED → APPROVED → IN_PROGRESS → DONE
           ↓          ↓             ↓
       REJECTED    DEFERRED      DEFERRED
                      ↓
                   WONT_DO
```

## Daily 3-step

1. Open today's report in `reports/YYYY/MM/YYYY-MM-DD.md`.
2. Edit `status:` to `APPROVED`, `WONT_DO`, or `DEFERRED`.
3. Run execute mode: "Run AUDIT.md in execute mode."

## Where to find what

| Path | Purpose |
|------|---------|
| `reports/<YYYY>/<MM>/<YYYY-MM-DD>.{md,json}` | Daily human-readable report and machine-readable mirror. |
| `state/{index,wont-do,in-flight}.json` | Master registry of findings, blocklist, and currently executing items. |
| `changelog/{CHANGELOG.md,transitions.jsonl}` | Append-only logs of all state changes. |
| `implementations/<epic>/<story>/<task>/` | Plans, diffs, and verification artifacts for executed tasks. |

## Status reference

- **PROPOSED**: Newly discovered, awaiting triage.
- **APPROVED**: Human has approved implementation.
- **IN_PROGRESS**: Agent is currently implementing.
- **DONE**: Implementation complete and verified.
- **DEFERRED**: Acknowledged but pushed to a later cycle.
- **WONT_DO**: Declined. Will not be re-suggested.
- **REJECTED**: False positive or invalid.

## MoSCoW reference

- **MUST**: Security-critical, data loss, broken builds, compliance gaps. Block release.
- **SHOULD**: High-value perf / reliability / maintainability. Address this cycle.
- **COULD**: Nice-to-have. Backlog candidate.
- **WONT**: Out of scope or explicitly declined. Terminalize to wont-do.json.

## Cheat sheet

See `templates/CHEAT-SHEET.md.tmpl`

## Troubleshooting

See `templates/TROUBLESHOOTING.md.tmpl`

## Footer

Auto-generated disclaimer.
Last regenerated: 2026-04-22T15:00:00Z by run-2026-04-22T15:00:00Z-g31p.
AUDIT.md schema_version: 1.0.0.
