// F006 benign src file 02. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_02() { return 02; }
module.exports = { noop_02 };
