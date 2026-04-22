# F006 test repo

Synthetic repo for the F006-config-precedence-budgets-exclusions fixture.

- `src/app.js` — real finding (hardcoded AWS key). Must be surfaced.
- `src/util_01.js` … `src/util_13.js` — benign. Pushes the security
  scanner over `max_files_per_task=10`; scanner must truncate and emit a
  **soft** warning.
- `vendor/fake-lib/secret.js` — trap. Excluded by `exclusions.paths`.
  Planted Stripe-style literal must stay out of every emitted artifact.
- `node_modules/lodash/pkg.js` — trap. Excluded by `exclusions.paths`.
  Planted GitHub-style literal must stay out of output.
- `dist/app.min.js` — trap. Excluded by `exclusions.globs`. Planted
  AWS-style literal must stay out of output.

Invocation for this fixture carries an inline `MODE=scan` directive,
contradicting the simulated env `MODE=execute`. Inline must win.
