#!/bin/bash -eux

# Re-applies the CURRENT Stead patch series over an unpacked build tree from a
# previous run's archive, so a resumed build picks up Stead patch fixes without
# restarting from scratch. Two paths:
#   1. Stead-CREATED files (new files) are rebuilt from the patches and copied
#      over the archived tree (overwrite — the archive has the old version).
#   2. Hunks that Stead patches make to SHARED Chromium files are applied with
#      `patch -N` (forward), which no-ops any hunk already present in the
#      archived tree and applies only the genuinely new ones.
#
# ninja then rebuilds exactly what changed. A fix touching a shared file that
# ANOTHER (helium/ungoogled) patch also edits still needs a fresh build, since
# the archived shared file already carries those edits and -N can't reconcile a
# 3-way conflict; but a Stead-only edit to an otherwise-unpatched shared file
# (e.g. a metrics allowlist) resyncs cleanly.

_root_dir="$(dirname "$(greadlink -f "$0")")"
_src_dir="$_root_dir/build/src"

if [ ! -d "$_src_dir" ]; then
  echo "error: unpacked source tree not found at $_src_dir" >&2
  exit 1
fi

# Path prefixes that are wholly Stead-created.
_stead_created_re='^(chrome/browser/ui/stead/|chrome/browser/ui/webui/side_panel/stead_sidebar/|chrome/browser/ui/webui/stead_chat/|chrome/browser/ui/webui/stead_newtab/|chrome/browser/ui/views/side_panel/stead_sidebar/|chrome/browser/resources/stead_sidebar/)'

_tmp="$(mktemp -d)"
trap 'rm -rf "$_tmp"' EXIT
(cd "$_tmp" && git init -q)

# --- Path 1: rebuild Stead-created files and copy them in -------------------
set -- \
  --include='chrome/browser/ui/stead/*' \
  --include='chrome/browser/ui/webui/side_panel/stead_sidebar/*' \
  --include='chrome/browser/ui/webui/stead_chat/*' \
  --include='chrome/browser/ui/webui/stead_newtab/*' \
  --include='chrome/browser/ui/views/side_panel/stead_sidebar/*' \
  --include='chrome/browser/resources/stead_sidebar/*'

grep -E '^stead/' "$_root_dir/patches/series" | while read -r _p; do
  if ! (cd "$_tmp" && git apply "$@" "$_root_dir/patches/$_p"); then
    echo "error: failed to resync stead-created files from $_p" >&2
    exit 1
  fi
done

_count=0
while IFS= read -r _f; do
  mkdir -p "$_src_dir/$(dirname "$_f")"
  cp "$_tmp/$_f" "$_src_dir/$_f"
  _count=$((_count + 1))
done < <(cd "$_tmp" && find chrome -type f 2>/dev/null)
echo "resynced $_count stead-created files"

if [ "$_count" -eq 0 ]; then
  echo "error: resync produced no stead-created files; refusing to continue" >&2
  exit 1
fi

# --- Path 2: forward-apply Stead hunks to shared files ----------------------
# For each Stead patch, keep only the file sections whose target is NOT a
# Stead-created path, then `patch -N` them onto the tree. Already-present hunks
# report "previously applied" and are skipped; new ones apply.
_shared_applied=0
grep -E '^stead/' "$_root_dir/patches/series" | while read -r _p; do
  _pf="$_root_dir/patches/$_p"
  _filtered="$_tmp/shared.patch"
  awk -v re="$_stead_created_re" '
    /^--- a\// { path=$2; sub(/^a\//,"",path); keep=(path !~ re) }
    /^diff --git / { keep=0 }
    { if (keep) print }
  ' "$_pf" > "$_filtered"
  if [ -s "$_filtered" ]; then
    # -N skips already-present hunks (returns non-zero); that's expected for
    # shared files already carried by the archived base, so never fail on it.
    (cd "$_src_dir" && patch -p1 -N --no-backup-if-mismatch < "$_filtered" >/dev/null 2>&1) \
      && echo "applied new shared hunks from $_p" \
      || echo "note: shared hunks in $_p already present or skipped" >&2
  fi
done

"$_root_dir/github_normalize_chromium_sources.sh" "$_src_dir"

echo "stead resync complete"
