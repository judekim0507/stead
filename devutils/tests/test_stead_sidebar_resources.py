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
            self.assertIn(
                '<part file="${root_gen_dir}/chrome/browser/resources/'
                'stead_sidebar/resources.grdp" />',
                text,
            )

    def test_sidebar_build_patch_compiles_and_packs_mojo_modules(self):
        repo_root = Path(__file__).resolve().parents[2]
        patch = repo_root / "patches/stead/sidebar/stead-sidebar-webui-files.patch"
        text = patch.read_text(encoding="utf-8")

        self.assertIn('import("//ui/webui/resources/tools/build_webui.gni")', text)
        self.assertIn('build_webui("build")', text)
        self.assertIn("generate_grdp = true", text)
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
        self.assertIn('deps = [ ":build_grdp" ]', text)
        self.assertIn('inputs = [ "$target_gen_dir/resources.grdp" ]', text)

    def test_agent_control_generates_webui_mojo_bindings(self):
        repo_root = Path(__file__).resolve().parents[2]
        patch = repo_root / "patches/stead/agent-control/native-control-layer.patch"
        text = patch.read_text(encoding="utf-8")

        self.assertIn('+  webui_module_path = "/"', text)


if __name__ == "__main__":
    unittest.main()
