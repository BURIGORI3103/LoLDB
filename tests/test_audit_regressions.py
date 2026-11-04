"""監査で確認した抽出境界と保存データの回帰を検証する。"""
import json
import unittest
from pathlib import Path

from process_url_list import parse_opgg_rsc

BASE = Path(__file__).resolve().parent.parent


class ExtractionRegressionTests(unittest.TestCase):
    def test_empty_boots_does_not_consume_next_group(self):
        payload = '{"boots_0":[],"core_items_0":[{"metaId":3070}]}'
        html = 'self.__next_f.push([1,' + json.dumps(payload) + '])'
        result = parse_opgg_rsc(html, {3070: "女神の涙"}, {}, {}, {})
        self.assertEqual(result["build"]["boots"], [])

    def test_rsc_japanese_names_remain_utf8(self):
        page = {"data": {"rune_pages": [{"builds": [{
            "main_runes": [[{"id": 1, "name": "日本語ルーン", "isActive": True}]],
            "sub_runes": [], "shards": [],
        }]}]}}
        html = 'self.__next_f.push([1,' + json.dumps(json.dumps(page, ensure_ascii=False), ensure_ascii=False) + '])'
        result = parse_opgg_rsc(html, {}, {}, {}, {})
        self.assertEqual(result["runes"]["primary"]["keystone_name"], "日本語ルーン")


class StoredDataRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.champs = json.loads((BASE / "merged_data/all_champions.json").read_text(encoding="utf-8"))
        cls.items = json.loads((BASE / "merged_data/all_items.json").read_text(encoding="utf-8"))

    def test_secondary_paths_are_known(self):
        paths = {"栄華", "覇道", "魔道", "不滅", "天啓"}
        for cid, champ in self.champs.items():
            for role, data in [("primary", champ), *champ.get("role_data", {}).items()]:
                with self.subTest(champion=cid, role=role):
                    self.assertIn(data["runes"]["secondary"]["path"], paths)

    def test_cassiopeia_has_no_boots(self):
        champ = self.champs["Cassiopeia"]
        for data in [champ, *champ["role_data"].values()]:
            self.assertEqual(data["build"]["boots"], [])
            for pattern in data.get("build_patterns", []):
                self.assertEqual(pattern.get("boots_items"), [])

    def test_catalog_names_and_recipe_links(self):
        names = [item.get("display_name", item["name"]) for item in self.items.values()]
        self.assertEqual(len(names), len(set(names)))
        for iid, item in self.items.items():
            self.assertLessEqual(len(iid), 4)
            for ref in item.get("from", []) + item.get("into", []):
                self.assertIn(str(ref), self.items)
        self.assertIn("3040", self.items)
        self.assertIn("3042", self.items)


if __name__ == "__main__":
    unittest.main()
