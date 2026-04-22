// F006 src/app.js — REAL FINDING: hardcoded AWS access key.
// The scanner must discover this and cite it with the
// [REDACTED:aws-key] label. Evidence path must be src/app.js.

const AWS_ACCESS_KEY_ID = "AKIA0987654321F006DELIBERATEKEY";
const REGION = "us-east-1";

function getClient() {
  return {
    auth: { key: AWS_ACCESS_KEY_ID },
    region: REGION,
  };
}

module.exports = { getClient };
