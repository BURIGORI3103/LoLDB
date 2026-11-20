"""合成データでチャンピオン・アイテムの補完と移転配布物を検証する。"""

import io
import json
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import build_migration_package as migration
import enhance_items_data as items
import update_champion_attack_types as attack
import update_champion_damage_types as damage
import update_champion_sustain as sustain


class ChampionEnricherTests(unittest.TestCase):
    def test_attack_range_boundary_and_default(self):
        cases = [(250, "MELEE"), (251, "RANGED")]
        for attack_range, expected in cases:
            with self.subTest(attack_range=attack_range):
                result = attack.determine_attack_type("Fixture", {"stats": {"attackrange": attack_range}})
                self.assertEqual((result["type"], result["range"]), (expected, attack_range))
        default = attack.determine_attack_type("Fixture", {})
        self.assertEqual((default["type"], default["range"]), ("MELEE", 175))

    def test_five_hybrid_champions_keep_form_metadata_and_official_range(self):
        forms = {
            "Jayce": (125, 500),
            "Nidalee": (525, 125),
            "Elise": (550, 125),
            "Gnar": (175, 175),
            "Kayle": (175, 525),
        }
        self.assertEqual(set(attack.HYBRID_SPECIAL_CHAMPIONS), forms.keys())
        for champion, expected in forms.items():
            with self.subTest(champion=champion):
                first = attack.determine_attack_type(champion, {"stats": {"attackrange": 250}})
                second = attack.determine_attack_type(champion, {"stats": {"attackrange": 251}})
                self.assertEqual((first["base_range"], first["alt_range"]), expected)
                self.assertEqual((first["type"], first["range"]), ("HYBRID", 250))
                self.assertEqual((second["type"], second["range"]), ("HYBRID", 251))

    def test_damage_profile_covers_damage_types_and_dual_precedence(self):
        cases = {
            "Fixture": ("AD", "badge-ad", "AR", False),
            "Lux": ("AP", "badge-ap", "MR", False),
            "Leona": ("TANK", "badge-tank", "MR", False),
            "Sion": ("TANK", "badge-tank", "AR", False),
            "Nami": ("AP", "badge-ap", "MR", False),
            "Malphite": ("TANK", "badge-hybrid", "MR", True),
            "Volibear": ("HYBRID", "badge-hybrid", "AR", True),
            "Jax": ("HYBRID", "badge-hybrid", "AR", True),
            "Katarina": ("HYBRID", "badge-hybrid", "AR", True),
        }
        for champion, expected in cases.items():
            with self.subTest(champion=champion):
                primary, badge, defense, has_dual = expected
                profile = damage.get_damage_profile(champion, {})
                self.assertEqual(profile["primary_type"], primary)
                self.assertEqual(profile["badge_class"], badge)
                self.assertIn(defense, profile["counter_defense"])
                self.assertIs(profile["has_dual_build"], has_dual)
                self.assertIs(bool(profile["dual_build_desc"]), has_dual)

    def test_sustain_uses_passive_and_spells_with_false_positives_excluded(self):
        champion = {
            "abilities": [{"name": "固有能力", "description": "<b>自身の体力</b>を回復する。"}],
            "spells": [
                {"slot": "Q", "name": "重傷", "description": "敵の体力回復量が低下する。"},
                {"slot": "W", "name": "マナ", "description": "自身のマナを回復する。"},
                {"slot": "E", "name": "味方の保護", "description": "味方からシールドを受ける。"},
                {"slot": "R", "name": "防壁", "description": "シールドを獲得する。"},
            ],
        }
        result = sustain.analyze_champion_sustain("Fixture", champion)
        self.assertEqual(result["type"], "BOTH")
        self.assertEqual(result["heal_skills"], ["固有能力"])
        self.assertEqual(result["shield_skills"], ["防壁"])


class EnricherPublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.merged = self.root / "merged_data"
        self.merged.mkdir()
        self.master = self.merged / "all_champions.json"
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(redirect_stderr(io.StringIO()))

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def read_json(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_attack_type_is_synchronized_to_roles_and_individual(self):
        champion = {
            "id": "Fixture",
            "stats": {"attackrange": 251},
            "role_data": {"TOP": {"note": "既存情報"}, "MID": {}},
        }
        self.write_json(self.master, {"Fixture": champion})
        with patch.multiple(attack, MERGED_JSON=self.master, MERGED_DIR=self.merged):
            attack.main()
        updated = self.read_json(self.master)["Fixture"]
        self.assertEqual(updated, self.read_json(self.merged / "Fixture.json"))
        self.assertEqual(updated["attack_type"]["type"], "RANGED")
        for role in updated["role_data"].values():
            self.assertEqual(role["attack_type"], updated["attack_type"])
        self.assertEqual(updated["role_data"]["TOP"]["note"], "既存情報")
        self.assertEqual(updated["stats"], champion["stats"])

    def test_damage_profile_normalizes_builds_and_writes_matching_individual(self):
        champion = {
            "id": "Malphite",
            "patch": "16.22.1",
            "stats": {"attackrange": 125},
            "roles": ["TOP"],
            "role_data": {"TOP": {"build_patterns": [{"name": "[AP] 既存ビルド"}]}},
        }
        self.write_json(self.master, {"Malphite": champion})
        with patch.multiple(damage, MERGED_JSON=self.master, __file__=str(self.root / "entry.py")):
            damage.main()
        updated = self.read_json(self.master)["Malphite"]
        self.assertEqual(updated, self.read_json(self.merged / "Malphite.json"))
        self.assertEqual(updated["damage_profile"]["primary_type"], "TANK")
        self.assertEqual(updated["build_patterns"][0]["name"], "[TANK] 既存ビルド")
        self.assertEqual(updated["build_patterns"], updated["role_data"]["TOP"]["build_patterns"])
        self.assertEqual((updated["patch"], updated["stats"]), (champion["patch"], champion["stats"]))

    def test_sustain_is_synchronized_without_discarding_individual_fields(self):
        champion = {
            "id": "Fixture",
            "spells": [{"slot": "Q", "name": "回復", "description": "自身の体力を回復する。"}],
        }
        individual = self.merged / "Fixture.json"
        self.write_json(self.master, {"Fixture": champion})
        self.write_json(individual, {**champion, "note": "個別の保存項目"})
        with patch.multiple(sustain, MERGED_JSON=self.master, MERGED_DIR=self.merged):
            sustain.main()
        updated = self.read_json(self.master)["Fixture"]
        self.assertEqual(updated["sustain_info"]["type"], "HEAL")
        self.assertEqual(self.read_json(individual), {**updated, "note": "個別の保存項目"})

    @unittest.skipUnless(sys.platform == "win32", "Windows の読み取り専用属性を検証します")
    def test_read_only_individual_leaves_all_enrichment_outputs_unchanged(self):
        champions = {
            name: {"id": name, "patch": "16.22.1", "stats": {"attackrange": 175}}
            for name in ("FixtureA", "FixtureB")
        }
        first = self.merged / "FixtureA.json"
        protected = self.merged / "FixtureB.json"
        cases = (
            (attack, {"MERGED_DIR": self.merged}),
            (damage, {"__file__": str(self.root / "entry.py")}),
            (sustain, {"MERGED_DIR": self.merged}),
        )
        for module, paths in cases:
            with self.subTest(enricher=module.__name__):
                self.write_json(self.master, champions)
                self.write_json(first, champions["FixtureA"])
                self.write_json(protected, champions["FixtureB"])
                before = {path: path.read_bytes() for path in (self.master, first, protected)}
                protected.chmod(stat.S_IREAD)
                try:
                    with patch.multiple(module, MERGED_JSON=self.master, **paths), self.assertRaises(PermissionError):
                        module.main()
                    self.assertEqual({path: path.read_bytes() for path in before}, before)
                finally:
                    protected.chmod(stat.S_IWRITE)

    def test_item_enrichment_normalizes_startup_categories_idempotently(self):
        path = self.merged / "all_items.json"
        self.write_json(path, {
            "1055": {"categories": "AD", "stats": {"FlatPhysicalDamageMod": 10}},
            "9991": {"name": "ドランの試作品", "categories": ["TANK", "STARTUP"]},
            "9992": {"plaintext": "初期装備"},
            "9993": {"categories": ["AP"]},
        })
        with patch.object(items, "ITEMS_JSON", path):
            items.main()
            first = path.read_bytes()
            items.main()
        self.assertEqual(path.read_bytes(), first)
        processed = self.read_json(path)
        self.assertEqual(processed["1055"]["categories"], ["AD", "STARTUP"])
        self.assertEqual(processed["1055"]["stat_tags"], ["AD"])
        self.assertEqual(processed["9991"]["categories"], ["TANK", "STARTUP"])
        self.assertEqual(processed["9992"]["categories"], ["STARTUP"])
        self.assertEqual(processed["9993"]["categories"], ["AP"])


class ItemTagTests(unittest.TestCase):
    def test_sources_contribute_sorted_unique_tags(self):
        source = {
            "stats": {"FlatPhysicalDamageMod": 10, "PercentAttackSpeedMod": 0.1, "FlatArmorMod": 4},
            "stats_summary": "攻撃力 +10、魔力 +20、魔法耐性 +8、体力 +30、マナ +12",
            "description": "Ability Haste、Critical Strike、移動速度、脅威、Magic Penetration、吸血、基本体力回復",
        }
        self.assertEqual(items.analyze_stat_tags(source), [
            "AD", "AH", "AP", "AR", "AS", "CRIT", "HP", "HPREGEN", "LETHALITY",
            "MAGICPEN", "MANA", "MR", "MS", "VAMP",
        ])
        self.assertEqual(items.analyze_stat_tags({"stats": None, "stats_summary": None, "description": None}), [])


class MigrationPackageTests(unittest.TestCase):
    def test_redirect_and_cleanup_files_are_packaged_with_available_assets(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        dist = root / "dist"
        output = root / "dist_old_url_migration"
        desktop = root / "desktop"
        dist.mkdir()
        desktop.mkdir()
        output.mkdir()
        (output / "stale.txt").write_bytes(b"old")
        (dist / "icon.png").write_bytes(b"icon")
        (dist / "manifest.json").write_bytes(b'{"name":"fixture"}')
        before = {path.name: path.read_bytes() for path in dist.iterdir()}
        url = "https://example.invalid/loldb/"
        with patch.multiple(
            migration, BASE_DIR=root, DIST_DIR=dist, MIGRATION_DIR=output, DESKTOP_DIR=desktop, NEW_URL=url,
        ):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                migration.build_migration_package()

        self.assertFalse((output / "stale.txt").exists())
        self.assertEqual(list(desktop.iterdir()), [])
        self.assertEqual({path.name: path.read_bytes() for path in dist.iterdir()}, before)
        html = (output / "index.html").read_text(encoding="utf-8")
        sw = (output / "sw.js").read_text(encoding="utf-8")
        self.assertIn(f'href="{url}"', html)
        self.assertIn(f'window.location.replace("{url}")', html)
        self.assertIn("self.registration.unregister()", sw)
        self.assertIn(f"client.navigate('{url}')", sw)
        with ZipFile(root / "LoLDB_old_url_migration.zip") as archive:
            expected = sorted(["index.html", "sw.js", *before])
            self.assertEqual(sorted(archive.namelist()), expected)
            for name in expected:
                self.assertEqual(archive.read(name), (output / name).read_bytes())
