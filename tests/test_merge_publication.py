"""不完全な公式入力で既存の配布データが失われないことを確認する。"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_transaction import JOURNAL_NAME, publish, recover, require_recovered, revision
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

    def prepare_valid_update(self):
        base, strategy = self.official_inputs()
        Path("strategy_data").mkdir()
        for cid in ("Annie", "Garen"):
            Path(f"champions_data/{cid}.json").write_text(
                json.dumps({**base, "id": cid}), encoding="utf-8"
            )
            Path(f"strategy_data/{cid.lower()}.json").write_text(json.dumps(strategy), encoding="utf-8")

    def test_partial_merge_write_restores_old_and_removes_new_individual(self):
        self.prepare_valid_update()
        replace = os.replace

        def fail_master(source, target):
            if Path(target).name == self.master.name:
                raise PermissionError("保存できません")
            return replace(source, target)

        with patch("os.replace", side_effect=fail_master):
            with self.assertRaises(PermissionError):
                merge_champion_data()
        self.assert_previous_preserved()
        self.assertFalse(Path("merged_data/Annie.json").exists())

    def interrupt_process_during_update(self):
        script = """
import os
from pathlib import Path
from unittest.mock import patch
from data_transaction import publish

root = Path.cwd()
replace = os.replace

def stop_after_first_output(source, target):
    replace(source, target)
    if Path(target).name == "Garen.json":
        os._exit(43)

with patch("os.replace", side_effect=stop_after_first_output):
    publish(root, [
        (root / "merged_data/Garen.json", b'{"new":true}'),
        (root / "merged_data/all_champions.json", b'{"new":true}'),
    ])
"""
        modules = str(Path(__file__).resolve().parents[1])
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=self.root, capture_output=True,
            env={**os.environ, "PYTHONPATH": modules}, timeout=15
        )
        self.assertEqual(result.returncode, 43, result.stderr)
        self.assertNotEqual(self.individual.read_bytes(), self.original_individual)
        self.assertTrue((self.root / JOURNAL_NAME / "pending.json").is_file())

    def test_forced_exit_blocks_readers_until_recovery(self):
        self.interrupt_process_during_update()
        with self.assertRaisesRegex(RuntimeError, "--recover"):
            require_recovered(self.root)
        self.assertTrue(recover(self.root))
        self.assert_previous_preserved()
        self.assertFalse(recover(self.root))

    def test_damaged_backup_preserves_pending_and_can_be_repaired(self):
        self.interrupt_process_during_update()
        backup = self.root / JOURNAL_NAME / "0.old"
        backup.write_bytes(b"broken")
        with self.assertRaisesRegex(RuntimeError, "破損"):
            recover(self.root)
        with self.assertRaises(RuntimeError):
            require_recovered(self.root)
        backup.write_bytes(self.original_individual)
        self.assertTrue(recover(self.root))
        self.assert_previous_preserved()

    def test_stale_update_cannot_replace_newer_master(self):
        master = self.root / self.master
        old_revision = revision(master)
        publish(self.root, [(master, b'{"newer":true}')], expected=(master, old_revision))
        with self.assertRaisesRegex(RuntimeError, "マスターが更新"):
            publish(self.root, [(master, b'{"stale":true}')], expected=(master, old_revision))
        self.assertEqual(master.read_bytes(), b'{"newer":true}')
