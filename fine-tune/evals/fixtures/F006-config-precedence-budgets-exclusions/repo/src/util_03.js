// F006 benign src file 03. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_03() { return 03; }
module.exports = { noop_03 };
