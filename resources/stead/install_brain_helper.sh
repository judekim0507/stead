#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 /path/to/Stead.app [arm64|x64|x86_64]" >&2
  exit 2
fi

_app_dir="$1"
_arch="${2:-$(uname -m)}"
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_root_dir="$(cd "$_script_dir/../.." && pwd)"
_brain_dir="$(cd "$_root_dir/../stead-brain" && pwd)"

case "$_arch" in
  arm64|aarch64)
    _cargo_target="aarch64-apple-darwin"
    ;;
  x64|x86_64)
    _cargo_target="x86_64-apple-darwin"
    ;;
  *)
    echo "unsupported Stead brain helper architecture: $_arch" >&2
    exit 2
    ;;
esac

if [ ! -f "$_brain_dir/Cargo.toml" ]; then
  echo "Stead brain workspace not found at $_brain_dir" >&2
  exit 1
fi

if [ ! -d "$_app_dir/Contents/MacOS" ]; then
  echo "app bundle MacOS directory not found: $_app_dir/Contents/MacOS" >&2
  exit 1
fi

if [ -n "${STEAD_BRAIN_HELPER_PATH:-}" ]; then
  _helper="$STEAD_BRAIN_HELPER_PATH"
else
  cargo build \
    --manifest-path "$_brain_dir/Cargo.toml" \
    --release \
    --package stead-brain \
    --target "$_cargo_target"
  _helper="$_brain_dir/target/$_cargo_target/release/stead-brain"
fi

if [ ! -x "$_helper" ]; then
  echo "stead-brain helper was not built or is not executable: $_helper" >&2
  exit 1
fi

install -m 0755 "$_helper" "$_app_dir/Contents/MacOS/stead-brain"
echo "installed stead-brain helper: $_app_dir/Contents/MacOS/stead-brain"
