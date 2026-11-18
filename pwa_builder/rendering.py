"""アプリの HTML、CSS、JavaScript を単一の配布用 HTML にまとめる。"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .sources import safe_json_for_script


_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "pwa_templates"
_TOKEN = re.compile(r"__[A-Z][A-Z0-9_]*?__")


def render_template(template: str, values: Mapping[str, str]) -> str:
    """テンプレート内のトークンを一度だけ置換し、挿入値は再走査しない。"""
    return _TOKEN.sub(lambda match: values[match.group()], template)


def _read_template(filename: str) -> str:
    # ソースとしての末尾改行を除き、元のインライン出力と改行位置をそろえる。
    return (_TEMPLATE_DIR / filename).read_text(encoding="utf-8").removesuffix("\n")


def render_page(
    *,
    build_patch: str,
    short_patch: str,
    latest_version: str,
    changelog_items_html: str,
    champions: dict[str, Any],
    items: dict[str, Any],
    ui_helpers: str,
) -> str:
    """正本 JSON と UI ヘルパーを埋め込み、単一 HTML を生成する。"""
    app_js = render_template(
        _read_template("app.js"),
        {
            "__DEFAULT_PATCH_JSON__": safe_json_for_script(build_patch),
            "__CHAMPIONS_JSON__": safe_json_for_script(champions),
            "__ITEMS_JSON__": safe_json_for_script(items),
            "__UI_HELPERS__": ui_helpers,
        },
    )
    return render_template(
        _read_template("index.html.tmpl"),
        {
            "__SHORT_PATCH__": short_patch,
            "__LATEST_VERSION__": latest_version,
            "__CHANGELOG_ITEMS_HTML__": changelog_items_html,
            "__STYLES__": _read_template("styles.css"),
            "__APP_JS__": app_js,
        },
    )
