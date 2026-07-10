import subprocess
import tempfile
import unittest
from pathlib import Path


class SteadSidebarResourcesTest(unittest.TestCase):
    def test_sidebar_grd_includes_generated_mojo_grdp(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = repo_root / "resources/stead/gen_sidebar_grd.py"

        with tempfile.TemporaryDirectory() as tmpdirname:
            bundle = Path(tmpdirname) / "bundle"
            bundle.mkdir()
            (bundle / "index.html").write_text("<script></script>", encoding="utf-8")
            (bundle / "BUILD.gn").write_text("# ignored\n", encoding="utf-8")
            out_grd = bundle / "stead_sidebar_resources.grd"

            subprocess.run(["python3", str(script), str(bundle), str(out_grd)], check=True)

            text = out_grd.read_text(encoding="utf-8")
            self.assertIn('resource_path="index.html"', text)
            self.assertNotIn("BUILD.gn", text)
            self.assertIn('resource_path="agent_control.mojom-webui.js"', text)
            self.assertIn('resource_path="brain_console.mojom-webui.js"', text)
            self.assertIn("${root_gen_dir}/chrome/browser/resources/stead_sidebar/tsc/", text)
            self.assertIn('use_base_dir="false"', text)
            self.assertNotIn("<part ", text)

    def test_sidebar_build_patch_compiles_and_packs_mojo_modules(self):
        repo_root = Path(__file__).resolve().parents[2]
        patch = repo_root / "patches/stead/sidebar/stead-sidebar-webui-files.patch"
        text = patch.read_text(encoding="utf-8")

        self.assertNotIn('build_webui("build")', text)
        self.assertIn('import("//tools/typescript/ts_library.gni")', text)
        self.assertIn('import("//tools/typescript/webui_path_mappings.gni")', text)
        self.assertIn('preprocess_if_expr("copy_mojo_ts")', text)
        self.assertIn('ts_library("build_ts")', text)
        self.assertIn('group("build_mojo_js")', text)
        self.assertIn(
            "//chrome/browser/ui/stead/agent_control:mojo_bindings_ts__generator",
            text,
        )
        self.assertIn(
            "//chrome/browser/ui/stead/brain:mojo_bindings_ts__generator",
            text,
        )
        self.assertIn("agent_control.mojom-webui.ts", text)
        self.assertIn("brain_console.mojom-webui.ts", text)
        self.assertIn("agent_control.mojom-webui.js", text)
        self.assertIn("brain_console.mojom-webui.js", text)
        self.assertIn('deps = [ ":build_mojo_js" ]', text)
        self.assertIn("inputs = stead_mojo_js_outputs", text)

    def test_agent_control_generates_webui_mojo_bindings(self):
        repo_root = Path(__file__).resolve().parents[2]
        patch = repo_root / "patches/stead/agent-control/native-control-layer.patch"
        text = patch.read_text(encoding="utf-8")

        self.assertIn('+  webui_module_path = "/"', text)

    def test_ask_stead_toolbar_action_is_mapped(self):
        repo_root = Path(__file__).resolve().parents[2]
        series = (repo_root / "patches/series").read_text(encoding="utf-8")
        patch = (
            repo_root
            / "patches/stead/sidebar/restore-ask-stead-toolbar-map.patch"
        )
        text = patch.read_text(encoding="utf-8")

        self.assertIn(
            "stead/sidebar/restore-ask-stead-toolbar-map.patch",
            series,
        )
        self.assertIn(
            "case kActionSidePanelShowReadingList:",
            text,
        )
        self.assertIn(
            "ActionId::kShowReadingList",
            text,
        )
        self.assertIn(
            "add_action(kActionSidePanelShowReadingList",
            text,
        )

    def test_ask_stead_toolbar_button_uses_reading_list_side_panel(self):
        repo_root = Path(__file__).resolve().parents[2]
        series = (repo_root / "patches/series").read_text(encoding="utf-8")
        patch = (
            repo_root
            / "patches/stead/sidebar/ask-stead-button.patch"
        )
        text = patch.read_text(encoding="utf-8")

        self.assertIn(
            "stead/sidebar/ask-stead-button.patch",
            series,
        )
        self.assertNotIn("stead/sidebar/open-ask-stead-toolbar-action.patch", series)
        self.assertIn(
            "SidePanelAction(SidePanelEntryId::kReadingList, IDS_STEAD_SIDEBAR_TITLE",
            text,
        )
        self.assertIn("kActionSidePanelShowReadingList, bwi, true", text)

    def test_sidebar_native_view_marks_webui_ready(self):
        repo_root = Path(__file__).resolve().parents[2]
        text = (
            repo_root
            / "patches/stead/sidebar/repurpose-reading-list-side-panel.patch"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "SteadSidebarSidePanelWebView::SteadSidebarSidePanelWebView", text
        )
        self.assertIn("+  ShowUI();", text)
        self.assertNotIn("OpenGURL", text)
        self.assertNotIn("chrome://chat/ai-chat", text)

    def test_settings_webui_binders_are_registered(self):
        repo_root = Path(__file__).resolve().parents[2]
        patch = (
            repo_root
            / "patches/stead/agent-control/native-control-layer.patch"
        )
        text = patch.read_text(encoding="utf-8")

        self.assertIn(
            "+      CustomizeChromeUI,\n"
            "+      settings::SettingsUI>(map);",
            text,
        )
        self.assertIn(
            "       help_bubble::mojom::HelpBubbleHandlerFactory",
            text,
        )
        self.assertIn(
            "       theme_color_picker::mojom::ThemeColorPickerHandlerFactory,\n"
            "       CustomizeChromeUI\n"
            " #if !BUILDFLAG(IS_CHROMEOS)\n"
            "       ,\n"
            "       ProfileCustomizationUI\n"
            " #endif  // !BUILDFLAG(IS_CHROMEOS)\n"
            "-      >(map);\n"
            "+      ,\n"
            "+      settings::SettingsUI>(map);",
            text,
        )
        self.assertIn(
            "       ProfilePickerUI\n"
            " #endif  //! BUILDFLAG(IS_CHROMEOS)\n"
            "-      >(map);\n"
            "+      ,\n"
            "+      settings::SettingsUI>(map);",
            text,
        )


if __name__ == "__main__":
    unittest.main()
