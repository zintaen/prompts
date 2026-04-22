# evals/runs/ — scan-run archive

Every manual AUDIT.md scan invocation produces a subdirectory here:

```
runs/
├── YYYY-MM-DD/
│   ├── ft-2026-04-20T10:14:01Z-a1b2/
│   │   ├── capture.json
│   │   └── .audit/          ← full snapshot of the agent's output
│   └── ft-…-b2c3/
└── YYYY-MM-DD/ …
```

`capture.json` is the handoff to `ANALYZER.md`. `.audit/` is the raw
output that the analyzer reads when it needs deeper evidence than
`capture.json` provides.

**Do not edit runs after the fact.** They are the ground truth the
analyzer and the diff scripts rely on. If a run was malformed (e.g.,
the model crashed halfway), delete the whole `<run_id>/` directory
rather than patching its contents.

**Index.** A lightweight listing (optional) lives in `index.jsonl` —
one line per run with `{run_id, date, fixture, model, ide, audit_md_version,
step_7_5_passed}`. `capture-run.sh` can append to it (TODO in the script).
