import subprocess
import tempfile
import unittest
from pathlib import Path


class GithubNormalizeChromiumSourcesTest(unittest.TestCase):
    def test_strips_stale_settings_agent_page_from_resumed_tree(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = repo_root / ".github/scripts/github_normalize_chromium_sources.sh"

        with tempfile.TemporaryDirectory() as tmpdirname:
            src = Path(tmpdirname)
            binder = src / "chrome/browser/chrome_browser_interface_binders_webui_parts_desktop.cc"
            binder.parent.mkdir(parents=True, exist_ok=True)
            binder.write_text(
                "void PopulateChromeWebUIFrameBindersPartsDesktop() {\n"
                "  RegisterWebUIControllerInterfaceBinder<stead::mojom::BrainConsole,\n"
                "                                         SteadSidebarUI, SteadChatUI,\n"
                "                                         SteadNewTabUI,\n"
                "                                         settings::SettingsUI>(map);\n"
                "  RegisterWebUIControllerInterfaceBinder<stead::mojom::ControlConsole,\n"
                "                                         SteadSidebarUI, SteadChatUI,\n"
                "                                         SteadNewTabUI,\n"
                "                                         settings::SettingsUI>(map);\n"
                "  // Mention the customize factory outside the real binder; the\n"
                "  // normalizer must still restore the settings binder below.\n"
                "  // customize_color_scheme_mode::mojom::CustomizeColorSchemeModeHandlerFactory\n"
                "  RegisterWebUIControllerInterfaceBinder<\n"
                "      theme_color_picker::mojom::ThemeColorPickerHandlerFactory,\n"
                "      CustomizeChromeUI\n"
                "#if !BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      ProfileCustomizationUI\n"
                "#endif  // !BUILDFLAG(IS_CHROMEOS)\n"
                "      >(map);\n"
                "  RegisterWebUIControllerInterfaceBinder<\n"
                "      help_bubble::mojom::HelpBubbleHandlerFactory, UserEducationInternalsUI,\n"
                "      ReadingListUI, NewTabPageUI, CustomizeChromeUI, PasswordManagerUI,\n"
                "      HistoryUI, lens::LensOverlayUntrustedUI, lens::LensSidePanelUntrustedUI,\n"
                "      ReadAnythingUntrustedUI\n"
                "#if !BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      ProfilePickerUI\n"
                "#endif  //! BUILDFLAG(IS_CHROMEOS)\n"
                "      >(map);\n"
                "  RegisterWebUIControllerInterfaceBinder<\n"
                "      browser_command::mojom::CommandHandlerFactory,\n"
                "      settings::SettingsUI>(map);\n"
                "}\n"
                "void PopulateChromeWebUIFrameInterfaceBrokersTrustedPartsDesktop() {\n"
                "  registry.ForWebUI<settings::SettingsUI>()\n"
                "      .Add<customize_color_scheme_mode::mojom::CustomizeColorSchemeModeHandlerFactory>()\n"
                "      .Add<help_bubble::mojom::HelpBubbleHandlerFactory>()\n"
                "      .Add<stead::mojom::BrainConsole>()\n"
                "      .Add<stead::mojom::ControlConsole>();\n"
                "}\n"
                "void PopulateChromeWebUIFrameInterfaceBrokersUntrustedPartsDesktop() {\n"
                "}\n",
                encoding="utf-8",
            )

            files = {
                "chrome/browser/resources/settings/BUILD.gn":
                    '    "settings_ui/settings_ui.ts",\n'
                    '    "stead_agent_page/stead_agent_page.ts",\n'
                    '    "simple_confirmation_dialog.ts",\n',
                "chrome/browser/resources/settings/route.ts":
                    "  r.STEAD_AGENT = r.BASIC.createSection(\n"
                    "      '/agent', 'steadAgent',\n"
                    "      loadTimeData.getString('steadAgentPageTitle'));\n"
                    "  r.AI = r.BASIC.createSection('/ai', 'ai', 'AI');\n",
                "chrome/browser/resources/settings/router.ts":
                    "  SYNC_ADVANCED: Route;\n"
                    "  STEAD_AGENT: Route;\n"
                    "  SYSTEM: Route;\n",
                "chrome/browser/resources/settings/settings_main/settings_main.html":
                    "  <div slot=\"view\" id=\"steadAgent\">\n"
                    "    <template is=\"dom-if\" if=\"[[renderPlugin_(\n"
                    "        routes_.STEAD_AGENT, lastRoute_, inSearchMode_)]]\">\n"
                    "      <settings-stead-agent-page prefs=\"{{prefs}}\"\n"
                    "          in-search-mode=\"[[inSearchMode_]]\">\n"
                    "      </settings-stead-agent-page>\n"
                    "    </template>\n"
                    "  </div>\n"
                    "  <template is=\"dom-if\"></template>\n",
                "chrome/browser/resources/settings/settings_main/settings_main.ts":
                    "import '../stead_agent_page/stead_agent_page.js';\n"
                    "import '../default_browser_page/default_browser_page.js';\n",
                "chrome/browser/resources/settings/settings_menu/settings_menu.html":
                    "        <a role=\"menuitem\" id=\"steadAgent\" href=\"/agent\"\n"
                    "            class=\"cr-nav-menu-item\">\n"
                    "          <cr-icon icon=\"settings20:magic\"></cr-icon>\n"
                    "          $i18n{steadAgentPageTitle}\n"
                    "          <cr-ripple></cr-ripple>\n"
                    "        </a>\n"
                    "        <a role=\"menuitem\" id=\"steadAiLink\"\n"
                    "            href=\"chrome://chat/ai-settings\" class=\"cr-nav-menu-item\">\n"
                    "          <cr-icon icon=\"settings20:magic\"></cr-icon>\n"
                    "          Stead AI\n"
                    "          <cr-ripple></cr-ripple>\n"
                    "        </a>\n"
                    "        <a role=\"menuitem\" id=\"autofill\"></a>\n",
                "chrome/browser/resources/settings/settings_menu/settings_menu.ts":
                    "const selector = 'a:not(#extensionsLink):not(#steadAiLink)';\n",
                "chrome/browser/ui/webui/settings/settings_ui.cc":
                    '#include "chrome/browser/ui/stead/brain/stead_brain_service_factory.h"\n'
                    "  html_source->AddString(\"steadAgentPageTitle\", \"Agent\");\n"
                    "  html_source->AddString(\"steadAgentStatusLocal\", \"Local\");\n"
                    "  AddSettingsPageUIHandler(std::make_unique<AppearanceHandler>(web_ui));\n"
                    "void SettingsUI::BindInterface(\n"
                    "    mojo::PendingReceiver<stead::mojom::BrainConsole> pending_receiver) {\n"
                    "  stead::SteadBrainServiceFactory::BindBrainConsole(\n"
                    "      Profile::FromWebUI(web_ui()), std::move(pending_receiver));\n"
                    "}\n",
                "chrome/browser/ui/webui/settings/settings_ui.h":
                    '#include "chrome/browser/ui/stead/brain/brain_console.mojom.h"\n'
                    "  void BindInterface(\n"
                    "      mojo::PendingReceiver<stead::mojom::BrainConsole> pending_receiver);\n",
            }
            for rel, content in files.items():
                path = src / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            stale_dir = src / "chrome/browser/resources/settings/stead_agent_page"
            stale_dir.mkdir(parents=True)
            (stale_dir / "stead_agent_page.ts").write_text("", encoding="utf-8")

            subprocess.run(["bash", str(script), str(src)], check=True)

            binder_text = binder.read_text(encoding="utf-8")
            self.assertIn(
                "customize_color_scheme_mode::mojom::CustomizeColorSchemeModeHandlerFactory,\n"
                "      CustomizeChromeUI,\n"
                "      settings::SettingsUI>(map);",
                binder_text,
            )
            self.assertIn(
                "theme_color_picker::mojom::ThemeColorPickerHandlerFactory,\n"
                "      CustomizeChromeUI\n"
                "#if !BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      ProfileCustomizationUI\n"
                "#endif  // !BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      settings::SettingsUI>(map);",
                binder_text,
            )
            self.assertIn(
                "help_bubble::mojom::HelpBubbleHandlerFactory, UserEducationInternalsUI,\n"
                "      ReadingListUI, NewTabPageUI, CustomizeChromeUI, PasswordManagerUI,\n"
                "      HistoryUI, lens::LensOverlayUntrustedUI, lens::LensSidePanelUntrustedUI,\n"
                "      ReadAnythingUntrustedUI\n"
                "#if !BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      ProfilePickerUI\n"
                "#endif  //! BUILDFLAG(IS_CHROMEOS)\n"
                "      ,\n"
                "      settings::SettingsUI>(map);",
                binder_text,
            )
            self.assertNotIn(
                "SteadNewTabUI,\n"
                "                                         settings::SettingsUI>(map);",
                binder_text,
            )
            self.assertNotRegex(
                binder_text,
                r"RegisterWebUIControllerInterfaceBinder<stead::mojom::BrainConsole,"
                r".*settings::SettingsUI>\(map\);",
            )
            self.assertNotRegex(
                binder_text,
                r"RegisterWebUIControllerInterfaceBinder<stead::mojom::ControlConsole,"
                r".*settings::SettingsUI>\(map\);",
            )
            self.assertNotIn(".Add<stead::mojom::BrainConsole>();", binder_text)
            self.assertNotIn(".Add<stead::mojom::ControlConsole>();", binder_text)

            for rel in files:
                self.assertNotIn("steadAgent", (src / rel).read_text(encoding="utf-8"))
                self.assertNotIn("BrainConsole", (src / rel).read_text(encoding="utf-8"))
            menu_text = (src / "chrome/browser/resources/settings/settings_menu/settings_menu.html").read_text(
                encoding="utf-8"
            )
            self.assertIn('id="steadAiLink"', menu_text)
            self.assertIn('href="chrome://chat/ai-settings"', menu_text)
            self.assertFalse(stale_dir.exists())


if __name__ == "__main__":
    unittest.main()
