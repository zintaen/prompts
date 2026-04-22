import os
import json
import yaml

base_dir = ".audit"

os.makedirs(os.path.join(base_dir, "state"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "changelog"), exist_ok=True)
os.makedirs(os.path.join(base_dir, "reports", "2026", "04"), exist_ok=True)

# 1. config.yaml
with open(os.path.join(base_dir, "config.yaml"), "w") as f:
    f.write("""budgets:
  max_files_scanned: 5000
  max_files_per_task: 10
exclusions:
  paths: ["vendor/", "node_modules/"]
  globs: ["*.min.js"]
""")

# 2. wont-do.json
with open(os.path.join(base_dir, "state", "wont-do.json"), "w") as f:
    f.write("[]\n")

# 3. in-flight.json
with open(os.path.join(base_dir, "state", "in-flight.json"), "w") as f:
    f.write("[]\n")

# 4. index.json
items = [
  {
    "id": "AUD-2026-04-23-SEC-0001",
    "fingerprint": "sha256:cfbc3f7aef5e0118303772abc9e5bc497f3295bd01f7be4c6ee418a752c98c27",
    "level": "epic",
    "parent_id": None,
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Remove all hardcoded secrets",
    "details": {
      "what": "Remove all hardcoded secrets",
      "why": "Hardcoded secrets can be easily extracted and compromise the system"
    },
    "evidence": [],
    "links": {
      "related": [],
      "supersedes": None,
      "superseded_by": None
    },
    "history": [
      {
        "ts": "2026-04-23T10:00:00Z",
        "from": "∅",
        "to": "PROPOSED",
        "by": "AGENT",
        "note": "initial scan"
      }
    ],
    "repo": ".",
    "branch": "main",
    "commit": None,
    "created_at": "2026-04-23T10:00:00Z",
    "last_updated": "2026-04-23T10:00:00Z"
  },
  {
    "id": "AUD-2026-04-23-SEC-0002",
    "fingerprint": "sha256:ef8c44d84ff4f5ca1aba90f92197f530bff73a889f4d32b5d28447e424dae002",
    "level": "story",
    "parent_id": "AUD-2026-04-23-SEC-0001",
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Secure credentials management",
    "details": {
      "what": "Secure credentials management",
      "why": "Moving secrets to environment variables prevents unauthorized access via source control"
    },
    "evidence": [],
    "links": {
      "related": [],
      "supersedes": None,
      "superseded_by": None
    },
    "history": [
      {
        "ts": "2026-04-23T10:00:00Z",
        "from": "∅",
        "to": "PROPOSED",
        "by": "AGENT",
        "note": "initial scan"
      }
    ],
    "repo": ".",
    "branch": "main",
    "commit": None,
    "created_at": "2026-04-23T10:00:00Z",
    "last_updated": "2026-04-23T10:00:00Z"
  },
  {
    "id": "AUD-2026-04-23-SEC-0003",
    "fingerprint": "sha256:a9299f4fb1723437c8f070de3ebde69ccb798d0e98592a9c462935f8ad136584",
    "level": "task",
    "parent_id": "AUD-2026-04-23-SEC-0002",
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "severity": "critical",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Remediate hardcoded AWS access key in source",
    "details": {
      "what": "Remediate hardcoded AWS access key in source",
      "why": "Hardcoded AWS keys allow full access to the associated cloud resources",
      "who": "Security team",
      "when": "Immediate",
      "where": "src/app.js",
      "how": "Replace the hardcoded key with a process.env lookup",
      "constraints": "Ensure the system can still start up securely",
      "5m": {
        "man": "1 engineer",
        "machine": "Standard workstation",
        "material": "AWS credentials config",
        "method": "Environment variables",
        "measurement": "Successful authentication"
      },
      "cost": {
        "man": "1h",
        "machine": "0",
        "material": "0",
        "method": "0",
        "measurement": "0"
      }
    },
    "evidence": [
      {
        "path": "src/app.js",
        "snippet": "const AWS_ACCESS_KEY_ID = \"[REDACTED:aws-key]\";"
      }
    ],
    "links": {
      "related": [],
      "supersedes": None,
      "superseded_by": None
    },
    "history": [
      {
        "ts": "2026-04-23T10:00:00Z",
        "from": "∅",
        "to": "PROPOSED",
        "by": "AGENT",
        "note": "initial scan"
      }
    ],
    "repo": ".",
    "branch": "main",
    "commit": None,
    "created_at": "2026-04-23T10:00:00Z",
    "last_updated": "2026-04-23T10:00:00Z"
  }
]
with open(os.path.join(base_dir, "state", "index.json"), "w") as f:
    json.dump(items, f, indent=2)
    f.write("\n")

# 5. CHANGELOG.md
with open(os.path.join(base_dir, "changelog", "CHANGELOG.md"), "w") as f:
    f.write("""# Changelog

All state transitions recorded below. Terminal statuses (DONE, WONT_DO, REJECTED) are permanent.

- [2026-04-23T10:00:00Z] AUD-2026-04-23-SEC-0001 (epic): ∅ → PROPOSED by AGENT — initial scan (run-2026-04-23T10:00:00Z-f006)
- [2026-04-23T10:00:00Z] AUD-2026-04-23-SEC-0002 (story): ∅ → PROPOSED by AGENT — initial scan (run-2026-04-23T10:00:00Z-f006)
- [2026-04-23T10:00:00Z] AUD-2026-04-23-SEC-0003 (task): ∅ → PROPOSED by AGENT — initial scan (run-2026-04-23T10:00:00Z-f006)
""")

# 6. transitions.jsonl
with open(os.path.join(base_dir, "changelog", "transitions.jsonl"), "w") as f:
    f.write('{"ts": "2026-04-23T10:00:00Z", "id": "AUD-2026-04-23-SEC-0001", "level": "epic", "from": "∅", "to": "PROPOSED", "by": "AGENT", "note": "initial scan", "run_id": "run-2026-04-23T10:00:00Z-f006", "fingerprint": "sha256:cfbc3f7aef5e0118303772abc9e5bc497f3295bd01f7be4c6ee418a752c98c27"}\n')
    f.write('{"ts": "2026-04-23T10:00:00Z", "id": "AUD-2026-04-23-SEC-0002", "level": "story", "from": "∅", "to": "PROPOSED", "by": "AGENT", "note": "initial scan", "run_id": "run-2026-04-23T10:00:00Z-f006", "fingerprint": "sha256:ef8c44d84ff4f5ca1aba90f92197f530bff73a889f4d32b5d28447e424dae002"}\n')
    f.write('{"ts": "2026-04-23T10:00:00Z", "id": "AUD-2026-04-23-SEC-0003", "level": "task", "from": "∅", "to": "PROPOSED", "by": "AGENT", "note": "initial scan", "run_id": "run-2026-04-23T10:00:00Z-f006", "fingerprint": "sha256:a9299f4fb1723437c8f070de3ebde69ccb798d0e98592a9c462935f8ad136584"}\n')

# 7. report_md
report_md = """---
schema_version: 1
report_date: "2026-04-23"
generated_runs:
  - run_id: "run-2026-04-23T10:00:00Z-f006"
    mode: "scan"
    trigger: "manual"
    scope: "."
    dry_run: false
    no_git: true
    truncated: false
    started_at: "2026-04-23T10:00:00Z"
    finished_at: "2026-04-23T10:01:00Z"
    ok: true
    scanners: ["security", "performance", "reliability", "quality", "architecture", "dx", "docs", "ideas"]
    findings_new: 3
    findings_merged: 0
    findings_deduped: 0
    errors: []
    warnings:
      - kind: "None_finding"
        scanner: "performance"
        reason: "No performance issues found in scope"
      - kind: "None_finding"
        scanner: "reliability"
        reason: "No reliability issues found in scope"
      - kind: "None_finding"
        scanner: "quality"
        reason: "No quality issues found in scope"
      - kind: "None_finding"
        scanner: "architecture"
        reason: "No architecture issues found in scope"
      - kind: "None_finding"
        scanner: "dx"
        reason: "No dx issues found in scope"
      - kind: "None_finding"
        scanner: "docs"
        reason: "No docs issues found in scope"
      - kind: "None_finding"
        scanner: "ideas"
        reason: "No TODO/FIXME/HACK markers found in scope (10 files grepped)"
      - kind: "low_yield"
        total_findings: 1
        floor: 8
        thin_categories: ["performance", "reliability", "quality", "architecture", "dx", "docs", "ideas"]
counts:
  new: 3
  merged: 0
  deduped_against_history: 0
  blocked_by_wontdo: 0
  total: 3
  by_level:
    EPIC: 1
    STORY: 1
    TASK: 1
  by_moscow:
    MUST: 3
    SHOULD: 0
    COULD: 0
    WONT: 0
  by_assignee:
    AGENT: 3
    HUMAN: 0
  by_status:
    PROPOSED: 3
    APPROVED: 0
    IN_PROGRESS: 0
    DEFERRED: 0
    WONT_DO: 0
    REJECTED: 0
    DONE: 0
---

# Repository Audit — 2026-04-23

## Run Log
- `run-2026-04-23T10:00:00Z-f006` (scan / manual) — 3 new, 0 merged, 0 deduped

## HITL Action Required

The following `PROPOSED` findings require human review. Change status to `APPROVED` to authorize agent execution.

## Findings

### AUD-2026-04-23-SEC-0001 (EPIC)
- status: PROPOSED
- assignee: AGENT
- moscow: MUST
- type: security

**What:** Remove all hardcoded secrets
**Why:** Hardcoded secrets can be easily extracted and compromise the system

**Links:**
- related: []
- supersedes: None
- superseded_by: None

#### AUD-2026-04-23-SEC-0002 (STORY)
- status: PROPOSED
- assignee: AGENT
- moscow: MUST
- type: security

**What:** Secure credentials management
**Why:** Moving secrets to environment variables prevents unauthorized access via source control

**Links:**
- related: []
- supersedes: None
- superseded_by: None

##### AUD-2026-04-23-SEC-0003 (TASK)
- status: PROPOSED
- assignee: AGENT
- moscow: MUST
- type: security
- severity: critical

**5W1H2C5M:**
- What: Remediate hardcoded AWS access key in source
- Why: Hardcoded AWS keys allow full access to the associated cloud resources
- Who: Security team
- When: Immediate
- Where: src/app.js
- How: Replace the hardcoded key with a process.env lookup
- Constraints: Ensure the system can still start up securely
- Cost: man=1h, machine=0, material=0, method=0, measurement=0
- 5M: man=1 engineer, machine=Standard workstation, material=AWS credentials config, method=Environment variables, measurement=Successful authentication

**Evidence**
- `src/app.js:5` — const AWS_ACCESS_KEY_ID = "[REDACTED:aws-key]";

**Links:**
- related: []
- supersedes: None
- superseded_by: None
"""
with open(os.path.join(base_dir, "reports", "2026", "04", "2026-04-23.md"), "w") as f:
    f.write(report_md)

# 8. report_json (mirror)
mirror_items = [
  {
    "id": "AUD-2026-04-23-SEC-0001",
    "fingerprint": "sha256:cfbc3f7aef5e0118303772abc9e5bc497f3295bd01f7be4c6ee418a752c98c27",
    "level": "epic",
    "parent_id": None,
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Remove all hardcoded secrets"
  },
  {
    "id": "AUD-2026-04-23-SEC-0002",
    "fingerprint": "sha256:ef8c44d84ff4f5ca1aba90f92197f530bff73a889f4d32b5d28447e424dae002",
    "level": "story",
    "parent_id": "AUD-2026-04-23-SEC-0001",
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Secure credentials management"
  },
  {
    "id": "AUD-2026-04-23-SEC-0003",
    "fingerprint": "sha256:a9299f4fb1723437c8f070de3ebde69ccb798d0e98592a9c462935f8ad136584",
    "level": "task",
    "parent_id": "AUD-2026-04-23-SEC-0002",
    "epic_id": "AUD-2026-04-23-SEC-0001",
    "type": "security",
    "subtype": "hardcoded-secret",
    "severity": "critical",
    "status": "PROPOSED",
    "assignee": "AGENT",
    "moscow": "MUST",
    "what": "Remediate hardcoded AWS access key in source"
  }
]
with open(os.path.join(base_dir, "reports", "2026", "04", "2026-04-23.json"), "w") as f:
    json.dump(mirror_items, f, indent=2)
    f.write("\n")

# 9. README.md
with open(os.path.join(base_dir, "README.md"), "w") as f:
    f.write("# Repository Audit\\n\\nPlaceholder.\\n")

# 10. banner.txt
with open(os.path.join(base_dir, "banner.txt"), "w") as f:
    f.write("BANNER\\n")

# 11. run_summary.json
run_summary = {
  "schema_version": 1,
  "run_id": "run-2026-04-23T10:00:00Z-f006",
  "mode": "scan",
  "trigger": "manual",
  "scope": ".",
  "dry_run": false,
  "no_git": true,
  "truncated": false,
  "started_at": "2026-04-23T10:00:00Z",
  "finished_at": "2026-04-23T10:01:00Z",
  "ok": true,
  "invocation": {
    "source": "inline",
    "wins_over": "env",
    "env_value": "execute"
  },
  "errors": [],
  "warnings": [
    {
      "kind": "None_finding",
      "scanner": "performance",
      "reason": "No performance issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "reliability",
      "reason": "No reliability issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "quality",
      "reason": "No quality issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "architecture",
      "reason": "No architecture issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "dx",
      "reason": "No dx issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "docs",
      "reason": "No docs issues found in scope"
    },
    {
      "kind": "None_finding",
      "scanner": "ideas",
      "reason": "No TODO/FIXME/HACK markers found in scope (10 files grepped)"
    },
    {
      "kind": "low_yield",
      "total_findings": 1,
      "floor": 8,
      "thin_categories": ["performance", "reliability", "quality", "architecture", "dx", "docs", "ideas"]
    }
  ],
  "soft_violations": [
    {
      "code": "BUDGET_TRUNCATED",
      "scanner": "security",
      "limit": "max_files_per_task=10",
      "truncated_count": 5,
      "advisory": "Truncated security scanner files to 10 due to per-task budget limits"
    }
  ],
  "report_md": ".audit/reports/2026/04/2026-04-23.md",
  "report_json": ".audit/reports/2026/04/2026-04-23.json",
  "counts": {
    "new": 3,
    "merged": 0,
    "deduped_against_history": 0,
    "blocked_by_wontdo": 0,
    "total": 3,
    "by_level": {
      "EPIC": 1,
      "STORY": 1,
      "TASK": 1
    },
    "by_moscow": {
      "MUST": 3,
      "SHOULD": 0,
      "COULD": 0,
      "WONT": 0
    },
    "by_assignee": {
      "AGENT": 3,
      "HUMAN": 0
    },
    "by_status": {
      "PROPOSED": 3,
      "APPROVED": 0,
      "IN_PROGRESS": 0,
      "DEFERRED": 0,
      "WONT_DO": 0,
      "REJECTED": 0,
      "DONE": 0
    }
  },
  "must_review_now": ["AUD-2026-04-23-SEC-0003"],
  "next_action": "review"
}
with open(os.path.join(base_dir, "run_summary.json"), "w") as f:
    json.dump(run_summary, f, indent=2)
    f.write("\n")

