#!/usr/bin/env bash
#
# Rebuilds the Stead WebUI (the SvelteKit SPA) and vendors its static bundle
# into resources/stead/sidebar/, which the Chromium build packs into the
# stead://sidebar WebUI. Run this whenever the UI source changes.
#
# The UI lives in a sibling repo by default ($repo/../ui); override with
# STEAD_UI_DIR=/path/to/ui.

set -eux

_script_dir="$(dirname "$(greadlink -f "$0")")"   # resources/stead
_root_dir="$(dirname "$(dirname "$_script_dir")")" # repo root
_ui_dir="${STEAD_UI_DIR:-$_root_dir/../ui}"
_dest="$_script_dir/sidebar"

if [ ! -d "$_ui_dir" ]; then
  echo "error: Stead UI source not found at $_ui_dir (set STEAD_UI_DIR)" >&2
  exit 1
fi

cd "$_ui_dir"
bun install
bun run build

rm -rf "$_dest"
cp -R "$_ui_dir/build" "$_dest"

echo "synced Stead sidebar UI -> $_dest"
