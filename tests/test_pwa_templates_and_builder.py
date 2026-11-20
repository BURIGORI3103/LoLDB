"""PWA テンプレート、変更履歴、単一 HTML の配布を合成データで検証する。"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import build_pwa
from data_transaction import JOURNAL_NAME
from pwa_builder import changelog
from pwa_builder.rendering import render_template
from pwa_builder.sources import safe_json_for_script


REPOSITORY = Path(__file__).resolve().parents[1]


class InlineAssets(HTMLParser):
    """HTML パーサーで実際の script と style の開始タグを拾う。"""

    def __init__(self):
        super().__init__()
        self.scripts = []
        self.styles = []
        self.in_script = False
        self.script_text = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))
            self.in_script = True
        elif tag == "style":
            self.styles.append(dict(attrs))

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.script_text.append(data)


class TemplateTests(unittest.TestCase):
    def test_replacement_uses_only_tokens_from_original_template(self):
        rendered = render_template(
            "__STYLES____APP_JS__ / __STYLES__",
            {"__STYLES__": "__APP_JS__", "__APP_JS__": "描画する"},
        )
        self.assertEqual(rendered, "__APP_JS__描画する / __APP_JS__")

    def test_missing_token_is_reported(self):
        with self.assertRaisesRegex(KeyError, "__UNKNOWN_SLOT__"):
            render_template("before __UNKNOWN_SLOT__ after", {})

    def test_inline_json_preserves_text_and_escapes_script_boundaries(self):
        data = {"description": "</script> & <要素> \u2028\u2029 __STYLES__ 日本語"}
        encoded = safe_json_for_script(data)
        self.assertEqual(json.loads(encoded), data)
        for unsafe in ("<", ">", "&", "\u2028", "\u2029"):
            self.assertNotIn(unsafe, encoded)
        self.assertIn("__STYLES__ 日本語", encoded)

    def test_javascript_sources_are_valid_standalone(self):
        for filename in ("pwa_templates/app.js", "ui_helpers.js", "service_worker_template.js"):
            with self.subTest(filename=filename):
                result = subprocess.run(
                    ["node", "--check", str(REPOSITORY / filename)],
                    capture_output=True, text=True, encoding="utf-8", timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


class BuilderFixtureTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.dist = self.root / "dist"
        self.dist.mkdir()
        self.merged = self.root / "merged_data"
        self.merged.mkdir()
        self.xo = self.root / "XO_Update_History.md"
        self.enterContext(patch.object(changelog, "XO_HISTORY_PATH", self.xo))
        self.enterContext(redirect_stdout(io.StringIO()))
        text = '__STYLES__ __APP_JS__ __CHAMPIONS_JSON__ __ITEMS_JSON__ </script> & "日本語"'
        self.champions = {"Fixture": {"id": "Fixture", "patch": "16.22.1", "description": text}}
        self.items = {"1001": {"id": "1001", "description": text}}
        self.write_json(self.merged / "all_champions.json", self.champions)
        self.write_json(self.merged / "all_items.json", self.items)
        (self.root / "UPDATE.md").write_text(
            "# アップデート（2026年11月18日 - v99.10.0 / 合成履歴）\n"
            "## 概要\n- ローカル注記 <要素> & __STYLES__\n",
            encoding="utf-8",
        )
        for name in ("ui_helpers.js", "service_worker_template.js"):
            shutil.copyfile(REPOSITORY / name, self.root / name)
        shutil.copytree(REPOSITORY / "pwa_templates", self.root / "pwa_templates")

    def write_json(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def artifact_paths(self):
        names = ("index.html", "sw.js", "manifest.json", ".nojekyll", "data/changelog_history.json")
        return [directory / name for directory in (self.root, self.dist) for name in names]

    def existing_artifacts(self):
        paths = [*self.artifact_paths(), self.root / "LoLDB_dist.zip"]
        for index, path in enumerate(paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"既存の配布物 {index}".encode("utf-8"))
        return {path: path.read_bytes() for path in paths}

    def test_changelog_prefers_local_and_sorts_versions_numerically(self):
        cache = self.root / "data/changelog_history.json"
        cache.parent.mkdir()
        self.write_json(cache, [
            {"version": "v99.10.0", "date": "2026-10-01", "items": ["古いキャッシュ"]},
            {"version": "v99.9.0", "date": "2026-10-02", "items": ["キャッシュ専用"]},
        ])
        xo_source = (
            "# 履歴\n"
            "### 📅 2026-10-03 | 📢 アップデート (v99.10.0)\n"
            "- 上書き対象\n"
            "### 📅 2026-10-04 | 📢 アップデート (v99.8.0)\n"
            "- XO 専用\n"
            "### 📅 2026-10-05 | 📢 アップデート (v0.1.0)\n"
            "- 除外対象\n"
        )
        self.xo.write_text(xo_source, encoding="utf-8")
        version, html = build_pwa.load_and_render_changelog(self.root, self.dist)
        history = json.loads(cache.read_text(encoding="utf-8"))
        self.assertEqual(version, "v99.10.0")
        self.assertEqual([entry["version"] for entry in history[:3]], ["v99.10.0", "v99.9.0", "v99.8.0"])
        self.assertEqual(history[0]["items"], ["ローカル注記 <要素> & __STYLES__"])
        self.assertIn("ローカル注記 &lt;要素&gt; &amp; __STYLES__", html)
        for expected in ("キャッシュ専用", "XO 専用"):
            self.assertIn(expected, html)
        for replaced in ("古いキャッシュ", "上書き対象", "除外対象"):
            self.assertNotIn(replaced, html)
        self.assertEqual(self.xo.read_text(encoding="utf-8"), xo_source)
        self.assertEqual(cache.read_bytes(), (self.dist / "data/changelog_history.json").read_bytes())

    def test_corrupted_changelog_cache_keeps_all_existing_artifacts(self):
        artifacts = self.existing_artifacts()
        cache = self.root / "data/changelog_history.json"
        for invalid in (b'[{"version":"v2', b'[{"version":"v98.1.0","items":null}]'):
            with self.subTest(invalid=invalid):
                cache.write_bytes(invalid)
                artifacts[cache] = invalid

                with self.assertRaisesRegex(ValueError, "changelog_history.json"):
                    build_pwa.build(self.root)

                self.assertEqual({path: path.read_bytes() for path in artifacts}, artifacts)

    def test_complete_build_embeds_data_and_creates_matching_distribution_zip(self):
        (self.dist / "icon.png").write_bytes(b"synthetic logo")
        build_pwa.build(self.root)
        for relative in ("index.html", "sw.js", "manifest.json", "data/changelog_history.json", ".nojekyll"):
            with self.subTest(relative=relative):
                self.assertEqual((self.root / relative).read_bytes(), (self.dist / relative).read_bytes())

        html_path = self.dist / "index.html"
        html = html_path.read_text(encoding="utf-8")
        self.assertIn("Patch 16.22 / v99.10.0", html)
        self.assertIn("ローカル注記 &lt;要素&gt; &amp; __STYLES__", html)
        parsed = InlineAssets()
        parsed.feed(html)
        parsed.close()
        self.assertEqual(parsed.styles, [{}])
        self.assertEqual(parsed.scripts, [{}])
        script = "".join(parsed.script_text)
        for declaration, expected in (("CHAMPIONS", self.champions), ("ITEMS", self.items)):
            with self.subTest(declaration=declaration):
                match = re.search(rf"^\s*const {declaration} = (.+);$", script, re.MULTILINE)
                self.assertIsNotNone(match)
                self.assertEqual(json.loads(match[1]), expected)
        checked = subprocess.run(
            ["node", "--check"], input=script, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)

        html_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()
        service_worker = (self.dist / "sw.js").read_text(encoding="utf-8")
        self.assertIn(f"const HTML_HASH = '{html_hash}';", service_worker)
        self.assertIn(f"const CORE_CACHE = 'loldb-core-v99.10.0-{html_hash[:8]}';", service_worker)
        manifest = json.loads((self.dist / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["start_url"], manifest["display"]), ("./index.html", "standalone"))
        self.assertEqual([icon["src"] for icon in manifest["icons"]], ["./icon.png", "./icon-512.png"])

        with ZipFile(self.root / "LoLDB_dist.zip") as archive:
            expected = {"index.html", "sw.js", "manifest.json", "icon.png", "data/changelog_history.json", ".nojekyll"}
            self.assertCountEqual(archive.namelist(), expected)
            for name in expected:
                self.assertEqual(archive.read(name), (self.dist / name).read_bytes())

    def test_broken_or_wrong_shape_sources_keep_all_existing_artifacts(self):
        artifacts = self.existing_artifacts()
        for name in ("all_champions.json", "all_items.json"):
            source = self.merged / name
            original = source.read_bytes()
            for invalid in (b"{invalid", b"[]", b"{}", b"\xff"):
                with self.subTest(source=name, invalid=invalid):
                    source.write_bytes(invalid)
                    with self.assertRaises(SystemExit) as failure:
                        build_pwa.build(self.root)
                    self.assertNotEqual(failure.exception.code, 0)
                    self.assertEqual({path: path.read_bytes() for path in artifacts}, artifacts)
            source.write_bytes(original)

    def test_pending_transaction_blocks_build_without_changing_distribution(self):
        artifacts = self.existing_artifacts()
        journal = self.root / JOURNAL_NAME
        journal.mkdir()
        (journal / "pending.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "--recover"):
            build_pwa.build(self.root)
        self.assertEqual({path: path.read_bytes() for path in artifacts}, artifacts)

    def test_staged_update_uses_proposed_version_and_leaves_real_outputs_untouched(self):
        artifacts = self.existing_artifacts()
        history = self.root / "data/changelog_history.json"
        self.write_json(history, [])
        artifacts[history] = history.read_bytes()
        update = self.root / "UPDATE.md"
        artifacts[update] = update.read_bytes()
        proposed = self.root / "proposed.md"
        proposed.write_text(
            "# アップデート（2026年11月19日 - v99.20.0 / 新版）\n\n## 概要\n- 新しい記録\n",
            encoding="utf-8",
        )
        self.xo.write_text(
            "### 📅 2026-11-19 | 📢 アップデート (v99.19.0)\n"
            "# アップデート（2026年11月19日 - v99.19.0 / 旧履歴）\n\n## 概要\n- XO にある前回の記録\n",
            encoding="utf-8",
        )
        (self.dist / "icon.png").write_bytes(b"synthetic logo")
        (self.dist / "work-in-progress.md").write_text("配布対象外", encoding="utf-8")
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

        build_pwa.stage_update(self.root, stage, proposed, "v99.20.0")

        publication = json.loads((stage / "publication.json").read_text(encoding="utf-8"))
        expected_outputs = [path.relative_to(self.root).as_posix() for path in artifacts if path != update]
        self.assertCountEqual(publication, expected_outputs)
        self.assertTrue(all((stage / path).is_file() for path in publication))
        inputs = json.loads((stage / "publication_inputs.json").read_text(encoding="utf-8"))
        app_js = self.root / "pwa_templates/app.js"
        self.assertEqual(inputs["pwa_templates/app.js"], hashlib.sha256(app_js.read_bytes()).hexdigest())
        self.assertIsNone(inputs["dist/icon-512.png"])
        self.assertNotIn("dist/work-in-progress.md", inputs)
        html = (stage / "index.html").read_text(encoding="utf-8")
        self.assertIn("Patch 16.22 / v99.20.0", html)
        self.assertIn("XO にある前回の記録", html)
        with ZipFile(stage / "LoLDB_dist.zip") as archive:
            self.assertEqual(archive.read("icon.png"), b"synthetic logo")
            self.assertNotIn("work-in-progress.md", archive.namelist())
        self.assertEqual({path: path.read_bytes() for path in artifacts}, artifacts)

    def test_staged_update_refuses_an_unexpected_version_and_keeps_real_artifacts(self):
        artifacts = self.existing_artifacts()
        history = self.root / "data/changelog_history.json"
        self.write_json(history, [])
        artifacts[history] = history.read_bytes()
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

        with self.assertRaisesRegex(ValueError, "v99.20.0.*v99.10.0"):
            build_pwa.stage_update(self.root, stage, self.root / "UPDATE.md", "v99.20.0")

        self.assertFalse((stage / "publication.json").exists())
        self.assertEqual({path: path.read_bytes() for path in artifacts}, artifacts)

    def test_staged_update_rejects_an_older_proposal_than_the_changelog(self):
        history = self.root / "data/changelog_history.json"
        history.parent.mkdir()
        self.write_json(history, [{"version": "v99.20.0", "items": ["新しい記録"]}])
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

        with self.assertRaisesRegex(ValueError, "v99.10.0.*v99.20.0"):
            build_pwa.stage_update(self.root, stage, self.root / "UPDATE.md", "v99.10.0")

        self.assertFalse((stage / "publication.json").exists())

    def test_staged_update_checks_the_source_data_transaction(self):
        journal = self.root / JOURNAL_NAME
        journal.mkdir()
        (journal / "pending.json").write_text("[]", encoding="utf-8")
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()

        with self.assertRaisesRegex(RuntimeError, "--recover"):
            build_pwa.stage_update(self.root, stage, self.root / "UPDATE.md", "v99.10.0")

        self.assertEqual(list(stage.iterdir()), [])

    def test_staged_update_rejects_modified_inputs_during_build(self):
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        original_build = build_pwa.build

        def change_source_while_building(*args, **kwargs):
            original_build(*args, **kwargs)
            (self.merged / "all_items.json").write_text("{}", encoding="utf-8")

        with patch.object(build_pwa, "build", side_effect=change_source_while_building):
            with self.assertRaisesRegex(RuntimeError, "元の入力が変更"):
                build_pwa.stage_update(self.root, stage, self.root / "UPDATE.md", "v99.10.0")

        self.assertFalse((stage / "publication.json").exists())

    def test_staged_update_rejects_a_linked_asset_directory(self):
        stage = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        source = self.root / "linked-assets"
        source.mkdir()
        (source / "icon.png").write_bytes(b"outside artifact")
        self.dist.rmdir()
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(self.dist), str(source)], check=True, capture_output=True)
        else:
            self.dist.symlink_to(source, target_is_directory=True)

        with self.assertRaisesRegex(ValueError, "リンクを使用できません"):
            build_pwa.stage_update(self.root, stage, self.root / "UPDATE.md", "v99.10.0")

        self.assertFalse((stage / "publication.json").exists())
