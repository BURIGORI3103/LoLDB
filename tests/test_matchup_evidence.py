"""根拠のない解説と別レーンへの流用を防止する。"""
import unittest
from apply_matchup_reasons import apply_reasons, load_evidence


class EvidenceTests(unittest.TestCase):
    def test_only_exact_supported_pair_gets_reason(self):
        champion = {"id": "Aatrox", "roles": ["TOP", "JUG"], "role_data": {}}
        for role in champion["roles"]:
            champion["role_data"][role] = {"matchups": {"favorable": [{"champion_id": "Trundle", "reason": "未確認文"}, {"champion_id": "Anivia", "reason": "未確認文"}], "unfavorable": [{"champion_id": "Trundle", "reason": "逆方向"}]}}
        apply_reasons(champion, load_evidence())
        top = champion["role_data"]["TOP"]["matchups"]
        self.assertTrue(top["favorable"][0]["reason_evidence"]["source_url"])
        self.assertEqual(top["favorable"][1]["reason"], "")
        self.assertEqual(top["unfavorable"][0]["reason"], "")
        self.assertEqual(champion["role_data"]["JUG"]["matchups"]["favorable"][0]["reason"], "")
