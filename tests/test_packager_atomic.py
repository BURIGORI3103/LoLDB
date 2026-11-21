"""配布物の出力が途中で失敗しても、版の混在や一時ファイルを残さないことを検証する。"""

import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import data_transaction
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
            packager.write_distribution(
                self.base, self.dist, html, version, changelog_history=f'[{{"version":"{version}"}}]',
            )

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.base)): path.read_bytes()
            for path in sorted(self.base.rglob("*")) if path.is_file()
        }

    def test_failure_while_staging_keeps_previous_version(self):
        self.build("<p>旧版</p>\n")
        before = self.snapshot()

        original = data_transaction._atomic_write

        def fail_on_candidate(path, content):
            if path.name == "3.new":
                raise OSError("合成の書き込み失敗")
            return original(path, content)

        with patch.object(data_transaction, "_atomic_write", side_effect=fail_on_candidate):
            with self.assertRaises(OSError):
                self.build("<p>新版</p>\n", "v2.0.0")

        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.base.rglob("*.loldb-tmp")), [])

    def test_failure_during_replacement_restores_previous_version(self):
        self.build("<p>旧版</p>\n")
        before = self.snapshot()
        replace_file = os.replace

        def fail_on_root_worker(source, destination):
            if Path(destination) == self.base / "sw.js":
                raise PermissionError("合成の置換失敗")
            return replace_file(source, destination)

        with patch.object(os, "replace", side_effect=fail_on_root_worker):
            with self.assertRaises(PermissionError):
                self.build("<p>新版</p>\n", "v2.0.0")
        self.assertEqual(self.snapshot(), before)

    def test_failure_during_zip_generation_leaves_previous_version(self):
        self.build("<p>旧版</p>\n")
        before = self.snapshot()
        with patch.object(ZipFile, "__init__", side_effect=OSError("合成のZIP作成失敗")):
            with self.assertRaises(OSError):
                self.build("<p>新版</p>\n", "v2.0.0")
        self.assertEqual(self.snapshot(), before)

    def test_process_exit_during_replacement_leaves_recoverable_previous_version(self):
        self.build("<p>旧版</p>\n")
        before = self.snapshot()
        child = """
import os
import sys
from pathlib import Path
from pwa_builder.packager import write_distribution

base = Path(sys.argv[1])
replace = os.replace
def exit_on_root_worker(source, destination):
    if Path(destination) == base / "sw.js":
        os._exit(42)
    return replace(source, destination)

os.replace = exit_on_root_worker
write_distribution(base, base / "dist", "<p>新版</p>", "v2.0.0", changelog_history="[]")
"""
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", child, str(self.base)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 42, result.stderr.decode("utf-8", errors="replace"))
        with self.assertRaisesRegex(RuntimeError, "--recover"):
            data_transaction.require_recovered(self.base)
        with redirect_stdout(io.StringIO()):
            self.assertTrue(data_transaction.recover(self.base))
        self.assertEqual(self.snapshot(), before)

    def test_successful_build_matches_pairs_and_zip(self):
        self.build("<p>版</p>\n")
        for name in ("index.html", "sw.js", "manifest.json", "data/changelog_history.json"):
            self.assertEqual((self.base / name).read_bytes(), (self.dist / name).read_bytes())
        self.assertEqual(list(self.base.rglob("*.loldb-tmp")), [])
        with ZipFile(self.base / "LoLDB_dist.zip") as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                [".nojekyll", "data/changelog_history.json", "index.html", "manifest.json", "sw.js"],
            )

    def test_stale_temporary_file_is_not_zipped(self):
        (self.dist / ".index.html.1.loldb-tmp").write_text("残骸", encoding="utf-8")
        self.build("<p>版</p>\n")
        with ZipFile(self.base / "LoLDB_dist.zip") as archive:
            self.assertNotIn(".index.html.1.loldb-tmp", archive.namelist())


if __name__ == "__main__":
    unittest.main()
