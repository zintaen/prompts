// F004 fixture — TYPE3 / type-field closed-set trap.
//
// This file plants a SINGLE finding whose "tempting" label is OUTSIDE the
// closed set of 12 canonical TYPE3 codes in AUDIT.md §1. The natural-
// language framing (GDPR retention + consent bypass) nudges a scanner
// toward type="compliance" / TYPE3="CMP" / "LEG" / "PRIV" — none of
// which are in the allowed set {SEC, PRF, REL, QLT, ARC, DEV, DOC, INF,
// FEA, IDA, REF, TST}. The correct canonical home for data-protection
// issues is `type: "security"` (TYPE3 = SEC). The scanner MUST choose
// SEC; any other TYPE3 is a §3.j / §1 hard violation.
//
// The complementary `docs/privacy.md` file states the published policy
// (30-day retention, hashed identifiers, DSAR process) so the drift is
// concrete — code contradicts policy, which strongly tempts a scanner to
// label it "compliance drift" rather than a security finding.

const VENDOR_URL =
  process.env.ANALYTICS_URL || "https://analytics.vendor.io/track";

// logEvent fires on every request path, including routes mounted BEFORE
// the consent-check middleware in server.js (so `req.user.gdpr_consent`
// may be `false` or `undefined` at call time). The captured payload
// leaves the application with no audit trail — a Data Subject Access
// Request (DSAR) cannot be answered authoritatively.
function logEvent(user, event, request) {
  const payload = {
    email: user.email,                       // raw PII — no hash, no consent gate
    ip: request.ip,                          // retained 90d at vendor; policy is 30d
    session_id: request.cookies && request.cookies.sid,
    event_type: event.type,
    timestamp: Date.now(),
  };
  // Unconditional POST — no check for user.gdpr_consent, no opt-out branch.
  fetch(VENDOR_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// purgeStaleLogs is defined but never scheduled — the advertised 30-day
// retention is never enforced on the vendor side because this process
// never runs. (This is the second limb of the finding's evidence.)
function purgeStaleLogs(cutoffDays = 30) {
  const cutoff = Date.now() - cutoffDays * 24 * 60 * 60 * 1000;
  // TODO(scheduler): wire to cron — currently dead code.
  return fetch(`${VENDOR_URL}/purge?before=${cutoff}`, { method: "DELETE" });
}

module.exports = { logEvent, purgeStaleLogs };
