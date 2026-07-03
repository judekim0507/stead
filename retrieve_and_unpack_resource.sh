#!/usr/bin/env bash

# Script to retrieve and unpack resources to build Chromium macOS

set -eux

_root_dir="$(dirname "$(greadlink -f "$0")")"
_download_cache="$_root_dir/build/download_cache"
_src_dir="$_root_dir/build/src"
_main_repo="$_root_dir/helium-chromium"

# Clone to get the Chromium Source
clone=true
retrieve_generic=false
retrieve_toolchain=false

while getopts 'dgt' OPTION; do
  case "$OPTION" in
    d)
        clone=false
        ;;
    g)
        retrieve_generic=true
        ;;
    t)
        retrieve_toolchain=true
        ;;
    ?)
        echo "Usage: $0 [-d] [-g] [-p]"
        echo "  -d: Use download instead of git clone to get Chromium Source"
        echo "  -g: Retrieve and unpack Chromium Source and general resources"
        echo "  -t: Retrieve and unpack Chromium toolchain"
        exit 1
        ;;
    esac
done

shift "$(($OPTIND -1))"

_target_cpu=${1:-arm64}

# Retry a command with backoff. The Chromium git host (googlesource) and the
# download mirrors intermittently return HTTP 5xx on large fetches; a bare
# failure there kills a multi-hour build for no code reason.
_retry() {
    local _attempts="$1"; shift
    local _n=1
    until "$@"; do
        if [[ $_n -ge $_attempts ]]; then
            echo "retry: command failed after $_n attempts: $*" >&2
            return 1
        fi
        echo "retry: attempt $_n failed, retrying in $((_n * 20))s: $*" >&2
        sleep "$((_n * 20))"
        _n=$((_n + 1))
    done
}

# A partial checkout left by a failed clone would make the next attempt refuse
# to clone into a non-empty dir, so wipe it first.
_clone_chromium() {
    rm -rf "$_src_dir"
    python3 "$_main_repo/utils/clone.py" "$@" -o "$_src_dir"
}

if $retrieve_generic; then
    if $clone; then
        if [[ $_target_cpu == "arm64" ]]; then
            # For arm64 (Apple Silicon)
            _retry 4 _clone_chromium -p mac-arm
        else
            # For amd64 (Intel)
            _retry 4 _clone_chromium -p mac
        fi
    else
        _retry 4 python3 "$_main_repo/utils/downloads.py" retrieve -i "$_main_repo/downloads.ini" -c "$_download_cache"
        python3 "$_main_repo/utils/downloads.py" unpack -i "$_main_repo/downloads.ini" -c "$_download_cache" "$_src_dir"
    fi

    # Retrieve and unpack general resources
    _retry 4 python3 "$_main_repo/utils/downloads.py" retrieve -i "$_root_dir/downloads.ini" -c "$_download_cache"
    _retry 4 python3 "$_main_repo/utils/downloads.py" retrieve -i "$_main_repo/deps.ini" -c "$_download_cache"
    python3 "$_main_repo/utils/downloads.py" unpack -i "$_root_dir/downloads.ini" -c "$_download_cache" "$_src_dir"
    python3 "$_main_repo/utils/downloads.py" unpack -i "$_main_repo/deps.ini" -c "$_download_cache" "$_src_dir"
fi

if $retrieve_toolchain; then
  pushd "$_src_dir"
    "$_src_dir/tools/rust/update_rust.py"
    for pkg in clang objdump clang-tidy libclang; do
      "$_src_dir/tools/clang/scripts/update.py" --package $pkg;
    done
    "$_src_dir/third_party/node/update_node_binaries"

    NODE="$_src_dir/third_party/node"
    mkdir -p "$NODE/mac_arm64"
    mv "$NODE/mac/node-darwin-arm64" "$NODE/mac_arm64/"
  popd
fi
