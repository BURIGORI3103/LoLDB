"""統合マスターデータを埋め込んだオフライン PWA を生成する。"""

import argparse
import hashlib
import json
import re
import stat
from pathlib import Path

from tqdm import tqdm

from audit_normalization import project_for_display
from data_transaction import PWA_OUTPUT_FILES as _PUBLICATION_FILES, require_recovered, update_lock
from pwa_builder import changelog
from pwa_builder.changelog import (
    CURATED_CHANGELOG_ITEMS as CURATED_CHANGELOG_ITEMS,
    VERSION_ICONS as VERSION_ICONS,
    _parse_markdown_update_block as _parse_markdown_update_block,
    _parse_version_tuple as _parse_version_tuple,
    load_and_render_changelog as load_and_render_changelog,
    prepare_changelog,
)
from pwa_builder.packager import write_distribution_locked
from pwa_builder.rendering import render_page
from pwa_builder.sources import _load_required_source, validate_catalog_patches


_STAGED_INPUTS = (
    "merged_data/all_champions.json",
    "merged_data/all_items.json",
    "ui_helpers.js",
    "service_worker_template.js",
    "pwa_templates/app.js",
    "pwa_templates/index.html.tmpl",
    "pwa_templates/styles.css",
)
_OPTIONAL_STAGED_INPUTS = ("data/changelog_history.json", "dist/icon.png", "dist/icon-512.png")


def _require_no_pending_xo_install(base_dir: Path) -> None:
    """XOが中断した配布の再開用ファイルを通常ビルドで上書きしない。"""
    state_path = base_dir.parent / "XObsidian/System_Inbox/.add_update/LoLDB/pending/state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return
    if (state["directory"] == str(base_dir)
            and state["next"] in {"contexts", "install", "project_commit", "project_push"}):
        raise RuntimeError("XOの配布処理が中断しています。先に add_update.py --project LoLDB --resume を実行してください。")


def build(
    base_dir: Path | None = None,
    *,
    expected_version: str | None = None,
    xo_history_text: str | None = None,
    template_dir: Path | None = None,
) -> None:
    """指定ディレクトリの正本と更新履歴から PWA の配布物を生成する。"""
    base_dir = Path(base_dir).resolve() if base_dir is not None else Path(__file__).resolve().parent
    with update_lock(base_dir):
        require_recovered(base_dir)
        _require_no_pending_xo_install(base_dir)
        master_file = base_dir / "merged_data" / "all_champions.json"
        items_file = base_dir / "merged_data" / "all_items.json"

        # 両方の正本を配布物へ書き込む前に検証する（欠損時に空の ITEMS で上書きしたり、正常終了したりしない）
        print("マスターデータを読み込み中...")
        all_champs = _load_required_source(master_file, "マスターデータファイル")
        print("アイテムデータを読み込み中...")
        all_items = _load_required_source(items_file, "アイテムデータファイル")
        print(f"合計 {len(all_items)} 件のアイテムデータを読み込みました。")

        print(f"合計 {len(all_champs)} 体のチャンピオンデータを読み込みました。")
        build_patch = validate_catalog_patches(all_champs, all_items)
        dist_dir = base_dir / "dist"
        short_patch = ".".join(build_patch.split(".")[:2])
        latest_version, changelog_items_html, changelog_history = prepare_changelog(base_dir, xo_history_text=xo_history_text)
        if not re.fullmatch(r"v\d+\.\d+\.\d+", latest_version):
            raise ValueError("生成対象のバージョンが不正です")
        if expected_version is not None and latest_version != expected_version:
            raise ValueError(f"指定版 {expected_version} と生成版 {latest_version} が一致しません")
        print(f"最新バージョン検出: {latest_version} (Patch {short_patch})")

        # 廃止したシミュレーター専用の対面マトリクスは配布 HTML へ含めない。
        display_champs = project_for_display(all_champs)
        ui_helpers = (base_dir / "ui_helpers.js").read_text(encoding="utf-8")
        html_content = render_page(
            build_patch=build_patch,
            short_patch=short_patch,
            latest_version=latest_version,
            changelog_items_html=changelog_items_html,
            champions=display_champs,
            items=all_items,
            ui_helpers=ui_helpers,
            template_dir=template_dir,
        )

        write_distribution_locked(
            base_dir, dist_dir, html_content, latest_version, changelog_history=changelog_history,
        )


def _read_stage_input(path: Path, *, optional: bool = False) -> bytes | None:
    """隔離ビルドの入力は、リンクや再解析ポイントを経由しない通常ファイルに限る。"""
    if path.resolve() != path or path.is_symlink() or path.is_junction():
        raise ValueError(f"隔離ビルドの入力にリンクを使用できません: {path}")
    try:
        status = path.stat()
    except FileNotFoundError:
        if optional:
            return None
        raise
    is_reparse_point = getattr(status, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    if not stat.S_ISREG(status.st_mode) or is_reparse_point:
        raise ValueError(f"隔離ビルドの入力が通常ファイルではありません: {path}")
    return path.read_bytes()


def stage_update(base_dir: Path, stage_dir: Path, update_file: Path, expected_version: str) -> None:
    """指定された更新文を使い、既存の配布物に触れずに候補を生成する。"""
    base_dir = base_dir.resolve()
    stage_dir = stage_dir.absolute()
    if stage_dir.resolve() != stage_dir or stage_dir.is_symlink() or stage_dir.is_junction():
        raise ValueError(f"隔離出力先にリンクを使用できません: {stage_dir}")
    if stage_dir.is_relative_to(base_dir):
        raise ValueError("隔離出力先は LoLDB の作業ディレクトリ外を指定してください")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", expected_version):
        raise ValueError(f"指定された更新版が不正です: {expected_version}")

    require_recovered(base_dir)
    proposed = _read_stage_input(update_file.absolute())
    parsed_update = _parse_markdown_update_block(proposed.decode("utf-8"))
    proposed_version = parsed_update["version"] if parsed_update else "取得不可"
    if proposed_version != expected_version:
        raise ValueError(f"指定版 {expected_version} と更新文の版 {proposed_version} が一致しません")

    stage_dir.mkdir(parents=True, exist_ok=True)
    if any(stage_dir.iterdir()):
        raise ValueError(f"隔離出力先は空ディレクトリを指定してください: {stage_dir}")

    snapshots = {}
    for name in tqdm((*_STAGED_INPUTS, *_OPTIONAL_STAGED_INPUTS), desc="隔離ビルドの入力を準備"):
        copied = _read_stage_input(base_dir / name, optional=name in _OPTIONAL_STAGED_INPUTS)
        snapshots[name] = copied
        if copied is not None:
            target = stage_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(copied)
    history_path = changelog.XO_HISTORY_PATH.absolute()
    xo_history = _read_stage_input(history_path, optional=True)
    (stage_dir / "UPDATE.md").write_bytes(proposed)

    build(
        stage_dir,
        expected_version=expected_version,
        xo_history_text=(xo_history or b"").decode("utf-8"),
        template_dir=stage_dir / "pwa_templates",
    )
    require_recovered(base_dir)
    if (
        _read_stage_input(history_path, optional=True) != xo_history
        or any(_read_stage_input(base_dir / name, optional=True) != copied for name, copied in snapshots.items())
    ):
        raise RuntimeError("隔離ビルド中に元の入力が変更されました。再実行してください")
    if not all((stage_dir / name).is_file() for name in _PUBLICATION_FILES):
        raise RuntimeError("隔離ビルドの成果物が不足しています")
    input_hashes = {
        name: hashlib.sha256(copied).hexdigest() if copied is not None else None
        for name, copied in snapshots.items()
    }
    (stage_dir / "publication_inputs.json").write_text(json.dumps(input_hashes, indent=2) + "\n", encoding="utf-8")
    (stage_dir / "publication.json").write_text(json.dumps(_PUBLICATION_FILES, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="LoLDB の PWA 配布物を生成します")
    parser.add_argument("--stage-update", type=Path, help="更新候補の隔離出力先")
    parser.add_argument("--update-file", type=Path, help="隔離ビルドに反映する更新文")
    parser.add_argument("--expected-version", help="隔離ビルドで検証するバージョン")
    args = parser.parse_args()
    stage_args = (args.stage_update, args.update_file, args.expected_version)
    if args.stage_update is not None and all(value is not None for value in stage_args):
        stage_update(Path(__file__).resolve().parent, *stage_args)
    elif any(value is not None for value in stage_args):
        parser.error("--stage-update、--update-file、--expected-version は一緒に指定してください")
    else:
        build()


if __name__ == "__main__":
    main()
