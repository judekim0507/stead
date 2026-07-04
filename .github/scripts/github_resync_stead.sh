#!/bin/bash -eux

# Rebuilds Stead-owned source files from the CURRENT patch series and copies
# them over an unpacked build tree from a previous run's archive. This lets a
# resumed build pick up Stead patch fixes without restarting from scratch.
#
# Only files wholly created by patches/stead may change between iterations;
# shared Chromium files keep the state they had in the archived tree. If a fix
# ever has to touch a shared file, start a fresh (non-resume) build instead.

_root_dir="$(dirname "$(greadlink -f "$0")")"
_src_dir="$_root_dir/build/src"

if [ ! -d "$_src_dir" ]; then
  echo "error: unpacked source tree not found at $_src_dir" >&2
  exit 1
fi

_tmp="$(mktemp -d)"
trap 'rm -rf "$_tmp"' EXIT
(cd "$_tmp" && git init -q)

# Path globs that are wholly Stead-created.
set -- \
  --include='chrome/browser/ui/stead/*' \
  --include='chrome/browser/ui/webui/side_panel/stead_sidebar/*' \
  --include='chrome/browser/ui/webui/stead_chat/*' \
  --include='chrome/browser/ui/webui/stead_newtab/*' \
  --include='chrome/browser/ui/views/side_panel/stead_sidebar/*' \
  --include='chrome/browser/resources/stead_sidebar/*'

grep -E '^stead/' "$_root_dir/patches/series" | while read -r _p; do
  # Patches whose files are all excluded by the pathspec apply as a no-op.
  (cd "$_tmp" && git apply "$@" "$_root_dir/patches/$_p") \
    || echo "warn: no stead-owned files in $_p (or apply failed)" >&2
done

_count=0
while IFS= read -r _f; do
  mkdir -p "$_src_dir/$(dirname "$_f")"
  cp "$_tmp/$_f" "$_src_dir/$_f"
  _count=$((_count + 1))
done < <(cd "$_tmp" && find chrome -type f 2>/dev/null)

echo "resynced $_count stead-owned files into $_src_dir"
if [ "$_count" -eq 0 ]; then
  echo "error: resync produced no files; refusing to continue" >&2
  exit 1
fi
