# .audit/ — repository audit state

This directory is maintained by the AI Repository Audit Agent
(spec: AUDIT.md). It is safe to commit; humans edit it to approve,
defer, or decline findings.

## Layout

- `state/index.json` — master registry of every finding, all time.
- `state/wont-do.json` — fingerprints permanently declined. Never
  re-suggested.
- `state/in-flight.json` — items currently being implemented by the
  agent.
- `reports/YYYY/MM/YYYY-MM-DD.md` — daily human-readable report.
  Re-runs append a new entry under "Run Log".
- `reports/YYYY/MM/YYYY-MM-DD.json` — daily machine-readable mirror.
- `changelog/CHANGELOG.md` — append-only human-readable transition
  log.
- `changelog/transitions.jsonl` — append-only machine-readable
  transition log (one row per state change).
- `implementations/<epic>/<story>/<task>/` — per-task PLAN.md,
  DIFF.patch, VERIFY.md written by execute mode.
- `config.yaml` — behavior configuration (§14 of AUDIT.md).

## How to use

- **Review today's findings:** open
  `reports/YYYY/MM/YYYY-MM-DD.md`.
- **Approve a finding:** set `status: APPROVED` on the item in
  `state/index.json` (or in the daily .md), then re-invoke the
  agent in `MODE=execute`.
- **Decline a finding permanently:** set `status: WONT_DO`. The
  agent will add the fingerprint to `wont-do.json` and never
  re-propose it.
- **Defer to next sprint:** set `status: DEFERRED`.

## Conformance

This directory is validated against AUDIT.md's Step 7.5
self-conformance check (53 items). Byte-level drifts in shape are
hard violations; repair the artifact rather than editing
`wont-do.json` to hide it.
