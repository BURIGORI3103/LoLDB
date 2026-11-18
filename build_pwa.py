"""統合マスターデータを埋め込んだオフライン PWA を生成する。"""

import re
from pathlib import Path

from audit_normalization import project_for_display
from pwa_builder.changelog import (
    CURATED_CHANGELOG_ITEMS as CURATED_CHANGELOG_ITEMS,
    VERSION_ICONS as VERSION_ICONS,
    _parse_markdown_update_block as _parse_markdown_update_block,
    _parse_version_tuple as _parse_version_tuple,
    load_and_render_changelog,
)
from pwa_builder.packager import write_distribution
from pwa_builder.rendering import render_page
from pwa_builder.sources import _load_required_source


def build(base_dir: Path | None = None) -> None:
    """指定ディレクトリの正本と更新履歴から PWA の配布物を生成する。"""
    from data_transaction import require_recovered

    base_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent
    require_recovered(base_dir)
    master_file = base_dir / "merged_data" / "all_champions.json"
    items_file = base_dir / "merged_data" / "all_items.json"

    # 両方の正本を配布物へ書き込む前に検証する（欠損時に空の ITEMS で上書きしたり、正常終了したりしない）
    print("マスターデータを読み込み中...")
    all_champs = _load_required_source(master_file, "マスターデータファイル")
    print("アイテムデータを読み込み中...")
    all_items = _load_required_source(items_file, "アイテムデータファイル")
    print(f"合計 {len(all_items)} 件のアイテムデータを読み込みました。")

    dist_dir = base_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"合計 {len(all_champs)} 体のチャンピオンデータを読み込みました。")

    # パッチ番号をマスターデータから一元抽出
    first_champ = next(iter(all_champs.values()), {})
    build_patch = first_champ.get("patch", "16.20.1")
    if not re.fullmatch(r"\d+\.\d+\.\d+", build_patch) or {champ.get("patch") for champ in all_champs.values()} != {build_patch}:
        raise ValueError("生成対象のパッチが不正または混在しています")
    short_patch = ".".join(build_patch.split(".")[:2])
    latest_version, changelog_items_html = load_and_render_changelog(base_dir, dist_dir)
    if not re.fullmatch(r"v\d+\.\d+\.\d+", latest_version):
        raise ValueError("生成対象のバージョンが不正です")
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
    )

    write_distribution(base_dir, dist_dir, html_content, latest_version)


if __name__ == "__main__":
    build()
