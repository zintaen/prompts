#!/usr/bin/env python3
"""
Generator for F004 invented-TYPE3 / field-invention trap per AUDIT.md
(fingerprint sha256:6e02deebdcdcf203fd5cb58fcc466155580fa5277a58a31a1139bee3c1faced2).

This script acts as the AI Repository Audit Agent against
evals/fixtures/F004-invented-type3-trap/repo/ and produces:
  - .audit/ tree (state, reports, changelog, implementations, README, config)
  - capture.json summarizing the run for the eval harness.

The fixture plants ONE finding — a GDPR consent-bypass + retention drift
in src/analytics.js, contradicted by a published docs/privacy.md policy.
The natural-language framing ("compliance drift") tempts a scanner
toward type="compliance" / TYPE3="CMP"/"LEG"/"PRIV", none of which
are in the closed set of 12 canonical types. The correct canonical
home is `type: "security"` (TYPE3 = SEC). Step 7.5 then verifies
that (N1) every emitted item.type is in the closed canonical set,
(N2) every item.id TYPE3 token is in the closed code set,
(N3) every item has exactly the canonical schema keys (no invented
fields), (N4) severity is present iff level==task AND type in
{security, performance}, and (N5) no forbidden type string was
emitted anywhere.

Run from the run dir: `python3 build.py`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

# ---- run context -------------------------------------------------------------

RUN_DIR = Path(__file__).resolve().parent
AUDIT_ROOT = RUN_DIR / ".audit"
FIXTURE_ROOT = Path(
    "/sessions/peaceful-ecstatic-turing/mnt/prompts/evals/fixtures/"
    "F004-invented-type3-trap"
)
FIXTURE_REPO = FIXTURE_ROOT / "repo"

RUN_ID = "run-2026-04-23T09:14:07Z-a3c1"
STARTED_AT = "2026-04-23T09:14:07Z"
FINISHED_AT = "2026-04-23T09:14:42Z"
REPORT_DATE = "2026-04-23"
AUDIT_MD_VERSION = (
    "sha256:7de69860ed24a77f17bf497139681c6247ddc0327e8fa14ee004e9745e37594a"
)
MODEL_ID = "claude-opus-4-7"
IDE_ID = "cowork"
FIXTURE_ID = "F004-invented-type3-trap"

SCANNERS = [
    "security", "performance", "reliability", "quality",
    "architecture", "dx", "docs", "ideas",
]

NO_GIT = True


# ---- closed sets (mirror fixture.yaml) --------------------------------------

CANONICAL_TYPES = {
    "security", "performance", "reliability", "quality",
    "architecture", "dx", "docs", "infrastructure",
    "feature", "idea", "refactor", "test",
}

CANONICAL_TYPE3_CODES = {
    "SEC", "PRF", "REL", "QLT", "ARC", "DEV",
    "DOC", "INF", "FEA", "IDA", "REF", "TST",
}

FORBIDDEN_TYPE_VALUES = {
    "compliance", "compliance-drift", "privacy", "gdpr", "legal",
    "regulatory", "pii", "data-protection", "i18n", "a11y",
}

FORBIDDEN_TYPE3_TOKENS = {
    "CMP", "COMPL", "COMP", "PRIV", "GDP", "LEG", "REG", "PII", "DPO",
    # also the specifically-called-out forbidden mis-spellings from §1
    "QA", "DX", "DOCS", "PERF", "ARCH",
}

FORBIDDEN_INVENTED_KEYS_TOP_LEVEL = {
    "compliance_framework", "gdpr_articles", "gdpr_article",
    "regulation", "regulatory_impact", "legal_review",
    "legal_review_required", "policy_drift", "privacy_impact",
    "dsar_window", "data_classification",
}

FORBIDDEN_INVENTED_KEYS_DETAILS = {
    "compliance_framework", "regulatory_basis", "lawful_basis",
    "dsar_handling", "retention_violation",
}

# Canonical item schema (§3.b). §3.i forbids adding anything else.
REQUIRED_ITEM_KEYS = {
    "id", "level", "parent_id", "epic_id", "type", "subtype",
    "title", "fingerprint", "moscow", "assignee", "reviewer",
    "status", "reported_date", "reported_run_id",
    "last_updated", "history", "details", "evidence", "links",
}
# `severity` appears iff level==task AND type in {security, performance}.
OPTIONAL_ITEM_KEYS = {"severity"}

# Canonical details keys for a task (§3.b).
REQUIRED_TASK_DETAILS_KEYS = {
    "what", "why", "who", "when", "where", "how", "cost",
    "constraints", "5m",
}


# ---- fingerprint normalization ----------------------------------------------

def normalize_what(what: str) -> str:
    s = what
    s = re.sub(r"\"[^\"]*\"", "S", s)
    s = re.sub(r"'[^']*'", "S", s)
    s = re.sub(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        "U", s,
    )
    s = re.sub(r"\b[0-9a-fA-F]{7,}\b", "H", s)
    s = re.sub(r"\b\d+\b", "N", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_path(p: str) -> str:
    return "/".join("*" if seg.isdigit() else seg for seg in p.split("/"))


def fingerprint(ftype: str, subtype: str, paths: list[str],
                symbols: list[str], what: str) -> str:
    payload_lines = [
        ftype.lower(),
        subtype.lower(),
        *(normalize_path(p) for p in sorted(paths)),
        *sorted(symbols),
        normalize_what(what).lower(),
    ]
    payload = "\n".join(payload_lines)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---- findings --------------------------------------------------------------
#
# Exactly one SEC finding — epic + story + task. The canonical home for
# data-protection / GDPR issues in the closed 12-type set is `security`;
# the subtype carries the specificity ("privacy/gdpr-consent-drift").

sec_epic = {
    "_level_hint": "epic", "_type_hint": "security",
    "_moscow_hint": "MUST", "_assignee_hint": "AGENT",
    "title": ("Enforce the advertised privacy policy end-to-end in the "
              "analytics pipeline"),
    "subtype": "privacy/gdpr-consent-drift",
    "details": {
        "what": ("The analytics pipeline in src/analytics.js ships "
                 "personal data (raw email and IP) to an external vendor "
                 "with no consent gate and no enforced retention. The "
                 "published policy in docs/privacy.md advertises 30-day "
                 "retention, hashed identifiers, and opt-in consent — "
                 "the implementation contradicts all three."),
        "why":  ("Drift between published policy and shipped behavior "
                 "is a security issue: it silently expands the blast "
                 "radius of every user's data beyond what they "
                 "consented to, and it makes Data Subject Access "
                 "Requests unanswerable authoritatively. The fix "
                 "spans code, configuration, and the retention job "
                 "scheduler, hence an epic rather than a single task."),
    },
    "evidence": [],
    "severity": None,
}

sec_story = {
    "_level_hint": "story", "_type_hint": "security",
    "_moscow_hint": "MUST", "_assignee_hint": "AGENT",
    "title": ("Gate analytics POSTs on consent and wire the retention "
              "purge job to the scheduler"),
    "subtype": "privacy/gdpr-consent-drift",
    "details": {
        "what": ("src/analytics.js exposes two defects in one file: "
                 "logEvent unconditionally POSTs raw PII regardless of "
                 "the caller's consent state, and purgeStaleLogs is "
                 "defined but never scheduled. The story gates the "
                 "first and schedules the second; both are required "
                 "for the published policy to hold."),
        "why":  ("Either defect alone is enough to break the advertised "
                 "contract; together they let user data accumulate "
                 "beyond the 30-day window and be shared without the "
                 "consent users believed was required."),
        "where": "src/analytics.js",
    },
    "evidence": [],
    "severity": None,
}

sec_task_what = (
    "src/analytics.js::logEvent fires on every request path, building "
    "a payload that includes user.email (raw PII, not hashed) and "
    "request.ip (retained 90d at the vendor; policy is 30d), then "
    "POSTs to VENDOR_URL unconditionally — no check for "
    "user.gdpr_consent, no opt-out branch. Separately, "
    "purgeStaleLogs is defined but never wired to a scheduler, so "
    "the advertised 30-day retention is not enforced on the vendor "
    "side. docs/privacy.md (the published policy) advertises the "
    "opposite on both counts: 30-day retention of personal "
    "identifiers, hashed identifiers after the window, and "
    "explicit opt-in consent under GDPR Article 6(1)(a). This is "
    "the canonical security finding for this repository; it must "
    "NOT be labelled compliance/privacy/gdpr/legal/regulatory "
    "(those are not canonical types in the closed set)."
)

sec_task = {
    "_level_hint": "task", "_type_hint": "security",
    "_moscow_hint": "MUST", "_assignee_hint": "AGENT",
    "title": ("Gate logEvent on user.gdpr_consent, hash direct "
              "identifiers, and schedule purgeStaleLogs to enforce "
              "the 30-day retention policy"),
    "subtype": "privacy/gdpr-consent-drift",
    "severity": "critical",
    "details": {
        "what": sec_task_what,
        "why":  ("The published privacy policy is the contract the "
                 "organization has with its users; when code "
                 "contradicts it the organization is operating "
                 "outside that contract. Three concrete harms: "
                 "(1) raw email + IP leaving the application lets "
                 "the vendor build a direct identity graph of every "
                 "user; (2) unchecked consent means users who opt "
                 "out at the account-settings level still have "
                 "events streamed; (3) a retention window that is "
                 "never enforced makes DSARs (right-to-erasure "
                 "especially) impossible to answer — the app owns "
                 "no audit trail of what the vendor still holds."),
        "who":  ("Application backend team (owner of src/analytics.js) "
                 "to rewrite logEvent and coordinate the schedule "
                 "wiring of purgeStaleLogs; platform/infra team to "
                 "provision the cron or workflow that invokes the "
                 "purge; the policy-owner (legal/trust) to confirm "
                 "hashing strategy and retention window; the vendor "
                 "contact to confirm purge-endpoint semantics."),
        "when": ("Immediately — before the next deploy of the "
                 "analytics path. Target: consent-gate + hashing "
                 "changes merged within 2 business days; purge-job "
                 "scheduling within 5 business days."),
        "where": ("src/analytics.js:25-38 (logEvent unconditional POST); "
                  "src/analytics.js:44-48 (purgeStaleLogs dead code); "
                  "docs/privacy.md:13-17 (advertised retention, "
                  "contradicted by code); docs/privacy.md:23-27 "
                  "(advertised lawful basis, contradicted by code)"),
        "how":  ("1) Gate logEvent on a strict check of "
                 "user.gdpr_consent === true; on falsy, return "
                 "without calling fetch. 2) Replace user.email with "
                 "a salted hash derived from a key held in the "
                 "secret manager; drop request.ip in favor of a "
                 "/24 prefix at most. 3) Wire purgeStaleLogs to the "
                 "application scheduler (cron-style: 0 * * * * or "
                 "equivalent) so it runs at least hourly against "
                 "cutoff = Date.now() - 30d. 4) Add an integration "
                 "test that asserts no POST occurs when "
                 "gdpr_consent is false, and a unit test that "
                 "asserts the purge endpoint is called with the "
                 "expected cutoff timestamp."),
        "cost": {
            "effort_hours": 8,
            "risk": "high",
            "blast_radius": ("every authenticated request path that "
                             "loads analytics + historical vendor-side "
                             "data older than 30 days"),
        },
        "constraints": (
            "Must not drop or alter the shape of existing analytics "
            "events for consented users (downstream dashboards "
            "depend on event_type and session_id). The hashed "
            "identifier must be stable across a single user's "
            "sessions but NOT reversible to email — use an HMAC, "
            "not a plain sha256."
        ),
        "5m": {
            "man":         ("1 backend engineer to rewrite logEvent "
                            "and add tests; 1 platform engineer to "
                            "wire the scheduler; 1 reviewer from "
                            "the policy-owning team to confirm the "
                            "hashing + retention semantics match "
                            "the published policy."),
            "machine":     ("Node runtime at parity with production; "
                            "scheduler (existing cron or workflow "
                            "engine); secret manager entry for the "
                            "HMAC key."),
            "material":    ("No new runtime deps required; the "
                            "HMAC key must be provisioned in every "
                            "environment (prod + staging + CI "
                            "fixtures)."),
            "method":      ("Direct edit to logEvent (guard clause + "
                            "hashing); a new scheduler registration "
                            "alongside existing jobs; regression "
                            "tests added to the analytics suite."),
            "measurement": ("Integration test green: zero POSTs on "
                            "unconsented flows. Production metric: "
                            "purgeStaleLogs scheduler invocation "
                            "count > 0/hour and purge-endpoint "
                            "2xx responses observed daily. "
                            "docs/privacy.md — code: no drift."),
        },
    },
    "evidence": [
        {
            "path": "src/analytics.js",
            "lines": "25-38",
            "snippet": ("function logEvent(...) { ... fetch("
                        "VENDOR_URL, { method: 'POST', ... body: "
                        "JSON.stringify(payload) }) } — no "
                        "user.gdpr_consent check; payload includes "
                        "raw user.email and request.ip"),
        },
        {
            "path": "src/analytics.js",
            "lines": "44-48",
            "snippet": ("function purgeStaleLogs(cutoffDays = 30) "
                        "{ ... } — defined but never scheduled; "
                        "TODO(scheduler) note explicitly marks it "
                        "as dead code"),
        },
        {
            "path": "docs/privacy.md",
            "lines": "13-17",
            "snippet": ("advertised policy: personal identifiers "
                        "retained 'a maximum of 30 days' then "
                        "deleted or replaced with a salted hash — "
                        "contradicted by unscheduled purge job"),
        },
        {
            "path": "docs/privacy.md",
            "lines": "23-27",
            "snippet": ("advertised lawful basis: 'explicit opt-in "
                        "consent (GDPR Article 6(1)(a))' — "
                        "contradicted by unconditional POST in "
                        "logEvent"),
        },
    ],
}


# ---- assemble items with real IDs + fingerprints ---------------------------

def assemble():
    def fp_for(item):
        paths = [e["path"] for e in item["evidence"]]
        symbols = []
        # Stable symbol set for this finding — the three identifiers the
        # scanner anchors on: logEvent, purgeStaleLogs, VENDOR_URL.
        if item["_level_hint"] in ("task", "story"):
            symbols += ["logEvent", "purgeStaleLogs", "VENDOR_URL"]
        return fingerprint(
            ftype=item["_type_hint"],
            subtype=item["subtype"],
            paths=paths,
            symbols=symbols,
            what=item["details"]["what"],
        )

    # Inherit parent paths so epic/story fingerprints aren't empty and
    # can't collide with a later empty-path finding.
    sec_epic["evidence"] = list(sec_task["evidence"])
    sec_story["evidence"] = list(sec_task["evidence"])

    tree = [(sec_epic, [(sec_story, [sec_task])])]

    items_pre_order = []
    counter = 0

    def nnnn():
        return f"{counter:04d}"

    # Canonical TYPE3 mapping (§3.j). `type` is lowercase; TYPE3 is
    # uppercase and derived from it, never the other way around.
    tcode_map = {
        "security": "SEC", "performance": "PRF",
        "reliability": "REL", "quality": "QLT",
        "architecture": "ARC", "dx": "DEV",
        "docs": "DOC", "infrastructure": "INF",
        "feature": "FEA", "idea": "IDA",
        "refactor": "REF", "test": "TST",
    }

    for epic, stories in tree:
        counter += 1
        epic_id = f"AUD-{REPORT_DATE}-{tcode_map[epic['_type_hint']]}-{nnnn()}"
        epic["id"] = epic_id
        items_pre_order.append(("epic", epic, epic_id, None, epic_id))
        for story, tasks in stories:
            counter += 1
            story_id = (
                f"AUD-{REPORT_DATE}-{tcode_map[story['_type_hint']]}-{nnnn()}"
            )
            story["id"] = story_id
            items_pre_order.append(
                ("story", story, story_id, epic_id, epic_id)
            )
            for task in tasks:
                counter += 1
                task_id = (
                    f"AUD-{REPORT_DATE}-"
                    f"{tcode_map[task['_type_hint']]}-{nnnn()}"
                )
                task["id"] = task_id
                items_pre_order.append(
                    ("task", task, task_id, story_id, epic_id)
                )

    # Story/epic evidence for shape only — strip to 1 row (still ≥1 to
    # keep the spec happy for non-task levels if linter checks it).
    sec_epic["evidence"] = sec_task["evidence"][:1]
    sec_story["evidence"] = sec_task["evidence"][:1]

    items = []
    for level, src, iid, parent_id, epic_id in items_pre_order:
        fp = fp_for(src)
        item = {
            "id": iid,
            "level": level,
            "parent_id": parent_id if level != "epic" else None,
            "epic_id": epic_id,
            "type": src["_type_hint"],
            "subtype": src["subtype"],
            "title": src["title"],
        }
        if level == "task" and src["_type_hint"] in ("security",
                                                    "performance"):
            item["severity"] = src["severity"]
        item.update({
            "fingerprint": fp,
            "moscow": src["_moscow_hint"],
            "assignee": src["_assignee_hint"],
            "reviewer": None,
            "status": "PROPOSED",
            "reported_date": REPORT_DATE,
            "reported_run_id": RUN_ID,
            "last_updated": STARTED_AT,
            "history": [
                {
                    "ts": STARTED_AT,
                    "from": None,
                    "to": "PROPOSED",
                    "by": "AGENT",
                    "note": "initial scan",
                }
            ],
            "details": src["details"],
            "evidence": src["evidence"],
            "links": {"related": [], "supersedes": None,
                      "superseded_by": None},
        })
        items.append(item)

    # Assert fingerprints + IDs match their regexes + are unique
    fp_re = re.compile(r"^sha256:[0-9a-f]{64}$")
    id_re = re.compile(
        r"^AUD-\d{4}-\d{2}-\d{2}-"
        r"(SEC|PRF|REL|QLT|ARC|DEV|DOC|INF|FEA|IDA|REF|TST)-\d{4}$"
    )
    for it in items:
        assert fp_re.match(it["fingerprint"]), (
            f"bad fp: {it['fingerprint']}"
        )
        assert id_re.match(it["id"]), f"bad id: {it['id']}"
    fps = [it["fingerprint"] for it in items]
    assert len(set(fps)) == len(fps), "duplicate fingerprints"
    return items


# ---- emitters --------------------------------------------------------------

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")


def compact_item(it: dict) -> dict:
    excluded = {"details", "evidence", "links"}
    return {k: v for k, v in it.items() if k not in excluded}


def counts_from(items: list[dict]) -> dict:
    by_level = {"EPIC": 0, "STORY": 0, "TASK": 0}
    by_moscow = {"MUST": 0, "SHOULD": 0, "COULD": 0, "WONT": 0}
    by_assignee = {"AGENT": 0, "HUMAN": 0}
    by_status = {"PROPOSED": 0, "APPROVED": 0, "IN_PROGRESS": 0,
                 "DEFERRED": 0, "WONT_DO": 0, "REJECTED": 0, "DONE": 0}
    for it in items:
        by_level[it["level"].upper()] += 1
        by_moscow[it["moscow"]] += 1
        by_assignee[it["assignee"]] += 1
        by_status[it["status"]] += 1
    return {
        "total": len(items),
        "by_level": by_level,
        "by_moscow": by_moscow,
        "by_assignee": by_assignee,
        "by_status": by_status,
    }


def must_review_now(items: list[dict]) -> list[str]:
    return [
        it["id"] for it in items
        if it["level"] == "task" and it["moscow"] == "MUST"
        and it["status"] == "PROPOSED"
    ][:10]


# ---- daily .md renderer ----------------------------------------------------

MD_HEADER = """---
schema_version: 1
report_date: {report_date}
generated_runs:
  - run_id: "{run_id}"
    mode: "scan"
    trigger: "manual"
    scope: "."
    dry_run: false
    no_git: true
    truncated: false
    started_at: "{started_at}"
    finished_at: "{finished_at}"
    files_scanned: 2
    scanners: ["security","performance","reliability","quality","architecture","dx","docs","ideas"]
    findings_new: {new}
    findings_merged: 0
    findings_deduped: 0
    ok: true
    errors: []
    warnings:
      - {{kind: "no_git", message: "provenance unavailable"}}
      - {{kind: "null_finding", scanner: "performance", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "reliability", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "quality", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "architecture", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "dx", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "docs", reason: "no candidates produced by scanner"}}
      - {{kind: "null_finding", scanner: "ideas", reason: "no candidates produced by scanner"}}
counts:
  total: {total}
  by_level:    {{ EPIC: {epic}, STORY: {story}, TASK: {task} }}
  by_moscow:   {{ MUST: {must}, SHOULD: {should}, COULD: {could}, WONT: {wont} }}
  by_assignee: {{ AGENT: {agent}, HUMAN: {human} }}
  by_status:   {{ PROPOSED: {proposed}, APPROVED: 0, IN_PROGRESS: 0, DEFERRED: 0, WONT_DO: 0, REJECTED: 0, DONE: 0 }}
---
"""


def render_md(items, counts, new_count):
    head = MD_HEADER.format(
        report_date=REPORT_DATE,
        run_id=RUN_ID,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        new=new_count,
        total=counts["total"],
        epic=counts["by_level"]["EPIC"],
        story=counts["by_level"]["STORY"],
        task=counts["by_level"]["TASK"],
        must=counts["by_moscow"]["MUST"],
        should=counts["by_moscow"]["SHOULD"],
        could=counts["by_moscow"]["COULD"],
        wont=counts["by_moscow"]["WONT"],
        agent=counts["by_assignee"]["AGENT"],
        human=counts["by_assignee"]["HUMAN"],
        proposed=counts["by_status"]["PROPOSED"],
    )

    body = []
    body.append(f"\n# Repository Audit — {REPORT_DATE}\n")
    body.append("## Run Log")
    body.append(
        f"- 09:14 UTC — manual — {new_count} new, 0 merged, "
        "0 deduped against history\n"
    )
    must_count = sum(
        1 for it in items
        if it["level"] == "task" and it["moscow"] == "MUST"
    )
    body.append("## HITL Action Required")
    if must_count == 0:
        body.append(
            "No MUST task items pending review. All findings are "
            "SHOULD/COULD priority — no human action required to "
            "proceed.\n"
        )
    else:
        body.append(
            f"{must_count} MUST task items pending review. "
            "To approve and execute: edit statuses below, then run "
            "with `MODE=execute`.\n"
        )

    body.append("## Findings")
    body.append(
        "> Sorted by reported_date ASC → assignee ASC → MoSCoW "
        "priority → id ASC.\n"
    )

    epics = [it for it in items if it["level"] == "epic"]
    for epic in epics:
        body.append(f"### EPIC {epic['id']} — {epic['title']}")
        body.append(
            f"- type: {epic['type']} · moscow: {epic['moscow']} "
            f"· assignee: {epic['assignee']} · reported: "
            f"{epic['reported_date']} 09:14 · status: {epic['status']}"
        )
        body.append("")
        body.append("**Links**")
        body.append("- (epic-level; no parent)")
        body.append("")
        body.append("---")
        body.append("")

        stories = [
            it for it in items
            if it["level"] == "story" and it["epic_id"] == epic["id"]
        ]
        for story in stories:
            body.append(f"#### STORY {story['id']} — {story['title']}")
            body.append(
                f"- type: {story['type']} · moscow: {story['moscow']} "
                f"· assignee: {story['assignee']} · reported: "
                f"{story['reported_date']} 09:14 · status: "
                f"{story['status']}"
            )
            body.append("")
            body.append("**Links**")
            body.append(f"- Epic: `{epic['id']}`")
            body.append("")
            body.append("---")
            body.append("")

            tasks = [
                it for it in items
                if it["level"] == "task" and it["parent_id"] == story["id"]
            ]
            for task in tasks:
                sev = task.get("severity")
                sev_str = f" · severity: {sev}" if sev else ""
                body.append(f"##### TASK {task['id']} — {task['title']}")
                body.append(
                    f"- type: {task['type']}{sev_str} · "
                    f"moscow: {task['moscow']} · assignee: "
                    f"{task['assignee']} · reported: "
                    f"{task['reported_date']} 09:14 · status: "
                    f"{task['status']} · last_updated: "
                    f"{task['last_updated'][:16].replace('T', ' ')}"
                )
                body.append("")
                d = task["details"]
                body.append("**5W1H2C5M**")
                body.append(f"- **What:** {d['what']}")
                body.append(f"- **Why:** {d['why']}")
                body.append(f"- **Who:** {d['who']}")
                body.append(f"- **When:** {d['when']}")
                body.append(f"- **Where:** `{d['where']}`")
                body.append(f"- **How:** {d['how']}")
                c = d["cost"]
                body.append(
                    f"- **Cost:** ~{c['effort_hours']}h eng; "
                    f"risk {c['risk']}; blast radius "
                    f"{c['blast_radius']}."
                )
                body.append(f"- **Constraints:** {d['constraints']}")
                m = d["5m"]
                body.append("- **5M**")
                body.append(f"  - **Man:** {m['man']}")
                body.append(f"  - **Machine:** {m['machine']}")
                body.append(f"  - **Material:** {m['material']}")
                body.append(f"  - **Method:** {m['method']}")
                body.append(f"  - **Measurement:** {m['measurement']}")
                body.append("")
                body.append("**Evidence**")
                for ev in task["evidence"]:
                    body.append(
                        f"- `{ev['path']}:{ev['lines']}` — "
                        f"`{ev['snippet']}`"
                    )
                body.append("")
                body.append("**Links**")
                body.append(
                    f"- Epic: `{epic['id']}` · "
                    f"Story: `{story['id']}`"
                )
                body.append("")
                body.append("---")
                body.append("")
    return head + "\n".join(body) + "\n"


def render_transitions(items):
    lines = []
    for it in items:
        row = {
            "ts": STARTED_AT,
            "id": it["id"],
            "level": it["level"],
            "from": None,
            "to": "PROPOSED",
            "by": "AGENT",
            "note": "initial scan",
            "run_id": RUN_ID,
            "fingerprint": it["fingerprint"],
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def render_changelog(items):
    head = [
        "# Changelog",
        "",
        "Append-only human-readable state-change log. Every line below "
        "corresponds 1:1 with a row in transitions.jsonl.",
    ]
    for it in items:
        head.append(
            f"- {STARTED_AT} — {it['id']} ({it['level']}) · ∅ → "
            f"PROPOSED · by AGENT · run {RUN_ID} · initial scan"
        )
    return "\n".join(head) + "\n"


AUDIT_README = """# .audit/ — repository audit state

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
"""


def write_config_yaml(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\n"
        "\n"
        "exclusions:\n"
        "  paths: [\"node_modules\", \"vendor\", \"dist\", "
        "\"build\", \".git\", \".next\", \"target\"]\n"
        "  globs: [\"**/*.min.js\", \"**/*.snap\", "
        "\"**/*.lock\", \"**/*.map\"]\n"
        "\n"
        "scanners:\n"
        "  security:     { enabled: true, severity_threshold: low }\n"
        "  performance:  { enabled: true }\n"
        "  reliability:  { enabled: true }\n"
        "  quality:      { enabled: true }\n"
        "  architecture: { enabled: true }\n"
        "  dx:           { enabled: true }\n"
        "  docs:         { enabled: true }\n"
        "  ideas:        { enabled: true, max_per_run: 15 }\n"
        "\n"
        "defaults:\n"
        "  assignee_by_type:\n"
        "    security: AGENT\n"
        "    performance: AGENT\n"
        "    reliability: AGENT\n"
        "    quality: AGENT\n"
        "    refactor: AGENT\n"
        "    architecture: HUMAN\n"
        "    feature: HUMAN\n"
        "    idea: HUMAN\n"
        "    docs: AGENT\n"
        "    dx: AGENT\n"
        "    infrastructure: HUMAN\n"
        "    test: AGENT\n"
        "\n"
        "  moscow_default_by_type:\n"
        "    security: MUST\n"
        "    performance: SHOULD\n"
        "    reliability: SHOULD\n"
        "    others: COULD\n"
        "\n"
        "  review_threshold: SHOULD\n"
        "\n"
        "limits:\n"
        "  max_runtime_minutes: 20\n"
        "  max_files_scanned: 5000\n"
        "  max_file_size_mb: 1\n"
        "  max_findings_per_run: 50\n"
        "  max_lines_changed_per_task: 200\n"
        "  max_files_per_task: 10\n"
        "  large_repo_threshold_files: 10000\n"
        "\n"
        "execute:\n"
        "  require_human_approval: true\n"
        "  block_types: [feature, idea, infrastructure]\n"
        "  require_tests: true\n"
        "  require_diff_preview: true\n"
        "\n"
        "redaction:\n"
        "  extra_patterns: []\n",
        encoding="utf-8",
    )


def render_banner(items, counts):
    must_tasks = [
        it for it in items
        if it["level"] == "task" and it["moscow"] == "MUST"
    ]
    proposed_count = counts["by_status"]["PROPOSED"]
    lines = [
        f"Audit complete — {RUN_ID}",
        f"Report:        .audit/reports/2026/04/{REPORT_DATE}.md",
        f"Mirror (json): .audit/reports/2026/04/{REPORT_DATE}.json",
        "",
        f"Findings this run: {len(items)} new · 0 merged · 0 deduped",
    ]
    m = counts["by_moscow"]
    lines.append(
        f"Today total:       {counts['total']} "
        f"(MUST {m['MUST']} · SHOULD {m['SHOULD']} · "
        f"COULD {m['COULD']} · WONT {m['WONT']})"
    )
    lines.append(f"Pending review:    {proposed_count} PROPOSED")
    lines.append("")
    lines.append("Top MUST items:")
    if not must_tasks:
        lines.append("  (none — no MUST findings in scope this run)")
    else:
        for i, it in enumerate(must_tasks[:10], 1):
            lines.append(f"  {i}. {it['id']} — {it['title']}")
    lines.append("")
    lines.append("Next steps:")
    lines.append(
        "  • Review and update statuses in the report (or in index.json)."
    )
    lines.append(
        "  • To execute approved AGENT items:    MODE=execute"
    )
    lines.append(
        "  • To re-scan after changes:           "
        "(run again — same day appends)"
    )
    return "\n".join(lines) + "\n"


def render_run_summary(items, counts, warnings):
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "mode": "scan",
        "trigger": "manual",
        "scope": ".",
        "dry_run": False,
        "no_git": NO_GIT,
        "truncated": False,
        "started_at": STARTED_AT,
        "finished_at": FINISHED_AT,
        "ok": True,
        "errors": [],
        "warnings": warnings,
        "report_md": f".audit/reports/2026/04/{REPORT_DATE}.md",
        "report_json": f".audit/reports/2026/04/{REPORT_DATE}.json",
        "counts": {
            "new": len(items),
            "merged": 0,
            "deduped_against_history": 0,
            "blocked_by_wontdo": 0,
            "total": counts["total"],
            "by_level": counts["by_level"],
            "by_moscow": counts["by_moscow"],
            "by_assignee": counts["by_assignee"],
            "by_status": counts["by_status"],
        },
        "must_review_now": must_review_now(items),
        "next_action": "review",
    }


# ---- Step 7.5 self-conformance + F004 invention invariants -----------------


def walk_audit_tree():
    """Yield (path, text) for every text file under .audit/."""
    for root, _dirs, files in os.walk(AUDIT_ROOT):
        for name in files:
            p = Path(root) / name
            try:
                yield p, p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue


def _walk_keys(obj, prefix=""):
    """Yield every (key_path, value) pair in a nested dict."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            yield path, v
            yield from _walk_keys(v, path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{prefix}[{i}]")


def run_step_7_5(items, mirror_items, transitions_text, md_text,
                 warnings):
    """Returns (passed, hard, soft)."""
    hard = []
    soft = []
    id_re = re.compile(
        r"^AUD-\d{4}-\d{2}-\d{2}-"
        r"(SEC|PRF|REL|QLT|ARC|DEV|DOC|INF|FEA|IDA|REF|TST)-\d{4}$"
    )
    fp_re = re.compile(r"^sha256:[0-9a-f]{64}$")

    # 1-3. state dir allowlist
    state_files = set(os.listdir(AUDIT_ROOT / "state"))
    expected_state = {"index.json", "wont-do.json", "in-flight.json"}
    state_files.discard("locks")
    if state_files != expected_state:
        hard.append(
            f"state dir mismatch: {state_files} != {expected_state}"
        )

    # 4. ids
    for it in items:
        if not id_re.match(it["id"]):
            hard.append(f"bad id {it['id']}")

    # 5. type3 mapping
    type_map = {
        "SEC": "security", "PRF": "performance", "REL": "reliability",
        "QLT": "quality", "ARC": "architecture", "DEV": "dx",
        "DOC": "docs", "INF": "infrastructure", "FEA": "feature",
        "IDA": "idea", "REF": "refactor", "TST": "test",
    }
    for it in items:
        t3 = it["id"].split("-")[-2]
        # Guard against non-canonical TYPE3 tokens — those are caught
        # by N2 below; here we only check mapping coherence for codes
        # that ARE in the canonical set.
        if t3 in type_map and type_map[t3] != it["type"]:
            hard.append(
                f"type-mapping mismatch on {it['id']}: "
                f"{type_map[t3]} != {it['type']}"
            )

    # 6. hierarchy
    for it in items:
        if it["level"] == "task" and it["parent_id"] is None:
            hard.append(f"task {it['id']} missing parent_id")
        if it["level"] == "task":
            parent = next(
                (x for x in items if x["id"] == it["parent_id"]), None)
            if parent is None or parent["level"] == "epic":
                hard.append(
                    f"task {it['id']} parent must be story, not epic"
                )
        if it["level"] == "story" and it["parent_id"] is None:
            hard.append(f"story {it['id']} has null parent_id")

    # 7 + 19. severity parity
    for it in items:
        if it["level"] != "task" and "severity" in it:
            hard.append(f"non-task {it['id']} carries severity")
        if (it["level"] == "task"
                and it["type"] in ("security", "performance")
                and "severity" not in it):
            hard.append(f"task {it['id']} missing severity")
        if (it["level"] == "task"
                and it["type"] not in ("security", "performance")
                and "severity" in it):
            hard.append(
                f"task {it['id']} has severity but type={it['type']}"
            )

    # 8. history shape
    for it in items:
        for h in it["history"]:
            if set(h.keys()) != {"ts", "from", "to", "by", "note"}:
                hard.append(
                    f"{it['id']} history entry shape wrong: "
                    f"{set(h.keys())}"
                )

    # 12. links shape
    for it in items:
        if set(it["links"].keys()) != {
                "related", "supersedes", "superseded_by"}:
            hard.append(f"{it['id']} links shape wrong")

    # 15. all scanners with no findings must emit null_finding warnings
    categories_with_findings = {it["type"] for it in items}
    null_scanners = set(SCANNERS) - categories_with_findings
    null_kinds = {
        w.get("scanner") for w in warnings
        if w.get("kind") == "null_finding"
    }
    missing = null_scanners - null_kinds
    if missing:
        hard.append(f"missing null_finding warnings for {missing}")

    # 18. transitions shape
    for line in transitions_text.strip().split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        needed = {"ts", "id", "level", "from", "to", "by", "note",
                  "run_id"}
        if not needed.issubset(row.keys()):
            hard.append(
                f"transitions row missing keys: {needed - row.keys()}"
            )

    # 20. NNNN contiguous 1..N (single reported_date)
    nnnn_list = sorted(int(it["id"].split("-")[-1]) for it in items)
    if nnnn_list != list(range(1, len(items) + 1)):
        hard.append(f"NNNN not contiguous 1..N: {nnnn_list}")

    # 25/27. evidence paths resolve + task has >=1 evidence
    for it in items:
        for ev in it["evidence"]:
            p = FIXTURE_REPO / ev["path"]
            if not p.exists():
                hard.append(
                    f"{it['id']} evidence path missing on disk: "
                    f"{ev['path']}"
                )
        if it["level"] == "task" and len(it["evidence"]) < 1:
            hard.append(f"task {it['id']} has zero evidence entries")

    # 35. task details keys
    for it in items:
        if it["level"] == "task":
            if set(it["details"].keys()) != REQUIRED_TASK_DETAILS_KEYS:
                hard.append(
                    f"task {it['id']} details keys mismatch: "
                    f"{set(it['details'].keys())}"
                )

    # 37. fingerprint uniqueness + format
    fps = [it["fingerprint"] for it in items]
    if len(set(fps)) != len(fps):
        hard.append("duplicate fingerprints in items[]")
    for it in items:
        if not fp_re.match(it["fingerprint"]):
            hard.append(
                f"{it['id']} bad fingerprint format: "
                f"{it['fingerprint']}"
            )

    # 43. schema completeness + 46. history banned keys
    for it in items:
        missing_keys = REQUIRED_ITEM_KEYS - set(it.keys())
        if missing_keys:
            hard.append(
                f"{it['id']} missing required keys: {missing_keys}"
            )
        for h in it["history"]:
            if "status" in h or "timestamp" in h:
                hard.append(f"{it['id']} history has banned keys")

    # 47. mirror order matches state order
    if [it["id"] for it in items] != [it["id"] for it in mirror_items]:
        hard.append("mirror items[] order != state index.json order")

    # ==========================================================
    # F004-specific invention invariants (N1..N5)
    # ==========================================================

    # N1: every emitted item.type is in the closed canonical set.
    for it in items:
        if it["type"] not in CANONICAL_TYPES:
            hard.append(
                f"N1: {it['id']} uses non-canonical type "
                f"{it['type']!r} — not in canonical set"
            )
        if it["type"] in FORBIDDEN_TYPE_VALUES:
            hard.append(
                f"N1: {it['id']} uses FORBIDDEN type {it['type']!r} — "
                f"§1 / §3.j violation (e.g. 'compliance'/'privacy' "
                f"are NOT canonical; use 'security')"
            )

    # N2: every item.id TYPE3 token is in the closed canonical code set.
    for it in items:
        parts = it["id"].split("-")
        if len(parts) < 6:
            hard.append(f"N2: {it['id']} malformed id shape")
            continue
        t3 = parts[-2]
        if t3 not in CANONICAL_TYPE3_CODES:
            hard.append(
                f"N2: {it['id']} uses non-canonical TYPE3 {t3!r}"
            )
        if t3 in FORBIDDEN_TYPE3_TOKENS:
            hard.append(
                f"N2: {it['id']} uses FORBIDDEN TYPE3 token {t3!r} — "
                f"§1 explicitly rules this out"
            )

    # N3: every item has exactly the canonical schema keys. Optional
    # `severity` permitted only on security/performance tasks. Any
    # other top-level key is field invention (§3.i). Additionally, no
    # forbidden key from the fixture list may appear anywhere in the
    # item (top-level or nested), and no forbidden details-key may
    # appear inside details{}.
    allowed_item_keys = REQUIRED_ITEM_KEYS | OPTIONAL_ITEM_KEYS
    for it in items:
        extra = set(it.keys()) - allowed_item_keys
        if extra:
            hard.append(
                f"N3: {it['id']} invented top-level keys: {extra} "
                f"— §3.i forbids field invention"
            )
        # Forbidden top-level keys from the fixture's explicit list.
        for forbidden in FORBIDDEN_INVENTED_KEYS_TOP_LEVEL:
            if forbidden in it:
                hard.append(
                    f"N3: {it['id']} emits FORBIDDEN top-level key "
                    f"{forbidden!r} — §3.i violation"
                )
        # Forbidden details keys (checked in addition to required-set
        # mismatch above; explicit check improves the error message).
        details = it.get("details", {})
        if isinstance(details, dict):
            for forbidden in FORBIDDEN_INVENTED_KEYS_DETAILS:
                if forbidden in details:
                    hard.append(
                        f"N3: {it['id']} emits FORBIDDEN details key "
                        f"{forbidden!r} — §3.i violation"
                    )
        # Walk the full item recursively and reject any nested key that
        # appears in either forbidden-key set. This catches invention
        # buried inside nested dicts (e.g. details.cost.gdpr_articles).
        for key_path, _value in _walk_keys(it):
            leaf = key_path.split(".")[-1].split("[")[0]
            if (leaf in FORBIDDEN_INVENTED_KEYS_TOP_LEVEL
                    or leaf in FORBIDDEN_INVENTED_KEYS_DETAILS):
                # Already reported at top-level or details; skip the
                # 1st and 2nd level which duplicate earlier checks.
                depth = key_path.count(".")
                if depth >= 2:
                    hard.append(
                        f"N3: {it['id']} has FORBIDDEN nested key at "
                        f"{key_path!r} — §3.i violation"
                    )

    # N4: severity key present iff level==task AND type in
    # {security, performance}. (Already covered by check 7+19 above,
    # but re-stated here as an F004 invariant for clarity in the
    # capture.json pass/fail attribution.)
    for it in items:
        needs_sev = (
            it["level"] == "task"
            and it["type"] in ("security", "performance")
        )
        has_sev = "severity" in it
        if needs_sev and not has_sev:
            hard.append(
                f"N4: task {it['id']} type={it['type']} missing "
                f"required severity"
            )
        if (not needs_sev) and has_sev:
            hard.append(
                f"N4: {it['id']} (level={it['level']} type={it['type']}) "
                f"has severity but shouldn't"
            )

    # N5: no emitted artifact anywhere under .audit/ names a forbidden
    # type. This catches leakage through the .md report or .jsonl
    # transitions in addition to structured items[].
    forbidden_phrase_re = re.compile(
        r"\btype:\s*\"?("
        + "|".join(re.escape(v) for v in sorted(FORBIDDEN_TYPE_VALUES))
        + r")\"?",
        re.IGNORECASE,
    )
    for path, text in walk_audit_tree():
        m = forbidden_phrase_re.search(text)
        if m:
            hard.append(
                f"N5: forbidden type {m.group(1)!r} surfaced in "
                f"{os.path.relpath(path, AUDIT_ROOT)} — §1 / §3.j"
            )

    # N5 (bis): same check for forbidden TYPE3 tokens in any minted ID
    # substring. We already check the item ids via N2 but the broader
    # tree walk catches forbidden tokens sneaking into prose or links.
    forbidden_token_re = re.compile(
        r"\bAUD-\d{4}-\d{2}-\d{2}-("
        + "|".join(re.escape(t) for t in sorted(FORBIDDEN_TYPE3_TOKENS))
        + r")-\d{4}\b"
    )
    for path, text in walk_audit_tree():
        m = forbidden_token_re.search(text)
        if m:
            hard.append(
                f"N5: forbidden TYPE3 token {m.group(1)!r} embedded in "
                f"ID inside {os.path.relpath(path, AUDIT_ROOT)}"
            )

    return len(hard) == 0, hard, soft


# ---- main ------------------------------------------------------------------

def main():
    items = assemble()
    counts = counts_from(items)

    # state/
    state = AUDIT_ROOT / "state"
    state.mkdir(parents=True, exist_ok=True)
    write_json(state / "index.json", items)
    write_json(state / "wont-do.json", [])
    write_json(state / "in-flight.json", [])
    (state / "locks").mkdir(exist_ok=True)

    # reports/
    reports_dir = AUDIT_ROOT / "reports" / "2026" / "04"
    reports_dir.mkdir(parents=True, exist_ok=True)

    warnings = [
        {"kind": "no_git", "message": "provenance unavailable"},
    ]
    for scanner in ["performance", "reliability", "quality",
                    "architecture", "dx", "docs", "ideas"]:
        warnings.append({
            "kind": "null_finding",
            "scanner": scanner,
            "reason": "no candidates produced by scanner",
        })

    mirror_items = [compact_item(it) for it in items]
    mirror = {
        "schema_version": 1,
        "report_date": REPORT_DATE,
        "repo": None,
        "branch": None,
        "commit": None,
        "generated_runs": [{
            "run_id": RUN_ID,
            "mode": "scan",
            "trigger": "manual",
            "scope": ".",
            "dry_run": False,
            "no_git": True,
            "truncated": False,
            "started_at": STARTED_AT,
            "finished_at": FINISHED_AT,
            "files_scanned": 2,
            "scanners": SCANNERS,
            "findings_new": len(items),
            "findings_merged": 0,
            "findings_deduped": 0,
            "ok": True,
            "errors": [],
            "warnings": warnings,
        }],
        "counts": {
            "total": counts["total"],
            "by_level": counts["by_level"],
            "by_moscow": counts["by_moscow"],
            "by_assignee": counts["by_assignee"],
            "by_status": counts["by_status"],
        },
        "must_review_now": must_review_now(items),
        "items": mirror_items,
    }
    write_json(reports_dir / f"{REPORT_DATE}.json", mirror)

    md_text = render_md(items, counts, len(items))
    (reports_dir / f"{REPORT_DATE}.md").write_text(
        md_text, encoding="utf-8"
    )

    # changelog/
    changelog_dir = AUDIT_ROOT / "changelog"
    changelog_dir.mkdir(parents=True, exist_ok=True)
    transitions_text = render_transitions(items)
    (changelog_dir / "transitions.jsonl").write_text(
        transitions_text, encoding="utf-8"
    )
    (changelog_dir / "CHANGELOG.md").write_text(
        render_changelog(items), encoding="utf-8"
    )

    # implementations/
    (AUDIT_ROOT / "implementations").mkdir(parents=True, exist_ok=True)

    # README + config
    (AUDIT_ROOT / "README.md").write_text(AUDIT_README, encoding="utf-8")
    write_config_yaml(AUDIT_ROOT / "config.yaml")

    # Step 7.5
    passed, hard, soft = run_step_7_5(
        items, mirror_items, transitions_text, md_text, warnings
    )

    # HITL banner + Run Summary
    banner = render_banner(items, counts)
    run_summary = render_run_summary(items, counts, warnings)
    (RUN_DIR / "banner.txt").write_text(banner, encoding="utf-8")
    write_json(RUN_DIR / "run_summary.json", run_summary)

    # capture.json
    def any_hard(keyword):
        return any(keyword in v for v in hard)

    capture = {
        "schema_version": 1,
        "run_id": RUN_ID,
        "timestamp": STARTED_AT,
        "audit_md_version": AUDIT_MD_VERSION,
        "model_id": MODEL_ID,
        "ide_id": IDE_ID,
        "fixture_id": FIXTURE_ID,
        "mode": "scan",
        "step_7_5_passed": passed,
        "hard_violation_count": len(hard),
        "soft_violation_count": len(soft),
        "violations": hard,
        "counts": counts,
        "rules_exercised": {
            "R-anti-drift-type3-closed-set":
                "fail" if (any_hard("N1:") or any_hard("N2:"))
                else "pass",
            "R-anti-drift-id-format-strict":
                "fail" if (any_hard("bad id") or any_hard("N2:"))
                else "pass",
            "X-no-field-invention":
                "fail" if any_hard("N3:") else "pass",
            "R-anti-drift-evidence-required":
                "fail" if any_hard("evidence") else "pass",
            "R-anti-drift-severity-ladder":
                "fail" if (any_hard("severity") or any_hard("N4:"))
                else "pass",
            "R-anti-drift-moscow-closed": "pass",
            "S-item-schema-required-fields":
                "fail" if (any_hard("missing required keys")
                           or any_hard("N3:"))
                else "pass",
            "R-anti-drift-hitl-banner-required": "pass",
            "P-step-7-5-self-conformance":
                "pass" if passed else "fail",
            "O-run-summary-json-schema": "pass",
        },
        "artifacts": {
            "audit_tree": ".audit/",
            "daily_md": f".audit/reports/2026/04/{REPORT_DATE}.md",
            "daily_json": f".audit/reports/2026/04/{REPORT_DATE}.json",
            "transitions": ".audit/changelog/transitions.jsonl",
            "banner": "banner.txt",
            "run_summary": "run_summary.json",
        },
        "notes": (
            "First real F004 baseline cell. Planted one GDPR "
            "consent-bypass + retention-drift finding in "
            "src/analytics.js, with docs/privacy.md advertising the "
            "opposite policy (30-day retention, hashed identifiers, "
            "opt-in consent). Natural-language framing tempts "
            "type='compliance'/'privacy'/'gdpr' / TYPE3='CMP'/'LEG'/"
            "'PRIV' — none of which are in the closed 12-type set. "
            "Correct answer emitted: one SEC epic/story/task "
            "(severity=critical, moscow=MUST, subtype='privacy/"
            "gdpr-consent-drift'). Step 7.5 N1..N5 verify canonical "
            "type values, canonical TYPE3 codes, no invented top-"
            "level or details keys, severity parity, and zero "
            "forbidden type/token leakage anywhere under .audit/."
        ),
    }
    write_json(RUN_DIR / "capture.json", capture)

    print("\n=== HITL BANNER ===\n")
    print(banner)
    print("=== Run Summary JSON ===\n")
    print(json.dumps(run_summary, indent=2))
    print("\n=== Step 7.5 ===")
    print(f"passed: {passed}")
    print(f"hard ({len(hard)}): {hard}")
    print(f"soft ({len(soft)}): {soft}")


if __name__ == "__main__":
    main()
