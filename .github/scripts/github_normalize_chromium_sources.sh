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

python3 - "$_src_dir" <<'PY'
import re
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1])


def rewrite(rel, mutator):
    path = src / rel
    if not path.exists():
        return False
    text = path.read_text()
    updated = mutator(text)
    if updated != text:
        path.write_text(updated)
        print(f"normalized stale Stead settings agent source: {rel}")
        return True
    return False


# Older resumed archives can still contain frontend/backend hunks from the
# disabled stead/settings/agent-settings-page.patch. Keeping that half-applied
# page can make chrome://settings request interfaces that the current patch
# series intentionally no longer registers, which kills the WebUI renderer with
# RESULT_CODE_KILLED_BAD_MESSAGE. Strip the whole stale page on resume.
rewrite(
    "chrome/browser/resources/settings/BUILD.gn",
    lambda text: text.replace('    "stead_agent_page/stead_agent_page.ts",\n', ""),
)
rewrite(
    "chrome/browser/resources/settings/route.ts",
    lambda text: re.sub(
        r"(^|\n)  r\.STEAD_AGENT = r\.BASIC\.createSection\(\n"
        r"      '/agent', 'steadAgent',\n"
        r"      loadTimeData\.getString\('steadAgentPageTitle'\)\);\n",
        r"\1",
        text,
    ),
)
rewrite(
    "chrome/browser/resources/settings/router.ts",
    lambda text: text.replace("  STEAD_AGENT: Route;\n", ""),
)
rewrite(
    "chrome/browser/resources/settings/settings_main/settings_main.html",
    lambda text: re.sub(
        r"(^|\n)  <div slot=\"view\" id=\"steadAgent\">\n"
        r"    <template is=\"dom-if\" if=\"\[\[renderPlugin_\(\n"
        r"        routes_\.STEAD_AGENT, lastRoute_, inSearchMode_\)\]\]\">\n"
        r"      <settings-stead-agent-page prefs=\"\{\{prefs\}\}\"\n"
        r"          in-search-mode=\"\[\[inSearchMode_\]\]\">\n"
        r"      </settings-stead-agent-page>\n"
        r"    </template>\n"
        r"  </div>\n",
        r"\1",
        text,
    ),
)
rewrite(
    "chrome/browser/resources/settings/settings_main/settings_main.ts",
    lambda text: text.replace("import '../stead_agent_page/stead_agent_page.js';\n", ""),
)
rewrite(
    "chrome/browser/resources/settings/settings_menu/settings_menu.html",
    lambda text: re.sub(
        r"(^|\n)        <a role=\"menuitem\" id=\"steadAgent\" href=\"/agent\"\n"
        r"            class=\"cr-nav-menu-item\">\n"
        r"          <cr-icon icon=\"settings20:magic\"></cr-icon>\n"
        r"          \$i18n\{steadAgentPageTitle\}\n"
        r"          <cr-ripple></cr-ripple>\n"
        r"        </a>\n",
        r"\1",
        text,
    ),
)
rewrite(
    "chrome/browser/ui/webui/settings/settings_ui.cc",
    lambda text: re.sub(
        r"(^|\n)  html_source->AddString\(\"steadAgentPageTitle\", \"Agent\"\);"
        r".*?\n  html_source->AddString\(\"steadAgentStatusLocal\", \"Local\"\);\n",
        r"\1",
        text.replace(
            '#include "chrome/browser/ui/stead/brain/stead_brain_service_factory.h"\n',
            "",
        ),
        flags=re.S,
    ),
)
rewrite(
    "chrome/browser/ui/webui/settings/settings_ui.cc",
    lambda text: re.sub(
        r"\nvoid SettingsUI::BindInterface\(\n"
        r"    mojo::PendingReceiver<stead::mojom::BrainConsole> pending_receiver\) \{\n"
        r"  stead::SteadBrainServiceFactory::BindBrainConsole\(\n"
        r"      Profile::FromWebUI\(web_ui\(\)\), std::move\(pending_receiver\)\);\n"
        r"\}\n",
        "\n",
        text,
    ),
)
rewrite(
    "chrome/browser/ui/webui/settings/settings_ui.h",
    lambda text: text.replace(
        '#include "chrome/browser/ui/stead/brain/brain_console.mojom.h"\n',
        "",
    ).replace(
        "\n  void BindInterface(\n"
        "      mojo::PendingReceiver<stead::mojom::BrainConsole> pending_receiver);\n",
        "",
    ).replace(
        "  void BindInterface(\n"
        "      mojo::PendingReceiver<stead::mojom::BrainConsole> pending_receiver);\n",
        "",
    ),
)

stale_dir = src / "chrome/browser/resources/settings/stead_agent_page"
if stale_dir.exists():
    shutil.rmtree(stale_dir)
    print("removed stale Stead settings agent page directory")
PY
