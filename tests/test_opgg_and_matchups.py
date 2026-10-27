"""
LoLDB - OP.GG RSC Fixture パーサー検証 ＆ レーン別相性分離テスト
"""
import unittest
from pathlib import Path
import sys
import tempfile
import shutil

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from process_url_list import parse_opgg_rsc, validate_parsed_opgg_data
from build_comprehensive_matchups import calculate_matchup


class TestLoLDBQuality(unittest.TestCase):
    def test_opgg_rsc_fixture_parsing_and_validation(self):
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "sample_opgg_rsc.html"
        html = fixture_path.read_text(encoding="utf-8")

        item_dict = {1055: "ドラン ブレード", 2003: "体力ポーション", 3047: "プレート スチールキャップ", 6692: "赤月の刃", 6610: "サンダード スカイ", 6333: "デス ダンス"}
        rune_dict = {8010: "征服者", 9111: "凱旋", 9105: "レジェンド: ヘイスト", 8299: "背水の陣", 8473: "ボーンアーマー", 8453: "生気付与"}
        path_dict = {8000: "栄華", 8400: "不滅"}
        champ_dict = {"varus": {"id": "Varus", "name": "ヴァルス"}, "singed": {"id": "Singed", "name": "シンジド"}}

        parsed = parse_opgg_rsc(html, item_dict, rune_dict, path_dict, champ_dict, latest_version="16.20.1")
        is_valid, msg = validate_parsed_opgg_data(parsed, html, "aatrox")
        self.assertTrue(is_valid, f"Validation failed: {msg}")
        self.assertEqual(parsed["roles"], ["TOP", "JUG"])
        self.assertEqual(parsed["runes"]["primary"]["keystone_name"], "征服者")
        self.assertEqual(len(parsed["build"]["core"]), 3)
        self.assertEqual(parsed["matchups"]["favorable"][0]["role"], "TOP")
        self.assertEqual(parsed["matchups"]["favorable"][0]["is_estimated"], False)

        # 空レスポンスやブロック画面は必ず失敗と判定され再取得対象に残ること
        empty_parsed = parse_opgg_rsc("<html>Blocked</html>", item_dict, rune_dict, path_dict, champ_dict)
        valid_empty, _ = validate_parsed_opgg_data(empty_parsed, "<html>Blocked</html>", "aatrox")
        self.assertFalse(valid_empty)

    def test_lane_isolation_in_matchup_calculation(self):
        me = {
            "id": "Aatrox",
            "name": "エイトロックス",
            "patch": "16.20.1",
            "roles": ["TOP", "JUG"],
            "stats": {"attackrange": 175},
            "damage_profile": {"primary_type": "AD"},
            "sustain_info": {"has_sustain": True},
            "matchups": {
                "favorable": [{"champion_id": "Varus", "name": "ヴァルス", "winrate": "59.03%", "role": "TOP"}]
            },
            "role_data": {
                "TOP": {
                    "matchups": {
                        "favorable": [{"champion_id": "Varus", "name": "ヴァルス", "winrate": "59.03%", "role": "TOP"}],
                        "unfavorable": [],
                    }
                },
                "JUG": {
                    "matchups": {
                        "favorable": [],
                        "unfavorable": [],
                    }
                },
            },
        }
        opp = {
            "id": "Varus",
            "name": "ヴァルス",
            "patch": "16.20.1",
            "roles": ["ADC", "TOP"],
            "stats": {"attackrange": 575},
            "damage_profile": {"primary_type": "AD"},
            "sustain_info": {"has_sustain": False},
        }

        # TOPレーン指定時は実測データが返る
        res_top = calculate_matchup(me, opp, target_role="TOP")
        self.assertFalse(res_top["is_estimated"])
        self.assertEqual(res_top["role"], "TOP")
        self.assertEqual(res_top["winrate"], "59.03%")

        # JUGレーン指定時はTOPの実測データが混入せず、推定データとして返る
        res_jug = calculate_matchup(me, opp, target_role="JUG")
        self.assertTrue(res_jug["is_estimated"])
        self.assertIsNone(res_jug["winrate"])

        # レーン不明(None)時も実測データとして表示せず推定になる
        res_unknown = calculate_matchup(me, opp, target_role=None)
        self.assertTrue(res_unknown["is_estimated"])
        self.assertIsNone(res_unknown["winrate"])

    def test_changelog_auto_sync_in_pwa(self):
        from build_pwa import _parse_markdown_update_block, load_and_render_changelog

        update_md_text = (BASE_DIR / "UPDATE.md").read_text(encoding="utf-8")
        parsed_latest = _parse_markdown_update_block(update_md_text)
        self.assertIsNotNone(parsed_latest)
        expected_ver = parsed_latest["version"]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_base = Path(temp_dir)
            shutil.copy2(BASE_DIR / "UPDATE.md", temp_base / "UPDATE.md")
            (temp_base / "data").mkdir()
            history = BASE_DIR / "data" / "changelog_history.json"
            if history.exists():
                shutil.copy2(history, temp_base / "data" / history.name)
            latest_ver, rendered_html = load_and_render_changelog(temp_base, temp_base / "dist")
        self.assertEqual(latest_ver, expected_ver)
        self.assertIn(expected_ver, rendered_html)

        dist_html = (BASE_DIR / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"/ {expected_ver} ℹ️", dist_html)
        self.assertIn(f'<span class="changelog-ver">⚔️ {expected_ver}</span>', dist_html)


if __name__ == "__main__":
    unittest.main()
