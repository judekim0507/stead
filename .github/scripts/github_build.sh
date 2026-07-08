#!/bin/bash -eux

# Simple partitioned (2 of 3) build script for building Stead macOS binaries on GitHub Actions
# Resuming build script for macOS

_target_cpu="${1:-x86_64}"

_root_dir="$(dirname "$(greadlink -f "$0")")"
_src_dir="$_root_dir/build/src"
if [[ -f "$_root_dir/epoch_job_start.txt" ]]; then
  epoch_job_start=$(cat "$_root_dir/epoch_job_start.txt")
  # GitHub's hard time limit is 6 h per job, we want to spare 1 h for steps before and after the build,
  # To get the remaining time for building we subtract 360*60s - 60*60s - (epoch_now - epoch_job_start)
  _remaining_time=$(( 360*60 - 60*60 - $(date +%s) + epoch_job_start ))
fi

cd "$_src_dir"

# A resumed archive can contain a completion marker from an older successful
# chunk. Clear it before ninja so failed resumed chunks cannot package/upload a
# stale app as if this run finished.
rm -f "$_root_dir/build_finished_$_target_cpu.log"

echo $(date +%s) | tee -a "$_root_dir/build_times_$_target_cpu.log"
echo "status=running" >> $GITHUB_OUTPUT

if ! env | grep -q SCCACHE; then
    export SCCACHE_GHA_ENABLED=on
    export SCCACHE_GHA_VERSION="$_target_cpu"
fi

export SCCACHE_WEBDAV_KEY_PREFIX="$_target_cpu"

set +e

timeout -k 7m -s SIGTERM ${_remaining_time:-19680}s ninja -C out/Default chrome chromedriver # 328 m as default $_remaining_time

_error_code="${?}"
if [[ "$_error_code" -eq 124 ]]; then
    exit 0
fi

if [[ "$_error_code" -ne 0 ]]; then
    # Preserve compile progress on failure: mark the status but exit 0 so the
    # archive/upload steps still run; a final do-build step then fails the job.
    # This lets the next dispatch resume from the exact failure point instead
    # of the last successful chunk.
    echo "status=failed" >> $GITHUB_OUTPUT
    exit 0
fi

set -e

echo $(date +%s) | tee "$_root_dir/build_finished_$_target_cpu.log"
echo "status=finished" >> $GITHUB_OUTPUT
