// F006 benign src file 13. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_13() { return 13; }
module.exports = { noop_13 };
