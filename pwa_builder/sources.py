"""PWA に埋め込む正本の読み込みと JSON の整形を扱う。"""

import json
import sys
from pathlib import Path
from typing import Any


def _load_required_source(path: Path, label: str) -> dict[str, Any]:
    """配布物の生成に必須の正本を読み込む。欠損・破損・空なら既存の配布物を残して非0終了する。"""
    if not path.exists():
        print(f"エラー: {label} {path} が見つかりません。既存の配布物は変更せずに中止します。")
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"エラー: {label} {path} を読み込めません ({exc})。既存の配布物は変更せずに中止します。")
        sys.exit(1)
    if not isinstance(data, dict) or not data:
        print(f"エラー: {label} {path} が空または形式不正です。既存の配布物は変更せずに中止します。")
        sys.exit(1)
    return data


def safe_json_for_script(obj: object) -> str:
    """HTML の script 要素の境界文字をエスケープした JSON を返す。"""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
