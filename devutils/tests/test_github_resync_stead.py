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


if __name__ == "__main__":
    unittest.main()
