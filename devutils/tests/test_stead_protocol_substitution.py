import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SteadProtocolSubstitutionTest(unittest.TestCase):
    def test_repairs_unrelated_helium_layout_include(self):
        repo_root = Path(__file__).resolve().parents[2]
        script = repo_root / "devutils" / "stead_protocol_substitution.py"

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "stead_protocol_substitution", script
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmpdirname:
            tmp_path = Path(tmpdirname)
            (tmp_path / "OWNERS").write_text("", encoding="utf-8")
            for rel in module.TARGETS:
                path = tmp_path / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    'const char* scheme = content::kHeliumUIScheme;\n',
                    encoding="utf-8",
                )

            browser_commands = tmp_path / "chrome/browser/ui/browser_commands.cc"
            browser_commands.write_text(
                '#include "chrome/browser/ui/stead/stead_layout_state_controller.h"\n'
                "const char* scheme = content::kHeliumUIScheme;\n",
                encoding="utf-8",
            )
            render_thread = tmp_path / "content/renderer/render_thread_impl.cc"
            render_thread.write_text(
                "// helium:\n"
                'const char* literal = "helium";\n'
                "WebString helium_scheme(WebString::FromAscii(kHeliumUIScheme));\n",
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, str(script), "-t", str(tmp_path)],
                check=True,
                text=True,
            )

            self.assertIn(
                '#include "chrome/browser/ui/helium/helium_layout_state_controller.h"',
                browser_commands.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "content::kSteadUIScheme",
                browser_commands.read_text(encoding="utf-8"),
            )

            rendered = render_thread.read_text(encoding="utf-8")
            self.assertIn("// stead:", rendered)
            self.assertIn('"stead"', rendered)
            self.assertIn("stead_scheme", rendered)


if __name__ == "__main__":
    unittest.main()
