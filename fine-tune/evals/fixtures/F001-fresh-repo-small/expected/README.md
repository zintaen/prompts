# F001 expected/ — reference outputs

Place a canonical "good" `.audit/` output here AFTER the first time a
model × IDE run against `repo/` passes all criteria in `../fixture.yaml`
and `../../../criteria.md`.

This directory is the reference other runs get compared to for
byte-level checks that criteria.md calls out (daily .md canonical shape,
sort order of state/index.json, etc.). It is NOT the authoritative
pass/fail — `criteria.md` is — but it is a useful visual diff target.

Suggested contents once populated:
- `state/index.json`
- `daily/<date>.md`
- `daily/<date>.json`
- `transitions.jsonl`
- `evidence/AUD-SEC-0001.txt` (redacted)
- `evidence/AUD-PRF-0002.txt`

Until then: empty on purpose.
