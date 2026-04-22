import json

now = "2026-04-22T14:00:00Z"
date = "2026-04-22"

items = [
    {
        "id": "AUD-2026-04-22-SEC-0001",
        "parent_id": None,
        "epic_id": "AUD-2026-04-22-SEC-0001",
        "level": "epic",
        "type": "security",
        "subtype": "auth/credentials",
        "title": "Security vulnerabilities in F006",
        "fingerprint": "ebbd-f006-sec-epic-0001",
        "moscow": "MUST",
        "assignee": "AGENT",
        "reviewer": "HUMAN",
        "status": "PROPOSED",
        "reported_date": date,
        "reported_run_id": "run-2026-04-22T14:00:00Z",
        "last_updated": now,
        "history": [
            {
                "ts": now,
                "actor": "AGENT",
                "action": "minted",
                "note": "Discovered during 2026-04-22 scan."
            }
        ],
        "details": {
            "what": "Security vulnerabilities in F006",
            "why": "Ensure no hardcoded secrets or other vulnerabilities exist"
        },
        "evidence": [],
        "links": {"related": [], "supersedes": None, "superseded_by": None}
    },
    {
        "id": "AUD-2026-04-22-SEC-0002",
        "parent_id": "AUD-2026-04-22-SEC-0001",
        "epic_id": "AUD-2026-04-22-SEC-0001",
        "level": "story",
        "type": "security",
        "subtype": "auth/credentials",
        "title": "Hardcoded secrets in source files",
        "fingerprint": "ebbd-f006-sec-story-0001",
        "moscow": "MUST",
        "assignee": "AGENT",
        "reviewer": "HUMAN",
        "status": "PROPOSED",
        "reported_date": date,
        "reported_run_id": "run-2026-04-22T14:00:00Z",
        "last_updated": now,
        "history": [
            {
                "ts": now,
                "actor": "AGENT",
                "action": "minted",
                "note": "Discovered during 2026-04-22 scan."
            }
        ],
        "details": {
            "what": "Hardcoded secrets in source files",
            "why": "Prevent unauthorized access using leaked credentials",
            "who": "AGENT",
            "when": "Next run",
            "where": "src/app.js"
        },
        "evidence": [],
        "links": {"related": [], "supersedes": None, "superseded_by": None}
    },
    {
        "id": "AUD-2026-04-22-SEC-0003",
        "parent_id": "AUD-2026-04-22-SEC-0002",
        "epic_id": "AUD-2026-04-22-SEC-0001",
        "level": "task",
        "type": "security",
        "subtype": "auth/credentials",
        "title": "Remove hardcoded AWS access key from src/app.js",
        "fingerprint": "ebbd-f006-sec-task-0001",
        "moscow": "MUST",
        "assignee": "AGENT",
        "reviewer": "HUMAN",
        "status": "PROPOSED",
        "reported_date": date,
        "reported_run_id": "run-2026-04-22T14:00:00Z",
        "last_updated": now,
        "severity": "high",
        "history": [
            {
                "ts": now,
                "actor": "AGENT",
                "action": "minted",
                "note": "Discovered during 2026-04-22 scan."
            }
        ],
        "details": {
            "what": "Remove hardcoded AWS access key from src/app.js",
            "why": "A hardcoded AWS access key exposes the AWS account to unauthorized access and potential compromise.",
            "who": "AGENT",
            "when": "Next run",
            "where": "src/app.js",
            "how": "Extract the secret to an environment variable or secure vault.",
            "constraints": "Must not break existing tests.",
            "cost": { "effort_hours": 1, "risk": "low", "blast_radius": "one function" },
            "5m": { "man": "1 dev", "machine": "CI time", "material": "n/a", "method": "refactor", "measurement": "passing tests" }
        },
        "evidence": [
            {
                "path": "src/app.js",
                "lines": "5",
                "snippet": "const AWS_ACCESS_KEY_ID = \"[REDACTED:aws-key]\";"
            }
        ],
        "links": {"related": [], "supersedes": None, "superseded_by": None}
    }
]

index_data = {
    "schema_version": 1,
    "items": items
}

report_data = {
  "schema_version": 1,
  "report_date": "2026-04-22",
  "generated_runs": [
    {
      "run_id": "run-2026-04-22T14:00:00Z",
      "mode": "scan",
      "timestamp": "2026-04-22T14:00:00Z",
      "findings_new": 3,
      "findings_merged": 0,
      "findings_deduped": 0,
      "truncated": True
    }
  ],
  "counts": {
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
  "items": items
}

with open(".audit/state/index.json", "w") as f:
    json.dump(index_data, f, indent=2)

with open(".audit/reports/2026/04/2026-04-22.json", "w") as f:
    json.dump(report_data, f, indent=2)

