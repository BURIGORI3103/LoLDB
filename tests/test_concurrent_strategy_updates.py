"""ロール別統計と対面更新が同じ攻略JSONを古い内容で上書きしないことを確認する（合成データのみ）。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import refresh_role_stats
from data_transaction import publish, revision


class ConcurrentStrategyUpdateTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        for name in ("champions_data", "strategy_data", "merged_data"):
            (self.root / name).mkdir()
        (self.root / "champions_data/Garen.json").write_text("{}", encoding="utf-8")
        self.strategy = self.root / "strategy_data/garen.json"
        self.strategy.write_text(json.dumps({
            "patch": "16.22.1", "slug": "garen", "roles": ["TOP"],
            "opgg_source": {"patch_verified": True}, "matchups": {"favorable": [], "unfavorable": []},
        }), encoding="utf-8")

    def test_publish_rejects_any_stale_input_in_list(self):
        master = self.root / "merged_data/all_champions.json"
        master.write_bytes(b"{}")
        expected = [(master, revision(master)), (self.strategy, revision(self.strategy))]
        self.strategy.write_text('{"newer": true}', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "garen.json"):
            publish(self.root, [(self.strategy, b'{"stale": true}')], expected=expected)
        self.assertEqual(self.strategy.read_text(encoding="utf-8"), '{"newer": true}')

    def test_role_stats_do_not_overwrite_strategy_saved_during_fetch(self):
        newer = '{"saved_by": "matchup refresh"}'

        def page(*_args, **_kwargs):
            # 取得中に対面更新が同じ攻略JSONを保存した状況を再現する。
            self.strategy.write_text(newer, encoding="utf-8")
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b"Build for Top, Patch 16.22"
            return response

        parsed = {"matchups": {"favorable": [], "unfavorable": []}}
        with patch.object(refresh_role_stats, "BASE", self.root), \
                patch.object(refresh_role_stats, "build_dictionaries",
                             return_value=("16.22.1", {}, {}, {}, {}, {})), \
                patch.object(refresh_role_stats, "parse_opgg_rsc", return_value=parsed), \
                patch.object(refresh_role_stats, "validate_parsed_opgg_data", return_value=(True, "")), \
                patch.object(refresh_role_stats.urllib.request, "urlopen", side_effect=page), \
                patch("sys.argv", ["refresh_role_stats.py"]):
            with self.assertRaisesRegex(RuntimeError, "更新されました"):
                refresh_role_stats.run()
        self.assertEqual(self.strategy.read_text(encoding="utf-8"), newer)


if __name__ == "__main__":
    unittest.main()
