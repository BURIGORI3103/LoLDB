"""不完全な公式入力で既存の配布データが失われないことを確認する。"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from merge_data import OFFICIAL_STAT_FIELDS, merge_champion_data, save_json
import test_patch_merge


class MergePublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        previous_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous_cwd)
        Path("champions_data").mkdir()
        Path("merged_data").mkdir()
        self.master = Path("merged_data/all_champions.json")
        self.individual = Path("merged_data/Garen.json")
        self.original_master = b'{"Garen": {"id": "Garen", "patch": "16.22.1"}}'
        self.original_individual = b'{"id": "Garen", "patch": "16.22.1"}'
        self.master.write_bytes(self.original_master)
        self.individual.write_bytes(self.original_individual)


    def official_inputs(self):
        base, strategy = test_patch_merge.MergeTests().inputs()
        def skill(slot):
            return {"slot": slot, "name": slot, "description": "", "image": f"{slot}.png"}
        base.update({
            "stats": dict.fromkeys(OFFICIAL_STAT_FIELDS, 1),
            "spells": [skill(slot) for slot in "QWER"],
            "abilities": [skill("Passive")],
        })
        return base, strategy

    def assert_previous_preserved(self):
        self.assertEqual(self.master.read_bytes(), self.original_master)
        self.assertEqual(self.individual.read_bytes(), self.original_individual)

    def test_empty_official_snapshot_preserves_previous_data(self):
        with self.assertRaises(ValueError):
            merge_champion_data()
        self.assert_previous_preserved()

    def test_null_official_record_preserves_previous_data(self):
        Path("champions_data/Garen.json").write_text("null", encoding="utf-8")
        with self.assertRaises(ValueError):
            merge_champion_data()
        self.assert_previous_preserved()

    def test_incomplete_nonempty_snapshot_preserves_previous_data(self):
        base, strategy = self.official_inputs()
        base["id"] = "Annie"
        Path("champions_data/Annie.json").write_text(json.dumps(base), encoding="utf-8")
        Path("strategy_data").mkdir()
        Path("strategy_data/annie.json").write_text(json.dumps(strategy), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Garen"):
            merge_champion_data()
        self.assert_previous_preserved()

    def test_failed_atomic_replacement_keeps_original_file(self):
        with patch("merge_data.os.replace", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                save_json({"new": True}, self.master)
        self.assert_previous_preserved()
        self.assertEqual(set(Path("merged_data").iterdir()), {self.master, self.individual})

    def test_mixed_official_patches_preserve_previous_data(self):
        base, strategy = self.official_inputs()
        Path("strategy_data").mkdir()
        for champ_id, patch_version in (("Annie", "16.21.1"), ("Garen", "16.22.1")):
            official = {**base, "id": champ_id, "patch": patch_version}
            Path(f"champions_data/{champ_id}.json").write_text(json.dumps(official), encoding="utf-8")
            Path(f"strategy_data/{champ_id.lower()}.json").write_text(json.dumps(strategy), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "複数パッチ"):
            merge_champion_data()
        self.assert_previous_preserved()

    def test_valid_snapshot_check_does_not_write_outputs(self):
        base, strategy = self.official_inputs()
        Path("strategy_data").mkdir()
        Path("champions_data/Garen.json").write_text(json.dumps(base), encoding="utf-8")
        Path("strategy_data/garen.json").write_text(json.dumps(strategy), encoding="utf-8")
        merge_champion_data(check_only=True)
        self.assert_previous_preserved()

    def test_empty_official_skill_payload_preserves_previous_data(self):
        base, strategy = self.official_inputs()
        Path("strategy_data").mkdir()
        Path("strategy_data/garen.json").write_text(json.dumps(strategy), encoding="utf-8")
        for field in ("stats", "spells", "abilities"):
            with self.subTest(field=field):
                invalid = {**base, field: {} if field == "stats" else []}
                Path("champions_data/Garen.json").write_text(json.dumps(invalid), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Garen"):
                    merge_champion_data()
                self.assert_previous_preserved()
