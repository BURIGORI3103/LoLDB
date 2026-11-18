"""2026-11-18 総合レビュー指摘12・13・14の回帰テスト（合成データ・一時ディレクトリのみ、通信なし）。"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import build_pwa  # noqa: E402
import process_url_list  # noqa: E402
from process_url_list import parse_opgg_rsc, validate_parsed_opgg_data  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_opgg_rsc.html"
ITEMS = {1055: "ドラン ブレード", 2003: "体力ポーション", 3047: "プレート スチールキャップ", 6692: "赤月の刃", 6610: "サンダード スカイ", 6333: "デス ダンス"}
RUNES = {8010: "征服者", 9111: "凱旋", 9105: "レジェンド: ヘイスト", 8299: "背水の陣", 8473: "ボーンアーマー", 8453: "生気付与"}
PATHS = {8000: "栄華", 8400: "不滅"}
CHAMPS = {"varus": {"id": "Varus", "name": "ヴァルス"}, "singed": {"id": "Singed", "name": "シンジド"}}


class MainChampionValidationTest(unittest.TestCase):
    """指摘12: 対面欄に名前があるだけの別チャンピオンのページを検証で通さない。"""

    def setUp(self):
        self.html = FIXTURE.read_text(encoding="utf-8")
        self.parsed = parse_opgg_rsc(self.html, ITEMS, RUNES, PATHS, CHAMPS, latest_version="16.20.1")

    def test_requested_champion_page_is_accepted(self):
        ok, msg = validate_parsed_opgg_data(self.parsed, self.html, "aatrox")
        self.assertTrue(ok, msg)

    def test_counter_names_do_not_identify_the_page(self):
        for slug in ("varus", "singed"):
            ok, _ = validate_parsed_opgg_data(self.parsed, self.html, slug)
            self.assertFalse(ok, f"Aatrox のページを {slug} として受け入れた")

    def test_page_without_main_champion_is_rejected(self):
        html = self.html.replace("<title>Aatrox Build - OP.GG</title>", "<title>OP.GG</title>")
        ok, _ = validate_parsed_opgg_data(self.parsed, html, "aatrox")
        self.assertFalse(ok)

    def test_canonical_url_identifies_main_champion(self):
        html = self.html.replace(
            "<title>Aatrox Build - OP.GG</title>",
            '<title>OP.GG</title><link rel="canonical" href="https://www.op.gg/champions/aatrox/build">',
        )
        self.assertTrue(validate_parsed_opgg_data(self.parsed, html, "aatrox")[0])
        self.assertFalse(validate_parsed_opgg_data(self.parsed, html, "varus")[0])


class PatchSelectionTest(unittest.TestCase):
    """指摘13: 旧パッチ指定で取得先が切り替わらない収集を、通信前に止める。別パッチのページも拒否する。"""

    def test_old_patch_stops_before_any_fetch(self):
        argv = ["process_url_list.py", "--patch", "16.20.1"]
        with (
            patch.object(sys, "argv", argv),
            patch.object(process_url_list, "fetch_json", return_value=["16.22.1", "16.21.1"]) as fetch,
            patch.object(process_url_list, "build_dictionaries") as dictionaries,
            patch.object(process_url_list.urllib.request, "urlopen") as urlopen,
        ):
            with self.assertRaises(SystemExit) as ctx:
                process_url_list.run()
        self.assertNotEqual(ctx.exception.code, 0)
        dictionaries.assert_not_called()
        urlopen.assert_not_called()
        self.assertEqual(fetch.call_count, 1)  # Data Dragon の最新版一覧だけ

    def test_page_of_other_patch_is_rejected(self):
        self.assertTrue(process_url_list.page_matches_patch("<div>Patch 16.22</div>", "16.22.1"))
        self.assertFalse(process_url_list.page_matches_patch("<div>Patch 16.21</div>", "16.22.1"))
        self.assertFalse(process_url_list.page_matches_patch("<div>Patch 16.221</div>", "16.22.1"))


class MissingSourceBuildTest(unittest.TestCase):
    """指摘14: 正本が欠けたら既存の配布物を保持したまま非0で終了する。"""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "merged_data").mkdir()
        (self.root / "dist").mkdir()
        self.outputs = {
            self.root / "dist" / "index.html": "旧配布物",
            self.root / "index.html": "旧配布物",
        }
        for path, text in self.outputs.items():
            path.write_text(text, encoding="utf-8")

    def _write(self, name, data):
        (self.root / "merged_data" / name).write_text(json.dumps(data), encoding="utf-8")

    def _assert_fails_and_preserves(self):
        with self.assertRaises(SystemExit) as ctx:
            build_pwa.build(base_dir=self.root)
        self.assertNotEqual(ctx.exception.code, 0)
        for path, text in self.outputs.items():
            self.assertEqual(path.read_text(encoding="utf-8"), text)

    def test_missing_items_source(self):
        self._write("all_champions.json", {"Aatrox": {"patch": "16.22.1"}})
        self._assert_fails_and_preserves()

    def test_missing_champions_source(self):
        self._write("all_items.json", {"1055": {"name": "ドラン ブレード"}})
        self._assert_fails_and_preserves()

    def test_empty_items_source(self):
        self._write("all_champions.json", {"Aatrox": {"patch": "16.22.1"}})
        self._write("all_items.json", {})
        self._assert_fails_and_preserves()


if __name__ == "__main__":
    unittest.main()
