import unittest

import test_patch_merge
from merge_data import merge_record


class IntegrationGuards(unittest.TestCase):
    def test_rejects_old_or_unverified_role_statistics(self):
        for field, value in (("patch", "16.20"), ("patch_verified", False), ("patch_verified", 1)):
            with self.subTest(field=field, value=value):
                base, strategy = test_patch_merge.MergeTests().inputs()
                source = strategy["role_data"]["TOP"]["opgg_source"]
                source.update({"patch": "16.21", "patch_verified": True, field: value})
                with self.assertRaisesRegex(ValueError, "TOP"):
                    merge_record(base, strategy, {})

    def test_legacy_entry_stops_before_opening_data(self):
        import sync_all_roles_complete
        from unittest.mock import patch
        with patch("builtins.open") as opener:
            with self.assertRaisesRegex(SystemExit, "merge_data.py"):
                sync_all_roles_complete.main()
        opener.assert_not_called()


    def test_legacy_migration_stops_before_opening_data(self):
        import migrate_matchups
        from unittest.mock import patch
        with patch("builtins.open") as opener:
            with self.assertRaisesRegex(SystemExit, "refresh_matchup_stats.py"):
                migrate_matchups.main()
        opener.assert_not_called()

    def test_unverified_matchup_does_not_become_measured(self):
        from build_comprehensive_matchups import calculate_matchup
        current = {"champion_id": "Varus", "winrate": "60%", "winrate_num": 60.0,
                   "role": "TOP", "patch": "16.21.1", "source": "opgg_stats", "games": 8}
        for field in ("patch", "source", "games"):
            with self.subTest(field=field):
                entry = {key: value for key, value in current.items() if key != field}
                me = {"id": "Garen", "patch": "16.21.1", "roles": ["TOP"],
                      "matchups": {"favorable": [entry]}}
                actual = calculate_matchup(me, {"id": "Varus"}, target_role="TOP")
                self.assertTrue(actual["is_estimated"])
