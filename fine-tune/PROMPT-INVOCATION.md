# PROMPT-INVOCATION.md — How to trigger AUDIT.md from any IDE, CLI, or API

**Purpose.** Copy-paste-ready invocation prompts for triggering `AUDIT.md` in scan / review / execute / consolidate mode, across every IDE, terminal, and model you're likely to use. Each template is model-agnostic where possible; model-specific notes are called out.

**Invariant.** AUDIT.md already specifies its own invocation interface in §INVOCATION (lines 605–622). These templates are wrappers that hand the spec to a model and tell it to enter scan mode, while also capturing the outputs the fine-tune harness needs.

---

## The canonical invocation (universal)

Every invocation, regardless of IDE, reduces to four pieces of information:

1. **Read AUDIT.md** — the model must load the spec first.
2. **MODE** — one of `scan` | `review` | `execute` | `consolidate`.
3. **SCOPE** — a repo-relative path or glob. Default `.`.
4. **OUTPUT ROOT** — where to write `.audit/`. Default `./.audit/`.

Then stop and report. Nothing else.

---

## Template A — Universal (works in Cursor, VSCode+Copilot, JetBrains AI, Windsurf, Zed, any IDE-chat)

Paste this into the chat panel once you have `AUDIT.md` open in the workspace:

```
You are the AI Repository Audit Agent defined in AUDIT.md.

1. Read /AUDIT.md in full, including §ROLE, §CRITICAL ANTI-DRIFT RULES, and §SCAN PROCEDURE.
2. Operate in MODE=scan, SCOPE=., DRY_RUN=false, RUN_TRIGGER=manual.
3. Walk the current workspace as the repo under scope. Do NOT scan .audit/ itself (§3.r).
4. Produce a complete .audit/ directory tree per §DIRECTORY & FILE LAYOUT.
5. Execute every Step 7.5 self-conformance check. If any hard violation, REPAIR (do not delete to pass — §3.i, §Step 7.5 anti-gaming items).
6. End with the HITL banner (§13) and the Run Summary JSON block (§OUTPUT CONTRACT).

After the Run Summary, also emit a separate fenced block labeled "capture" with this JSON (for the fine-tune harness):

```capture
{
  "run_id": "<same run_id as Run Summary>",
  "timestamp": "<ISO-8601 UTC>",
  "audit_md_version": "<sha256 of AUDIT.md contents>",
  "model_id": "<your model id, e.g. claude-sonnet-4.6>",
  "ide_id": "<cursor|vscode|jetbrains|windsurf|zed|cli|raw-api>",
  "fixture_id": "<fixture or repo slug>",
  "step_7_5_passed": <true|false>,
  "violations": [
    {"check": "<§ref>", "severity": "hard|soft", "evidence": "<short excerpt, redacted>", "drift_pattern": "<slug>"}
  ],
  "notes": "<free-form, optional>"
}
```

Do NOT modify any file outside .audit/. Stop after emitting the two blocks.
```

**How the human uses it:**

1. Open your IDE's chat panel with AUDIT.md loaded as a context file.
2. Paste the template above.
3. Replace `<your model id>` and `<cursor|vscode|...>` with your actual model/IDE.
4. Wait for the response. Copy the `.audit/` output + `capture` block into `fine-tune/evals/runs/YYYY-MM-DD/<run_id>/`.

---

## Template B — Cursor (with `@` file references)

Cursor lets you pin files into context. Use this shorter form:

```
@AUDIT.md

Run AUDIT.md in scan mode on this workspace. Follow §SCAN PROCEDURE Steps 0–8 exactly, including Step 7.5 self-conformance. Output .audit/ at workspace root. After the Run Summary JSON, emit a second fenced block labeled "capture" with my run metadata (model_id=<claude-sonnet-4.6 or your pick>, ide_id=cursor).
```

Pin AUDIT.md and any relevant code dirs via `@`.

---

## Template C — GitHub Copilot Chat (VSCode / JetBrains / Visual Studio)

Copilot Chat reads workspace files but its context window is smaller. Break the invocation in two:

**Turn 1 (load spec):**
```
#file:AUDIT.md Summarize the §ROLE and §CRITICAL ANTI-DRIFT RULES sections so you can follow them exactly.
```

**Turn 2 (run scan):**
```
Now operate as the AI Repository Audit Agent. MODE=scan, SCOPE=., DRY_RUN=false. Walk #codebase. Produce the full .audit/ tree per §DIRECTORY & FILE LAYOUT. Execute Step 7.5. End with HITL banner + Run Summary JSON + a "capture" block (fields: run_id, timestamp, audit_md_version, model_id=copilot-<model>, ide_id=vscode, fixture_id=<slug>, step_7_5_passed, violations[], notes).
```

Copilot tends to lose long instructions over multiple turns — verify at Turn 3 that Step 7.5 actually ran by asking *"Show me the Step 7.5 conformance outcome block."* If it can't, the run is invalid.

---

## Template D — Gemini in IDE (Gemini Code Assist, AI Studio)

```
System: You are the AI Repository Audit Agent per AUDIT.md. Follow §ROLE and §CRITICAL ANTI-DRIFT RULES literally.

User: [attach AUDIT.md] Run AUDIT.md in MODE=scan on this repo. Output .audit/ tree per §DIRECTORY & FILE LAYOUT. Execute Step 7.5 self-conformance. Finish with HITL banner + Run Summary JSON + a "capture" block (model_id=gemini-<version>, ide_id=gemini-code).
```

Note: Gemini sometimes collapses tables into prose. If §1 (TYPE3 table) gets mangled, re-prompt with *"The 12 canonical TYPE3 codes are a closed set. Enumerate them from AUDIT.md §1 verbatim before writing any item ID."*

---

## Template E — Claude Code CLI (terminal)

```bash
# From your repo root, with AUDIT.md committed:
claude "Read ./AUDIT.md and run it in MODE=scan on the current directory. Follow §SCAN PROCEDURE Steps 0–8. Execute Step 7.5. End with HITL banner + Run Summary JSON + capture block (model_id=\$CLAUDE_MODEL, ide_id=claude-code-cli, fixture_id=\$(basename \$PWD))."
```

Or via a slash command. Create `.claude/commands/audit-scan.md` once:

```markdown
---
description: Run AUDIT.md in scan mode on the current repo
---
Read ./AUDIT.md and operate as the AI Repository Audit Agent.

MODE=scan, SCOPE=., DRY_RUN=false, RUN_TRIGGER=manual.

Follow §SCAN PROCEDURE Steps 0–8 exactly. Execute Step 7.5 self-conformance.
End with §13 HITL banner + Run Summary JSON + capture block.

Capture block fields: run_id, timestamp, audit_md_version (sha256 of AUDIT.md),
model_id (your Claude model), ide_id=claude-code-cli, fixture_id=${1:-.},
step_7_5_passed, violations[], notes.
```

Then invoke with `/audit-scan` or `/audit-scan <fixture-slug>`.

---

## Template F — Gemini CLI / other terminal agents

```bash
gemini "$(cat <<'EOF'
Read AUDIT.md (in the current directory). Operate as the AI Repository Audit Agent.
MODE=scan, SCOPE=., DRY_RUN=false.
Follow §SCAN PROCEDURE Steps 0-8. Execute Step 7.5.
Emit HITL banner + Run Summary JSON + capture block with:
run_id, timestamp, audit_md_version (sha256 of AUDIT.md),
model_id (gemini-<version>), ide_id=gemini-cli,
fixture_id=<slug>, step_7_5_passed, violations[].
Do NOT modify files outside .audit/.
EOF
)"
```

The same pattern works for `cursor-agent`, `aider`, `cline`, `continue`, etc. — swap the CLI name and the `ide_id`.

---

## Template G — Raw API (Anthropic / OpenAI / Gemini)

For programmatic / headless runs (use this when you're building the automated fine-tune loop):

```bash
# Anthropic (Claude)
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d @- <<JSON
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 16000,
  "system": "You are the AI Repository Audit Agent. Follow the attached AUDIT.md literally.",
  "messages": [
    {"role": "user", "content": [
      {"type": "text", "text": "<AUDIT.md contents here>\n\n---\n\nMODE=scan SCOPE=. DRY_RUN=false.\nRun §SCAN PROCEDURE Steps 0-8. Execute Step 7.5.\nOutput: HITL banner, Run Summary JSON, capture block.\nRepo tree follows:"},
      {"type": "text", "text": "<flattened repo listing and key file contents>"}
    ]}
  ]
}
JSON
```

For OpenAI / Gemini the shape is the same: system message sets the role, user message contains AUDIT.md + the repo dump + the mode directive.

**Practical note:** In API mode, the model can't walk a filesystem. You must pre-flatten the repo and include it in the prompt. Use a small harness script that:

1. Reads `AUDIT.md` → computes sha256 → injects as `audit_md_version`.
2. Flattens the repo (git-aware; respect `.gitignore`, skip files listed in `exclusions.paths`/`exclusions.globs` from §14).
3. Sends the request.
4. Parses the response for the `Run Summary` and `capture` JSON blocks.
5. Writes the response into `fine-tune/evals/runs/YYYY-MM-DD/<run_id>/.audit/` and `capture.json`.

This is the pathway `scripts/run-baseline.sh` will wrap when it's fully implemented.

---

## Template H — Mode-specific short forms

For day-to-day work where the harness isn't the goal, you don't need the capture block. Use these:

### Scan (discover)
```
Run AUDIT.md in scan mode.
```

### Review (summarize pending)
```
Run AUDIT.md in review mode on today's report.
```

### Execute (implement approved items)
```
Run AUDIT.md in execute mode. Only touch items where assignee=AGENT and status=APPROVED. DRY_RUN=true first; show the diff; I'll flip to DRY_RUN=false after I approve.
```

### Consolidate (merge dupes, rotate files)
```
Run AUDIT.md in consolidate mode.
```

These short forms work because AUDIT.md's §INVOCATION accepts inline instructions with precedence over env vars. The model pulls SCOPE=. and the other defaults automatically.

---

## Gotchas (all IDEs)

1. **Don't trust the IDE's context on whether AUDIT.md is loaded.** Explicitly say "Read AUDIT.md first." Some IDEs attach files but don't feed them until asked.
2. **TYPE3 hallucination is the #1 drift.** Any model will try to invent "OPS", "UI", "API", "DB". Your prompt doesn't need to re-list the 12 codes — but asking the model to *quote* AUDIT.md §1 before minting any ID catches most invention.
3. **Long outputs truncate in some IDE chat panels.** If the response is cut mid-JSON, ask for *"just the capture block, nothing else"* as a second turn.
4. **Some IDEs rewrite your code when you paste it.** VSCode Copilot Chat has been observed to auto-insert code into open files when the agent's output contained a code block. Run the invocation with no editor windows showing source files you care about.
5. **Temperature matters.** Set to 0 (or as low as your IDE allows) for scan runs. Fingerprints are deterministic in theory; they'll drift if the model rewrites the same finding with different prose at high temperature.
6. **Fingerprint AUDIT.md before you run.** The capture block needs `audit_md_version: sha256:...`. If you don't know it, run `shasum -a 256 AUDIT.md` (macOS/Linux) or `Get-FileHash -Algorithm SHA256 AUDIT.md` (Windows PowerShell) and paste the result in.

---

## Quick reference card

| I want to... | Paste this |
|---|---|
| Run a scan, any IDE | Template A |
| Run a scan in Cursor | Template B |
| Run a scan in VSCode+Copilot | Template C |
| Run a scan with Gemini | Template D |
| Run a scan in Claude CLI | Template E |
| Run a scan in a generic CLI | Template F |
| Run a scan via raw API | Template G |
| Quick review / execute / consolidate | Template H |

---

*End of PROMPT-INVOCATION.md.*
