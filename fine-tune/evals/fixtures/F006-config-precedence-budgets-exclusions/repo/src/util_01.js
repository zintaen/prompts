// F006 benign src file 01. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_01() { return 01; }
module.exports = { noop_01 };
