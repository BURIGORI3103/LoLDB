"""合成入力で取得・検証・JSON更新の境界を検証する。"""

import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import chdir, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import call, patch

import data_transaction as transaction
import fetch_champions as champions
import generate_all_items as items
import verify_patch_data as validator


def json_response(value):
    return io.BytesIO(json.dumps(value, ensure_ascii=False).encode("utf-8"))


class PipelineTemporaryFiles(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.stdout = self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))

    def write_json(self, relative_path, value):
        (self.root / relative_path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def read_json(self, relative_path):
        return json.loads((self.root / relative_path).read_text(encoding="utf-8"))


class DataDragonFixtureTests(PipelineTemporaryFiles):
    def setUp(self):
        super().setUp()
        self.enterContext(chdir(self.root))
        (self.root / "merged_data").mkdir()

    def test_item_catalog_selects_supported_items_and_keeps_valid_recipe_ids(self):
        self.write_json("merged_data/all_champions.json", {
            "A": {"name": "試作家", "role_data": {"TOP": {"build": {"core": [{"item_id": "1003"}]}}}},
        })
        raw_items = {
            "1001": {
                "name": "試作ブーツ", "maps": {"11": True}, "tags": ["Boots"],
                "description": "<stats><b>攻撃力</b> 25<br>移動速度 -5</stats>"
                               "<passive>加速</passive><p>速度が上がる。</p>",
                "into": ["1002", "1105", "100001"],
            },
            "1002": {
                "name": "試作完成品", "maps": {"11": True}, "inStore": False, "specialRecipe": 1001,
                "stats": {"PercentAttackSpeedMod": 0.125}, "from": ["1001", "1105"],
            },
            "1003": {"name": "参照あり", "maps": {"11": True}, "inStore": False},
            "1004": {"name": "参照なし", "maps": {"11": True}, "inStore": False},
            "1005": {"name": "専用品", "maps": {"11": True}, "inStore": False, "requiredChampion": "A"},
            "1006": {"name": "専用品", "maps": {"11": True}, "requiredChampion": "B"},
            "1105": {"name": "内部ペット", "maps": {"11": True}},
            "100001": {"name": "モード別クローン", "maps": {"11": True}},
            "2001": {"name": "別マップ", "maps": {"12": True}},
        }
        with patch.object(items.urllib.request, "urlopen", side_effect=[
            json_response(["99.99.1"]), json_response({"data": raw_items}),
        ]) as urlopen:
            items.main(patch="16.22.1")
        self.assertEqual(urlopen.call_count, 2)
        self.assertTrue(urlopen.call_args_list[0].args[0].endswith("/api/versions.json"))
        self.assertTrue(urlopen.call_args_list[1].args[0].full_url.endswith("/16.22.1/data/ja_JP/item.json"))
        # 応答が止まっても無期限に待たないよう、両方の取得に期限を渡す。
        self.assertEqual(
            [request.kwargs.get("timeout") for request in urlopen.call_args_list],
            [items.FETCH_TIMEOUT_SECONDS] * 2,
        )
        catalog = self.read_json("merged_data/all_items.json")
        self.assertEqual(set(catalog), {"1001", "1002", "1003", "1005", "1006"})
        self.assertEqual({entry["patch"] for entry in catalog.values()}, {"16.22.1"})
        self.assertEqual(catalog["1001"]["categories"], ["AD", "BOOTS"])
        self.assertEqual(catalog["1001"]["stats_list"], ["攻撃力 +25", "移動速度 -5"])
        self.assertEqual(catalog["1001"]["description"], "【自動効果: 加速】\n速度が上がる。")
        self.assertEqual(catalog["1001"]["into"], ["1002"])
        self.assertEqual(catalog["1002"]["from"], ["1001"])
        self.assertEqual(catalog["1002"]["stats_summary"], "攻撃速度 +12%")
        self.assertEqual(catalog["1005"]["display_name"], "専用品（試作家専用）")
        self.assertEqual(catalog["1006"]["display_name"], "専用品（B専用）")

    def test_duplicate_generic_item_names_leave_existing_catalog_untouched(self):
        output = self.root / "merged_data/all_items.json"
        original = b'{"previous":true}'
        output.write_bytes(original)
        duplicate = {"name": "汎用装備", "maps": {"11": True}}
        with patch.object(items.urllib.request, "urlopen", side_effect=[
            json_response(["16.22.1"]), json_response({"data": {"1001": duplicate, "1002": duplicate}}),
        ]):
            with self.assertRaisesRegex(ValueError, "通常アイテム名が重複"):
                items.main()
        self.assertEqual(output.read_bytes(), original)

    def test_champion_fetch_saves_official_fields_and_normalizes_descriptions(self):
        spell = {
            "name": "試作技", "description": "ダメージ<br>続き<script>除外</script>",
            "cooldownBurn": "8/7", "costBurn": "25", "image": {"full": "fixture-spell.png"},
        }
        raw = {
            "id": "Fixture", "key": "999", "name": "試作チャンピオン", "title": "テスト用",
            "tags": ["Mage"], "partype": "Mana", "stats": {"attackrange": 250},
            "passive": {"name": "固有", "description": "<b>体力</b>&amp;マナ", "image": {"full": "fixture.png"}},
            "spells": [spell] * 5,
        }
        with patch.object(champions.urllib.request, "urlopen", side_effect=[
            json_response(["99.1.1"]), json_response({"data": {"Fixture": raw}}),
        ]) as urlopen:
            champions.fetch_lol_data(patch="16.22.1")
        self.assertEqual(urlopen.call_count, 2)
        version, detail = urlopen.call_args_list
        self.assertTrue(version.args[0].full_url.endswith("/api/versions.json"))
        self.assertTrue(detail.args[0].full_url.endswith("/16.22.1/data/ja_JP/championFull.json"))
        self.assertEqual([call.kwargs for call in (version, detail)], [{"timeout": 15}, {"timeout": 15}])
        self.assertEqual(list((self.root / "champions_data").iterdir()), [
            self.root / "champions_data/Fixture.json",
        ])
        record = self.read_json("champions_data/Fixture.json")
        self.assertEqual((record["patch"], record["stats"], record["roles"]), ("16.22.1", raw["stats"], ["Mage"]))
        self.assertEqual(record["abilities"], [{
            "slot": "Passive", "name": "固有", "description": "体力&マナ", "image": "fixture.png",
        }])
        self.assertEqual([entry["slot"] for entry in record["spells"]], ["Q", "W", "E", "R", "Skill_5"])
        self.assertEqual(record["spells"][0], {
            "slot": "Q", "name": "試作技", "description": "ダメージ\n続き",
            "cooldown": "8/7", "cost": "25", "image": "fixture-spell.png",
        })


class PatchVerificationTests(PipelineTemporaryFiles):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(validator, "BASE", self.root))
        for directory in ("merged_data", "champions_data", "docs", "dist"):
            (self.root / directory).mkdir()
        self.matchup = {
            "patch": "16.22.1", "role": "TOP", "source": "opgg_stats",
            "is_estimated": False, "champion_id": "Opponent",
        }
        self.champions = {}
        for champion in ("Fixture", "Opponent"):
            matchups = {"Opponent": self.matchup} if champion == "Fixture" else {}
            self.champions[champion] = {
                "patch": "16.22.1",
                "wiki_info": {"status": "success"},
                "opgg_source": {"patch": "16.22", "patch_verified": True},
                "roles": ["TOP"],
                "role_data": {"TOP": {
                    "opgg_source": {"role": "TOP", "patch": "16.22", "patch_verified": True},
                    "runes": {"primary": {"keystone": "試作"}},
                    "build": {"core": [{"item_id": "1001"}]},
                }},
                "matchup_matrix_by_role": {"TOP": matchups},
                **dict.fromkeys(("attack_type", "damage_profile", "sustain_info", "combos", "skill_matrix")),
            }
            self.write_json(f"champions_data/{champion}.json", {"patch": "16.22.1"})
        self.save_champions()
        self.write_json("merged_data/all_items.json", {"1001": {}})
        self.checklist = self.root / "docs/LoL_URL_list.md"
        self.checklist.write_text("- [x] Fixture\n- [x] Opponent\n", encoding="utf-8")
        self.scripts = ('const patch = "16.22";', 'const roles = ["TOP"];')
        self.html = (
            f"Patch 16.22 wikiの考察・対策<script>{self.scripts[0]}</script>"
            f'<script type="text/javascript">{self.scripts[1]}</script>'
        )
        for path in ("index.html", "dist/index.html"):
            (self.root / path).write_text(self.html, encoding="utf-8")
        self.report = self.root / "docs/data_refresh_report.json"
        self.javascript = self.enterContext(patch.object(validator.subprocess, "run"))

    def save_champions(self):
        self.write_json("merged_data/all_champions.json", self.champions)
        for name, champion in self.champions.items():
            self.write_json(f"merged_data/{name}.json", champion)

    def test_check_does_not_write_report_and_checks_each_inline_script(self):
        first_report = b'{"previous":true}'
        self.report.write_bytes(first_report)
        validator.run(write_report=False)
        self.assertEqual(self.report.read_bytes(), first_report)
        self.assertEqual(self.javascript.call_args_list, [
            call(["node", "--check"], input=script, text=True, encoding="utf-8", check=True, capture_output=True)
            for script in self.scripts
        ])
        report = json.loads(self.stdout.getvalue())
        self.assertEqual(
            {key: report[key] for key in ("champions", "roles", "items", "wiki_success", "measured_matchup_pairs")},
            {"champions": 2, "roles": 2, "items": 1, "wiki_success": 2, "measured_matchup_pairs": 1},
        )

    def test_successful_run_writes_the_verified_report(self):
        validator.run()
        self.assertEqual(json.loads(self.stdout.getvalue()), json.loads(self.report.read_text(encoding="utf-8")))

    def test_invalid_node_script_does_not_publish_a_report(self):
        self.javascript.side_effect = subprocess.CalledProcessError(1, ["node", "--check"])
        with self.assertRaises(subprocess.CalledProcessError):
            validator.run()
        self.assertFalse(self.report.exists())

    def test_rejects_unmeasured_mismatched_or_unknown_matchups(self):
        for field, invalid, error in [
            ("role", "MID", "対面のパッチかロールが不一致"),
            ("patch", "16.21.1", "対面のパッチかロールが不一致"),
            ("is_estimated", True, "実測統計でない"),
            ("source", "synergy_estimate", "実測統計でない"),
            ("champion_id", "Unknown", "対面相手が未登録"),
        ]:
            with self.subTest(field=field), patch.dict(self.matchup, {field: invalid}):
                self.save_champions()
                with self.assertRaisesRegex(ValueError, error):
                    validator.run(write_report=False)
        self.javascript.assert_not_called()
        self.assertFalse(self.report.exists())

    def test_rejects_unknown_core_item_before_rendered_html_checks(self):
        self.write_json("merged_data/all_items.json", {})
        with self.assertRaisesRegex(ValueError, "アイテム辞書に未登録"):
            validator.run(write_report=False)
        self.javascript.assert_not_called()

    def test_rejects_incomplete_urls_and_mismatched_published_html(self):
        self.checklist.write_text("- [x] Fixture\n- [ ] Opponent\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "URLの取得チェックが未完了"):
            validator.run(write_report=False)
        self.checklist.write_text("- [x] Fixture\n- [x] Opponent\n", encoding="utf-8")
        (self.root / "dist/index.html").write_text(self.html + "差分", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ルートとdistのHTMLが不一致"):
            validator.run(write_report=False)
        self.javascript.assert_not_called()


class TransactionDetailTests(PipelineTemporaryFiles):
    def setUp(self):
        super().setUp()
        self.merged = self.root / "merged_data"
        self.merged.mkdir()
        self.target = self.merged / "Fixture.json"
        self.journal = self.root / transaction.JOURNAL_NAME

    def test_utf8_json_content_and_revision_track_exact_file_bytes(self):
        self.assertIsNone(transaction.revision(self.target))
        body = transaction.json_bytes({"名前": "試作"})
        self.assertEqual(body, '{\n  "名前": "試作"\n}'.encode("utf-8"))
        with_newline = transaction.json_bytes({"名前": "試作"}, trailing_newline=True)
        self.assertEqual(with_newline, body + b"\n")
        self.target.write_bytes(with_newline)
        self.assertEqual(transaction.revision(self.target), hashlib.sha256(with_newline).hexdigest())

    def test_lock_rejects_second_writer_and_is_released_on_error(self):
        with self.assertRaisesRegex(RuntimeError, "書き込み中断"):
            with transaction.update_lock(self.root):
                with self.assertRaises(OSError):
                    with transaction.update_lock(self.root):
                        self.fail("二重ロックを取得した")
                raise RuntimeError("書き込み中断")
        with transaction.update_lock(self.root):
            self.assertTrue((self.root / transaction.LOCK_NAME).is_file())

    def test_duplicate_or_invalid_targets_leave_files_intact_and_staging_recoverable(self):
        original = b'{"original":true}'
        self.target.write_bytes(original)
        for update, error in [
            ([(self.target, b"{}"), (self.target, b"{}")], "パスが重複"),
            ([(self.root / "index.html", b"{}")], "JSONパスが不正"),
            ([(self.merged / "subdir" / "Fixture.json", b"{}")], "JSONパスが不正"),
        ]:
            with self.subTest(update=update):
                with self.assertRaisesRegex(ValueError, error):
                    transaction.publish(self.root, update)
                self.assertEqual(self.target.read_bytes(), original)
                self.assertFalse((self.root / "index.html").exists())
                transaction.require_recovered(self.root)
                self.assertFalse(transaction.recover(self.root))
                self.assertFalse(self.journal.exists())

    def test_recovery_refuses_an_external_edit_and_preserves_pending_journal(self):
        old, published, external = b'{"old":true}', b'{"published":true}', b'{"external":true}'
        self.journal.mkdir()
        (self.journal / "0.old").write_bytes(old)
        self.write_json(f"{transaction.JOURNAL_NAME}/pending.json", [[
            "merged_data/Fixture.json", hashlib.sha256(old).hexdigest(), hashlib.sha256(published).hexdigest(),
        ]])
        self.target.write_bytes(external)
        with self.assertRaisesRegex(RuntimeError, "別の変更を検出"):
            transaction.recover(self.root)
        self.assertEqual(self.target.read_bytes(), external)
        with self.assertRaisesRegex(RuntimeError, "--recover"):
            transaction.require_recovered(self.root)
        self.target.write_bytes(published)
        self.assertTrue(transaction.recover(self.root))
        self.assertEqual(self.target.read_bytes(), old)
        self.assertFalse(self.journal.exists())
