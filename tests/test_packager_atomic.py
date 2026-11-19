"""配布物の出力が途中で失敗しても、版の混在や一時ファイルを残さないことを検証する。"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from pwa_builder import packager


WORKER_TEMPLATE = "const v='__VER_HASH__';const c='__DYNAMIC_CORE_CACHE__';const h='__HTML_HASH__';\n"


class PackagerAtomicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.dist = self.base / "dist"
        self.dist.mkdir()
        (self.base / "service_worker_template.js").write_text(WORKER_TEMPLATE, encoding="utf-8")

    def build(self, html: str, version: str = "v1.0.0") -> None:
        with redirect_stdout(io.StringIO()):
            packager.write_distribution(self.base, self.dist, html, version)

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.base)): path.read_bytes()
            for path in sorted(self.base.rglob("*")) if path.is_file()
        }

    def test_failure_while_staging_keeps_previous_version(self):
        self.build("<p>旧版</p>\n")
        before = self.snapshot()

        original = Path.write_text
        calls = 0

        def fail_on_fourth(path, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("合成の書き込み失敗")
            return original(path, *args, **kwargs)

        with patch.object(Path, "write_text", fail_on_fourth):
            with self.assertRaises(OSError):
                self.build("<p>新版</p>\n", "v2.0.0")

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.base.rglob("*.loldb-tmp")), [])

    def test_successful_build_matches_pairs_and_zip(self):
        self.build("<p>版</p>\n")
        for name in ("index.html", "sw.js", "manifest.json"):
            self.assertEqual((self.base / name).read_bytes(), (self.dist / name).read_bytes())
        self.assertEqual(list(self.base.rglob("*.loldb-tmp")), [])
        with ZipFile(self.base / "LoLDB_dist.zip") as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [".nojekyll", "index.html", "manifest.json", "sw.js"],
            )

    def test_stale_temporary_file_is_not_zipped(self):
        (self.dist / ".index.html.1.loldb-tmp").write_text("残骸", encoding="utf-8")
        self.build("<p>版</p>\n")
        with ZipFile(self.base / "LoLDB_dist.zip") as archive:
            self.assertNotIn(".index.html.1.loldb-tmp", archive.namelist())


if __name__ == "__main__":
    unittest.main()
