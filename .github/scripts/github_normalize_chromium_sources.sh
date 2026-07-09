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
text = re.sub(
    r"(RegisterWebUIControllerInterfaceBinder<stead::mojom::[A-Za-z0-9_]+,\s*"
    r"SteadSidebarUI,\s*SteadChatUI,\s*SteadNewTabUI),\s*"
    r"settings::SettingsUI(>\(map\);)",
    r"\1\2",
    text,
    flags=re.S,
)

def strip_stale_settings_stead_interfaces(match):
    return re.sub(
        r"\n\s*\.Add<stead::mojom::[A-Za-z0-9_]+>\(\)",
        "",
        match.group(0),
    )

text = re.sub(
    r"registry\.ForWebUI<settings::SettingsUI>\(\)"
    r"(?:\n\s*\.Add<[^;]+>\(\))*;",
    strip_stale_settings_stead_interfaces,
    text,
    flags=re.S,
)
text = re.sub(
    r"\nvoid RegisterWebUIBrowserInterfaceBindersForSteadSettings\([^{}]*\)\s*\{"
    r".*?\n\}\n",
    "\n",
    text,
    flags=re.S,
)

# Some resumed source archives were captured after a stale settings rewrite
# removed Chromium's stock settings binder while leaving the matching broker
# entry advertised. The first settings page load then requests
# CustomizeColorSchemeModeHandlerFactory and the renderer is killed for a bad
# IPC message. Restore the stock binder if the broker entry is present.
customize_broker_re = (
    r"\.Add<customize_color_scheme_mode::mojom::\s*"
    r"CustomizeColorSchemeModeHandlerFactory>\(\)"
)
customize_any_binder_re = (
    r"RegisterWebUIControllerInterfaceBinder<\s*"
    r"customize_color_scheme_mode::mojom::"
    r"CustomizeColorSchemeModeHandlerFactory"
    r"(?:(?!>\(map\);).)*>\(map\);"
)
customize_binder_re = (
    r"RegisterWebUIControllerInterfaceBinder<\s*"
    r"customize_color_scheme_mode::mojom::"
    r"CustomizeColorSchemeModeHandlerFactory"
    r"(?:(?!>\(map\);).)*settings::SettingsUI"
    r"(?:(?!>\(map\);).)*>\(map\);"
)
customize_snippet = (
    "  RegisterWebUIControllerInterfaceBinder<\n"
    "      customize_color_scheme_mode::mojom::CustomizeColorSchemeModeHandlerFactory,\n"
    "      CustomizeChromeUI,\n"
    "      settings::SettingsUI>(map);\n\n"
)
browser_command_binder = (
    "  RegisterWebUIControllerInterfaceBinder<\n"
    "      browser_command::mojom::CommandHandlerFactory,"
)
if (
    re.search(customize_broker_re, text, flags=re.S)
    and not re.search(customize_any_binder_re, text, flags=re.S)
    and browser_command_binder in text
):
    text = text.replace(browser_command_binder, customize_snippet + browser_command_binder, 1)

def ensure_settings_ui_binder(factory_re, label):
    global text
    pattern = re.compile(
        r"(RegisterWebUIControllerInterfaceBinder<\s*"
        + factory_re
        + r"\s*,)(.*?)(>\(map\);)",
        flags=re.S,
    )

    def replace(match):
        block = match.group(0)
        if "settings::SettingsUI" in block:
            return block
        return match.group(1) + match.group(2) + ",\n      settings::SettingsUI" + match.group(3)

    updated, count = pattern.subn(replace, text, count=1)
    if count == 0:
        raise SystemExit(f"error: settings {label} binder registration is missing")
    text = updated

ensure_settings_ui_binder(
    r"customize_color_scheme_mode::mojom::\s*CustomizeColorSchemeModeHandlerFactory",
    "color-scheme",
)
ensure_settings_ui_binder(
    r"theme_color_picker::mojom::ThemeColorPickerHandlerFactory",
    "theme-color-picker",
)
ensure_settings_ui_binder(
    r"help_bubble::mojom::HelpBubbleHandlerFactory",
    "help-bubble",
)

if re.search(
    r"RegisterWebUIControllerInterfaceBinder<stead::mojom::[A-Za-z0-9_]+,"
    r"[^;]*settings::SettingsUI>\(map\);",
    text,
    flags=re.S,
):
    raise SystemExit("error: stale Stead SettingsUI WebUI binder remains")
if re.search(
    r"registry\.ForWebUI<settings::SettingsUI>\(\)"
    r"(?:(?!;).)*\.Add<stead::mojom::[A-Za-z0-9_]+>\(\)",
    text,
    flags=re.S,
):
    raise SystemExit("error: stale Stead SettingsUI broker entry remains")
if re.search(customize_broker_re, text, flags=re.S) and not re.search(
    customize_binder_re, text, flags=re.S
):
    raise SystemExit("error: settings color-scheme binder is missing")

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

_pinned_toolbar_button="$_src_dir/chrome/browser/ui/views/toolbar/pinned_action_toolbar_button.cc"
if [ -f "$_pinned_toolbar_button" ]; then
  python3 - "$_pinned_toolbar_button" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()
original = text

# Older resumed archives can still contain the removed Ask Stead toolbar
# override that navigates to the full-page chat WebUI. The current Ask Stead
# button must keep Chromium's native side-panel action path instead.
stale_block = """\
  if (action_id.value() == kActionSidePanelShowReadingList) {
    action_view_->browser()->OpenGURL(
        GURL("chrome://chat/ai-chat"),
        WindowOpenDisposition::NEW_FOREGROUND_TAB);
    return;
  }

"""
text = text.replace(stale_block, "")
if text != original:
    text = text.replace('#include "chrome/browser/ui/browser.h"\n', "")
    text = text.replace('#include "ui/base/window_open_disposition.h"\n', "")
    text = text.replace('#include "url/gurl.h"\n', "")

if 'GURL("chrome://chat/ai-chat")' in text:
    raise SystemExit("error: stale Ask Stead full-page toolbar override remains")

if text != original:
    path.write_text(text)
    print("normalized stale Ask Stead toolbar full-page override")
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
