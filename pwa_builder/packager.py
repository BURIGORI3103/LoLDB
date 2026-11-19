"""HTML、Service Worker、マニフェストと配布 ZIP を出力する。"""

import hashlib
import os
import re
import zipfile
from pathlib import Path


_SERVICE_WORKER_TOKEN = re.compile(r"__(?:VER_HASH|DYNAMIC_CORE_CACHE|HTML_HASH)__")
_MANIFEST_CONTENT = """{
  "name": "LoLDB",
  "short_name": "LoLDB",
  "start_url": "./index.html",
  "display": "standalone",
  "background_color": "#0b0f19",
  "theme_color": "#0f172a",
  "orientation": "any",
  "icons": [
    {
      "src": "./icon.png",
      "sizes": "120x120",
      "type": "image/png"
    },
    {
      "src": "./icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
"""


_TEMP_SUFFIX = ".loldb-tmp"


def _temporary_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.{os.getpid()}{_TEMP_SUFFIX}")


def _publish_texts(outputs: list[tuple[Path, str]]) -> None:
    """全ファイルを一時ファイルへ書き終えてから置き換え、版の混在を残さない。"""
    staged: list[tuple[Path, Path]] = []
    try:
        for path, content in outputs:
            temporary = _temporary_path(path)
            staged.append((temporary, path))
            temporary.write_text(content, encoding="utf-8")
        for temporary, path in staged:
            os.replace(temporary, path)
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def write_distribution(base_dir: Path, dist_dir: Path, html_content: str, latest_version: str) -> None:
    """同じ PWA をルートと dist に出力し、dist の内容を ZIP にまとめる。"""
    index_path = dist_dir / "index.html"
    root_index_path = base_dir / "index.html"
    print(f"単一HTML {index_path} および {root_index_path} を出力中...")

    # HTML とバージョンから Service Worker のキャッシュ名を決める。
    html_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
    version_hash = f"{latest_version}-{html_hash[:8]}"
    worker_values = {
        "__VER_HASH__": version_hash,
        "__DYNAMIC_CORE_CACHE__": f"loldb-core-{version_hash}",
        "__HTML_HASH__": html_hash,
    }
    sw_template = (base_dir / "service_worker_template.js").read_text(encoding="utf-8")
    sw_content = _SERVICE_WORKER_TOKEN.sub(lambda match: worker_values[match.group()], sw_template)
    sw_path = dist_dir / "sw.js"
    print(f"Service Worker {sw_path} を出力中...")

    manifest_path = dist_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    _publish_texts([
        (index_path, html_content),
        (root_index_path, html_content),
        (sw_path, sw_content),
        (base_dir / "sw.js", sw_content),
        (manifest_path, _MANIFEST_CONTENT),
        (base_dir / "manifest.json", _MANIFEST_CONTENT),
    ])

    # GitHub Pages用 .nojekyll の配置
    (dist_dir / ".nojekyll").touch(exist_ok=True)
    (base_dir / ".nojekyll").touch(exist_ok=True)

    # プロジェクト直下の配布用ZIP (LoLDB_dist.zip) も自動同期更新
    zip_path = base_dir / "LoLDB_dist.zip"
    temporary_zip = _temporary_path(zip_path)
    try:
        with zipfile.ZipFile(temporary_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(dist_dir):
                for file in files:
                    if file.endswith(_TEMP_SUFFIX):
                        continue  # 中断した過去のビルドの一時ファイルは配布しない
                    full_p = Path(root) / file
                    zf.write(full_p, full_p.relative_to(dist_dir))
        os.replace(temporary_zip, zip_path)
    finally:
        temporary_zip.unlink(missing_ok=True)

    html_size_kb = index_path.stat().st_size / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")
