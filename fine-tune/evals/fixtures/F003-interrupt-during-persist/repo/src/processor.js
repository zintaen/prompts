// Deliberate PRF finding for F003: O(n^2) loop (identical to F001).
// A real AUDIT.md run should re-match by fingerprint, not re-mint.

function findDuplicates(items) {
  const dups = [];
  for (let i = 0; i < items.length; i++) {
    for (let j = 0; j < items.length; j++) {
      if (i !== j && items[i] === items[j]) {
        dups.push(items[i]);
      }
    }
  }
  return dups;
}

module.exports = { findDuplicates };
