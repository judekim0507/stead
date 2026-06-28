#!/usr/bin/env bash
#
# Copies the vendored Stead sidebar WebUI bundle into the Chromium source tree
# at chrome/browser/resources/stead_sidebar/, where the BUILD.gn added by
# patches/stead packs it into stead_sidebar_resources.pak.
#
# Usage: install_sidebar_to_tree.sh <chromium_src_dir>

set -eux

_script_dir="$(dirname "$(greadlink -f "$0")")"   # resources/stead
_src_dir="${1:?usage: install_sidebar_to_tree.sh <chromium_src_dir>}"
_bundle="$_script_dir/sidebar"
_dest="$_src_dir/chrome/browser/resources/stead_sidebar"

if [ ! -f "$_bundle/index.html" ]; then
  echo "error: missing sidebar bundle at $_bundle (run sync_sidebar_ui.sh first)" >&2
  exit 1
fi

mkdir -p "$_dest"
# Copy the built assets in alongside the patched-in BUILD.gn (don't clobber it).
cp -R "$_bundle/." "$_dest/"

# Regenerate the GRIT manifest for the (hash-named) bundle files.
python3 "$_script_dir/gen_sidebar_grd.py" "$_dest" "$_dest/stead_sidebar_resources.grd"

echo "installed Stead sidebar bundle -> $_dest"
