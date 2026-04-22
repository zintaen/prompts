// Deliberate QLT finding for F002: unused import + dead code.
// A real AUDIT.md run should flag this under AUD-QLT-NNNN with
// severity medium and moscow=COULD.

const _ = require("lodash");
const crypto = require("crypto"); // unused

function isValidEmail(value) {
  return typeof value === "string" && value.indexOf("@") > 0;
}

// Dead code: never referenced, never exported.
function legacyNormalizeIgnored(x) {
  return String(x).trim().toLowerCase();
}

module.exports = { isValidEmail };
