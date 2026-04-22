// F006 benign src file 10. No findings. Purely to make the security
// scanner's in-scope file list exceed max_files_per_task=10.
function noop_10() { return 10; }
module.exports = { noop_10 };
