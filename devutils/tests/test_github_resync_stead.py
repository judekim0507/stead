import subprocess
import tempfile
import unittest
from pathlib import Path


class GithubResyncSteadTest(unittest.TestCase):
    def test_stead_patch_series_parses_for_created_file_resync(self):
        repo_root = Path(__file__).resolve().parents[2]
        include_args = [
            "--include=chrome/browser/ui/stead/*",
            "--include=chrome/browser/ui/webui/side_panel/stead_sidebar/*",
            "--include=chrome/browser/ui/webui/stead_chat/*",
            "--include=chrome/browser/ui/webui/stead_newtab/*",
            "--include=chrome/browser/ui/views/side_panel/stead_sidebar/*",
            "--include=chrome/browser/resources/stead_sidebar/*",
        ]

        with tempfile.TemporaryDirectory() as tmpdirname:
            subprocess.run(["git", "init", "-q"], cwd=tmpdirname, check=True)
            series = repo_root / "patches" / "series"
            for rel in series.read_text(encoding="utf-8").splitlines():
                if not rel.startswith("stead/"):
                    continue
                subprocess.run(
                    ["git", "apply", *include_args, str(repo_root / "patches" / rel)],
                    cwd=tmpdirname,
                    check=True,
                )

            generated_builds = [
                "chrome/browser/resources/stead_sidebar/BUILD.gn",
                "chrome/browser/ui/stead/agent_control/BUILD.gn",
                "chrome/browser/ui/stead/brain/BUILD.gn",
                "chrome/browser/ui/stead/brain/stead_brain_service.cc",
            ]
            for rel in generated_builds:
                text = (Path(tmpdirname) / rel).read_text(encoding="utf-8")
                self.assertEqual(text.count("{"), text.count("}"), rel)

    def test_normalize_removes_stale_ask_stead_full_page_toolbar_override(self):
        repo_root = Path(__file__).resolve().parents[2]
        normalizer = repo_root / ".github/scripts/github_normalize_chromium_sources.sh"

        with tempfile.TemporaryDirectory() as tmpdirname:
            source = Path(tmpdirname)
            toolbar = (
                source
                / "chrome/browser/ui/views/toolbar/pinned_action_toolbar_button.cc"
            )
            toolbar.parent.mkdir(parents=True)
            toolbar.write_text(
                '#include "chrome/browser/ui/browser.h"\n'
                '#include "ui/base/window_open_disposition.h"\n'
                '#include "url/gurl.h"\n'
                "\n"
                "void Invoke() {\n"
                "  if (action_id.value() == kActionSidePanelShowReadingList) {\n"
                "    action_view_->browser()->OpenGURL(\n"
                '        GURL("chrome://chat/ai-chat"),\n'
                "        WindowOpenDisposition::NEW_FOREGROUND_TAB);\n"
                "    return;\n"
                "  }\n"
                "\n"
                "  action_item->InvokeAction(context);\n"
                "}\n",
                encoding="utf-8",
            )

            subprocess.run([str(normalizer), str(source)], check=True)

            text = toolbar.read_text(encoding="utf-8")
            self.assertNotIn('GURL("chrome://chat/ai-chat")', text)
            self.assertNotIn('chrome/browser/ui/browser.h', text)
            self.assertNotIn('ui/base/window_open_disposition.h', text)
            self.assertNotIn('url/gurl.h', text)
            self.assertIn("action_item->InvokeAction(context);", text)

    def test_normalize_upgrades_resumed_ask_stead_coordinator(self):
        repo_root = Path(__file__).resolve().parents[2]
        normalizer = repo_root / ".github/scripts/github_normalize_chromium_sources.sh"

        with tempfile.TemporaryDirectory() as tmpdirname:
            source = Path(tmpdirname)
            coordinator = (
                source
                / "chrome/browser/ui/views/side_panel/reading_list/reading_list_side_panel_coordinator.cc"
            )
            coordinator.parent.mkdir(parents=True)
            coordinator.write_text(
                '#include "base/check_deref.h"\n'
                '#include "chrome/browser/ui/browser_window/public/browser_window_interface.h"\n'
                '#include "chrome/browser/ui/side_panel/side_panel_entry.h"\n'
                '#include "chrome/browser/ui/side_panel/side_panel_registry.h"\n'
                '#include "chrome/browser/sessions/session_tab_helper.h"\n'
                "\n"
                "std::unique_ptr<views::View> CreateReadingListWebView(\n"
                "    Profile* profile,\n"
                "    TabStripModel* tab_strip_model,\n"
                "    SidePanelEntryScope& scope) {\n"
                "  return std::make_unique<SteadSidebarSidePanelWebView>(\n"
                "      profile, scope, base::RepeatingClosure());\n"
                "}\n"
                "\n"
                "void ReadingListSidePanelCoordinator::CreateAndRegisterEntry(\n"
                "    SidePanelRegistry* global_registry) {\n"
                "  global_registry->Register(std::make_unique<SidePanelEntry>(\n"
                "      SidePanelEntry::Key(SidePanelEntry::Id::kReadingList),\n"
                "      base::BindRepeating(&CreateReadingListWebView, &profile_.get(),\n"
                "                          &tab_strip_model_.get()),\n"
                "      /*default_content_width_callback=*/base::NullCallback()));\n"
                "}\n",
                encoding="utf-8",
            )

            agent_control = (
                source
                / "chrome/browser/ui/stead/agent_control/stead_agent_control_service.cc"
            )
            agent_control.parent.mkdir(parents=True)
            agent_control.write_text(
                "void Block(content::WebContents* opened) {\n"
                "  blocks.insert_or_assign(1, opened->IgnoreInputEvents());\n"
                "}\n",
                encoding="utf-8",
            )

            sidebar = source / "chrome/browser/ui/webui/side_panel/stead_sidebar"
            sidebar.mkdir(parents=True)
            sidebar_cc = sidebar / "stead_sidebar_ui.cc"
            sidebar_cc.write_text(
                '#include "base/functional/bind.h"\n'
                '#include "chrome/browser/profiles/profile.h"\n'
                "SteadSidebarUI::SteadSidebarUI(content::WebUI* web_ui) {\n"
                "  web_ui->RegisterMessageCallback(\n"
                '      "closeSteadSidebar",\n'
                "      base::BindRepeating(&SteadSidebarUI::HandleClose,\n"
                "                          base::Unretained(this)));\n"
                "}\n"
                "WEB_UI_CONTROLLER_TYPE_IMPL(SteadSidebarUI)\n",
                encoding="utf-8",
            )
            sidebar_h = sidebar / "stead_sidebar_ui.h"
            sidebar_h.write_text(
                "#include <string_view>\n"
                "class SteadSidebarUI {\n"
                "  void HandleClose(const base::ListValue&);\n"
                "};\n",
                encoding="utf-8",
            )

            subprocess.run([str(normalizer), str(source)], check=True)

            text = coordinator.read_text(encoding="utf-8")
            self.assertIn("profile, scope, std::move(close_cb)", text)
            self.assertIn("entry->set_should_show_header(false);", text)
            self.assertIn('side_panel_ui.h', text)
            self.assertIn(
                'components/sessions/content/session_tab_helper.h', text
            )
            self.assertNotIn('chrome/browser/sessions/session_tab_helper.h', text)
            self.assertNotIn("profile, scope, base::RepeatingClosure()", text)
            self.assertIn("stead_agent_control_service.h", text)
            self.assertIn("stead_agent_control_service_factory.h", text)

            agent_text = agent_control.read_text(encoding="utf-8")
            self.assertIn("opened->IgnoreInputEvents(std::nullopt)", agent_text)
            self.assertNotIn("opened->IgnoreInputEvents()", agent_text)
            sidebar_text = sidebar_cc.read_text(encoding="utf-8")
            self.assertIn('"openSteadAiSettings"', sidebar_text)
            self.assertIn("HandleOpenAiSettings", sidebar_text)
            self.assertIn('GURL("chrome://chat/ai-settings")', sidebar_text)
            self.assertIn("HandleOpenAiSettings", sidebar_h.read_text(encoding="utf-8"))

    def test_normalize_upgrades_resumed_brain_to_multi_tab_context(self):
        repo_root = Path(__file__).resolve().parents[2]
        normalizer = repo_root / ".github/scripts/github_normalize_chromium_sources.sh"

        with tempfile.TemporaryDirectory() as tmpdirname:
            brain = Path(tmpdirname) / "chrome/browser/ui/stead/brain"
            brain.mkdir(parents=True)
            (brain / "brain_console.mojom").write_text(
                "SendMessage(string session_id, string text, BrainTabContext? tab_context,\n",
                encoding="utf-8",
            )
            (brain / "stead_brain_service.h").write_text(
                "#include <string>\n"
                "void SendMessage(mojom::BrainTabContextPtr tab_context,\n"
                "                 int model);\n",
                encoding="utf-8",
            )
            (brain / "stead_brain_service.cc").write_text(
                "void SendMessage(mojom::BrainTabContextPtr tab_context, int model) {\n"
                "  if (tab_context) {\n"
                "    base::DictValue tab;\n"
                '    tab.Set("tab_id", tab_context->tab_id);\n'
                '    tab.Set("url", tab_context->url);\n'
                '    tab.Set("title", tab_context->title);\n'
                '    request.Set("tab_context", std::move(tab));\n'
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            subprocess.run([str(normalizer), tmpdirname], check=True)
            subprocess.run([str(normalizer), tmpdirname], check=True)

            mojo = (brain / "brain_console.mojom").read_text(encoding="utf-8")
            header = (brain / "stead_brain_service.h").read_text(encoding="utf-8")
            source = (brain / "stead_brain_service.cc").read_text(encoding="utf-8")
            self.assertIn("array<BrainTabContext> tab_contexts", mojo)
            self.assertEqual(header.count("#include <vector>"), 1)
            self.assertIn("std::vector<mojom::BrainTabContextPtr> tab_contexts", header)
            self.assertIn('request.Set("tab_contexts", std::move(tabs))', source)
            self.assertNotIn('request.Set("tab_context", std::move(tab))', source)


if __name__ == "__main__":
    unittest.main()
