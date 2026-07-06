#!/bin/bash -eux
# Simple script for packing Stead macOS build artifacts on GitHub Actions

_target_cpu="${1:-x86_64}"

_root_dir="$(dirname "$(greadlink -f "$0")")"
_src_dir="$_root_dir/build/src"

gsync --file-system "$_src_dir"

# Needs to be compressed to stay below GitHub's upload limit 2 GB (?!) 2020-11-24; used to be  5-8GB (?)
tar -C build -c -f - src | zstd -vv -11 -T0 -o build_src.tar.zst

sha256sum ./build_src.tar.zst | tee ./sums.txt

mkdir -p upload_part_build
mv -vn ./*.zst ./sums.txt upload_part_build/ || true
cp -va ./*.log upload_part_build/

ls -kahl upload_part_build/
du -hs upload_part_build/

_packaging_status="skipped"

# Package after the resumable archive is ready. If packaging fails, the action
# still uploads upload_part_build/ so the completed compile can be resumed.
if [[ -f "$_root_dir/build_finished_$_target_cpu.log" ]] ; then
  if bash "$_root_dir/github_package_finished_build.sh" "$_target_cpu"; then
    _packaging_status="finished"
  else
    _packaging_status="failed"
    echo "artifact packaging failed after build archive was prepared" >&2
  fi
fi

echo "packaging_status=$_packaging_status" >> "$GITHUB_OUTPUT"

mkdir upload_logs
mv -vn ./*.log upload_logs/

ls -kahl upload_logs/
du -hs upload_logs/

echo "ready for upload action"
