import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from update_champion_sustain import analyze_champion_sustain


def champ(desc):
    return {"abilities": [], "spells": [{"slot": "W", "name": "テスト", "description": desc}]}


class SustainDetectionTests(unittest.TestCase):
    def test_shield_listed_with_other_buffs_is_detected(self):
        # パッチ16.22のメルWなど「シールドと増加移動速度を付与」の表記を判定する。
        for desc in ("このノヴァは自身と味方にシールドと増加移動速度を付与する。",
                     "シールドと移動速度を獲得し、少ししてから周囲を爆発させる。"):
            info = analyze_champion_sustain("X", champ(desc))
            self.assertTrue(info["has_shield"], desc)
            self.assertEqual(info["shield_skills"], ["テスト"])

    def test_text_without_shield_gain_is_not_detected(self):
        info = analyze_champion_sustain("X", champ("敵の飛翔物を破壊し、レーザー弾で反撃する。"))
        self.assertFalse(info["has_sustain"])


if __name__ == "__main__":
    unittest.main()
