"""折りたたみ内の対象群・例外・敵味方の分離を検証する。"""
import unittest
from collect_wiki_matchups import parse_matchups


class CollectionTests(unittest.TestCase):
    def test_hidden_body_and_inline_exceptions(self):
        html = '''<div id="body"><h3>相性・対策<a class="anchor_super" id="counter"></a></h3>
        <div class="plugin_fold_title_plus"><p>敵との相性</p></div><div class="plugin_fold_body" style="display:none">
        <p><strong>有利（Strong Against）</strong><br><img src="image/champ/80/ico_Lux.jpg">/メイジ<br>
        長い射程を生かしてハラスをかわす。ただしゼラス<img src="image/champ/80/ico_Xerath.jpg">は例外。<br><br>
        <strong>不利（Weak Against）</strong><br><img src="image/champ/80/ico_Blitzcrank.jpg">/キャッチャー<br>
        キャッチスキルを受けると逃げづらいので注意する。</p></div>
        <div><p>味方との相性</p></div><div class="plugin_fold_body"><p><em>Strong With</em><br>
        <img src="image/champ/80/ico_Blitzcrank.jpg">/味方<br>キャッチした敵を追撃してキルへつなげやすい。</p></div>
        <h3>スキル紹介</h3><p>無関係な本文</p></div>'''
        names = {"Lux": "ラックス", "Xerath": "ゼラス", "Blitzcrank": "ブリッツクランク"}
        groups, anchor = parse_matchups(html, names)
        self.assertEqual(anchor, "counter")
        self.assertEqual(len(groups), 3)
        self.assertEqual(groups[0]["champion_ids"], ["Lux"])
        self.assertIn("ゼラス", groups[0]["text"])
        self.assertTrue(groups[0]["has_caveat"])
        self.assertEqual(groups[1]["relation"], "enemy")
        self.assertEqual(groups[1]["advantage"], "unfavorable")
        self.assertEqual(groups[2]["relation"], "ally")
        self.assertNotIn("無関係", groups[2]["text"])

    def test_missing_structure_is_not_invented(self):
        groups, _ = parse_matchups('<div id="body"><h3>相性・対策</h3><p>まだ記載されていない</p></div>', {})
        self.assertEqual(groups, [])


class RefreshFailureTests(unittest.TestCase):
    def test_failed_fetch_keeps_previous_matchups(self):
        """--refresh 中に取得が失敗したら、前回の相性データを空で上書きせず非0で終了する。"""
        import json
        import sys
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import collect_wiki_matchups as module

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "merged_data").mkdir()
            (base / "data").mkdir()
            (base / "docs").mkdir()
            champion = {"name": "ラックス", "wiki_info": {"source_url": "https://example.invalid/lux"},
                        "wiki_matchups": {"status": "extracted", "groups": [{"relation": "enemy"}]}}
            master = base / "merged_data/all_champions.json"
            master.write_text(json.dumps({"Lux": champion}, ensure_ascii=False), encoding="utf-8")
            before = master.read_text(encoding="utf-8")
            with patch.object(module, "BASE", base), patch.object(module, "CACHE", base / "cache"), \
                    patch.object(module.urllib.request, "urlopen", side_effect=OSError("timeout")), \
                    patch.object(module.time, "sleep"), patch.object(sys, "argv", ["collect", "--refresh"]):
                with self.assertRaises(SystemExit) as raised:
                    module.main()
            self.assertEqual(raised.exception.code, 1)
            self.assertEqual(master.read_text(encoding="utf-8"), before)
            self.assertFalse((base / "merged_data/Lux.json").exists())
            self.assertFalse((base / "data/wiki_matchups.json").exists())
