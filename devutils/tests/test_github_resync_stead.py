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


if __name__ == "__main__":
    unittest.main()
