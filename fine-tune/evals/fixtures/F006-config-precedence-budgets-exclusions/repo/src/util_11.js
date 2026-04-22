// F006 benign src file 11. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_11() { return 11; }
module.exports = { noop_11 };
