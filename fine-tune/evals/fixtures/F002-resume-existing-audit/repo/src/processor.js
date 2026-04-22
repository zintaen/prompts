// Deliberate PRF finding for F001: O(n^2) loop on a list that may be large.
// A real AUDIT.md run should flag this under AUD-PRF-NNNN with
// severity at least medium; hot-path threshold per AUDIT.md definitions.

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
