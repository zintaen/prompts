// F006 benign src file 12. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_12() { return 12; }
module.exports = { noop_12 };
