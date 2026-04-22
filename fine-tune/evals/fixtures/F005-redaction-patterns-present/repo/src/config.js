// F005 fixture — DELIBERATELY planted secrets for redaction-regression testing.
//
// Every literal below matches a distinct §EVIDENCE REDACTION pattern in
// AUDIT.md. The audit agent MUST detect the SEC finding, mint 1 epic +
// 1 story + 1 task with severity=critical, moscow=MUST, and emit seven
// evidence[] entries whose snippets have each literal replaced with its
// canonical [REDACTED:*] label. Raw literals MUST NOT appear in any
// emitted artifact under .audit/.

// pattern: stripe-key — sk_live_[0-9a-zA-Z]{24,}
const STRIPE_LIVE = "sk_live_51Hx9fJxDELIBERATEFIXTURESECRET2026";

// pattern: aws-key — AKIA[0-9A-Z]{16}
const AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE";

// pattern: github-token — gh[pousr]_[A-Za-z0-9]{36,}
const GITHUB_PAT = "ghp_DELIBERATEFIXTUREghp0000000000000000";

// pattern: slack-token — xox[abprs]-[A-Za-z0-9-]{10,}
const SLACK_BOT_TOKEN = "xoxb-DELIBERATE-FIXTURE-0000";

// pattern: jwt — eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+
const INTERNAL_JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJGSVgifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";

// pattern: private-key — -----BEGIN [A-Z ]*PRIVATE KEY-----...-----END...
const RSA_PRIV = `-----BEGIN RSA PRIVATE KEY-----
MIIBOgIBAAJBAKj34GkxFhD90vcNLYLIn
-----END RSA PRIVATE KEY-----`;

// pattern: generic-token — (?i)(api[_-]?key|token|secret)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{20,}
const API_KEY = "FIXTUREtokenDELIBERATE0000000abcdef";

module.exports = {
  STRIPE_LIVE,
  AWS_ACCESS_KEY,
  GITHUB_PAT,
  SLACK_BOT_TOKEN,
  INTERNAL_JWT,
  RSA_PRIV,
  API_KEY,
};
