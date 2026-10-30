"""パッチ更新時の補完保持と古い統計の混入防止を検証する。"""
import unittest
from merge_data import merge_record


class MergeTests(unittest.TestCase):
    def inputs(self):
        base = {"id": "Garen", "patch": "16.21.1", "roles": ["Fighter"]}
        measured = {"build": {"core": [{"name": "新アイテム", "item_id": "1"}], "starter": [], "boots": []}, "runes": {}, "matchups": {"favorable": [], "unfavorable": []}, "summoner_spells": ["フラッシュ"], "opgg_source": {"role": "TOP"}}
        strategy = {"patch": "16.21.1", "roles": ["TOP"], "role_data": {"TOP": measured}, "opgg_source": {"patch_verified": True}}
        return base, strategy

    def test_preserves_manual_extras_replaces_statistics(self):
        base, strategy = self.inputs()
        previous = {"combos": ["手動コンボ"], "role_data": {"TOP": {"skill_order": "E > Q > W", "build_patterns": ["旧ビルド"]}, "MID": {}}, "matchup_matrix": {"古い統計": {}}}
        merged = merge_record(base, strategy, previous)
        self.assertEqual(merged["combos"], ["手動コンボ"])
        self.assertEqual(merged["role_data"]["TOP"]["skill_order"], "E > Q > W")
        self.assertEqual(merged["role_data"]["TOP"]["build_patterns"][0]["core"], ["新アイテム"])
        self.assertNotIn("MID", merged["role_data"])
        self.assertNotIn("matchup_matrix", merged)

    def test_old_patch_is_rejected(self):
        base, strategy = self.inputs()
        strategy["patch"] = "16.20.1"
        with self.assertRaises(ValueError):
            merge_record(base, strategy, {})
