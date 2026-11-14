"""生成済みロールのパッチ検証済みフラグを読み取り検査する。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import verify_patch_data


class PatchValidatorTests(unittest.TestCase):
    def test_each_role_requires_verified_boolean(self):
        base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(verify_patch_data, "BASE", base))
        for directory in ("champions_data", "merged_data", "docs", "dist"):
            (base / directory).mkdir()

        champion = {
            "patch": "16.22.1",
            "wiki_info": {"status": "success"},
            "opgg_source": {"patch": "16.22", "patch_verified": True},
            "roles": ["TOP"],
            "role_data": {
                "TOP": {
                    "opgg_source": {"role": "TOP", "patch": "16.22", "patch_verified": True},
                    "runes": {"primary": {"keystone": "fixture"}},
                    "build": {"core": [{"item_id": "1"}]},
                }
            },
            "matchup_matrix_by_role": {"TOP": {}},
            **dict.fromkeys(("attack_type", "damage_profile", "sustain_info", "combos", "skill_matrix")),
        }
        (base / "champions_data/Garen.json").write_text('{"patch":"16.22.1"}', encoding="utf-8")
        (base / "merged_data/all_items.json").write_text('{"1":{}}', encoding="utf-8")
        (base / "docs/LoL_URL_list.md").write_text("- [x] Garen\n", encoding="utf-8")
        for html in ("index.html", "dist/index.html"):
            (base / html).write_text("Patch 16.22 wikiの考察・対策", encoding="utf-8")

        def save_champion():
            (base / "merged_data/Garen.json").write_text(json.dumps(champion), encoding="utf-8")
            (base / "merged_data/all_champions.json").write_text(
                json.dumps({"Garen": champion}), encoding="utf-8"
            )

        save_champion()
        verify_patch_data.run(write_report=False)
        self.assertFalse((base / "docs/data_refresh_report.json").exists())

        source = champion["role_data"]["TOP"]["opgg_source"]
        for unverified in (False, 1, "true"):
            with self.subTest(unverified=unverified):
                source["patch_verified"] = unverified
                save_champion()
                with self.assertRaisesRegex(ValueError, "Garen TOP"):
                    verify_patch_data.run(write_report=False)
