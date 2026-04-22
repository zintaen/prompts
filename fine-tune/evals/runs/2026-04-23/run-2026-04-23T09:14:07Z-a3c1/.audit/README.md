# .audit/ — repository audit state

This directory is maintained by the AI Repository Audit Agent
(spec: AUDIT.md). It is safe to commit; humans edit it to approve,
defer, or decline findings.

## Layout

- `state/index.json` — master registry of every finding, all time.
- `state/wont-do.json` — fingerprints permanently declined.
- `state/in-flight.json` — items currently being implemented by the agent.
- `reports/YYYY/MM/YYYY-MM-DD.md` — daily human-readable report.
- `reports/YYYY/MM/YYYY-MM-DD.json` — daily machine-readable mirror.
- `changelog/CHANGELOG.md` — append-only human-readable transition log.
- `changelog/transitions.jsonl` — append-only machine-readable log.
- `implementations/<epic>/<story>/<task>/` — per-task PLAN/DIFF/VERIFY.
- `config.yaml` — behavior configuration (§14 of AUDIT.md).

## Conformance

This directory is validated against AUDIT.md's Step 7.5
self-conformance check (53 items). Byte-level drifts in shape are
hard violations; repair the artifact rather than editing
`wont-do.json` to hide it.
