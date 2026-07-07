#!/bin/bash -eux
# Normalize known Chromium source drift after Stead patch application/resume.

if command -v greadlink >/dev/null 2>&1; then
  _script_path="$(greadlink -f "$0")"
else
  _script_dir="$(cd "$(dirname "$0")" && pwd -P)"
  _script_path="$_script_dir/$(basename "$0")"
fi
_root_dir="$(dirname "$_script_path")"
_src_dir="${1:-$_root_dir/build/src}"

if [ ! -d "$_src_dir" ]; then
  echo "error: source tree not found at $_src_dir" >&2
  exit 1
fi

_binder="$_src_dir/chrome/browser/chrome_browser_interface_binders_webui_parts_desktop.cc"
if [ -f "$_binder" ]; then
  python3 - "$_binder" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()
original = text

# Older archives may contain partial hunks from the disabled
# stead/settings/agent-settings-page.patch. Those hunks are intentionally no
# longer in patches/series, but resumed archives can still carry them.
text = text.replace(
    "                                         SteadNewTabUI,\n"
    "                                         settings::SettingsUI>(map);",
    "                                         SteadNewTabUI>(map);",
)
text = text.replace(
    "      .Add<help_bubble::mojom::HelpBubbleHandlerFactory>()\n"
    "      .Add<stead::mojom::BrainConsole>();",
    "      .Add<help_bubble::mojom::HelpBubbleHandlerFactory>();",
)
text = re.sub(
    r"\nvoid RegisterWebUIBrowserInterfaceBindersForSteadSettings\([^{}]*\)\s*\{"
    r".*?\n\}\n",
    "\n",
    text,
    flags=re.S,
)

# The automatic chained build jobs resume from archived source trees without
# running github_resync_stead.sh. If a prior archive has the trusted WebUI binder
# function missing its closing brace, the compile fails near the end of the
# build when the untrusted binder function starts. Repair only that bounded
# function chunk.
trusted = "void PopulateChromeWebUIFrameInterfaceBrokersTrustedPartsDesktop("
untrusted = "\nvoid PopulateChromeWebUIFrameInterfaceBrokersUntrustedPartsDesktop("
trusted_at = text.find(trusted)
untrusted_at = text.find(untrusted, trusted_at)
if trusted_at != -1 and untrusted_at != -1:
    chunk = text[trusted_at:untrusted_at]
    missing_closes = chunk.count("{") - chunk.count("}")
    if missing_closes > 0:
        text = text[:untrusted_at] + ("}\n" * missing_closes) + text[untrusted_at:]

if text != original:
    path.write_text(text)
    print("normalized Stead WebUI binder source")
PY
fi
