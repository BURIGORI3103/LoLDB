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


def _write_pair(dist_path: Path, root_path: Path, content: str) -> None:
    """同じ内容を配布用ディレクトリとルートに保存する。"""
    dist_path.write_text(content, encoding="utf-8")
    root_path.write_text(content, encoding="utf-8")


def write_distribution(base_dir: Path, dist_dir: Path, html_content: str, latest_version: str) -> None:
    """同じ PWA をルートと dist に出力し、dist の内容を ZIP にまとめる。"""
    index_path = dist_dir / "index.html"
    root_index_path = base_dir / "index.html"
    print(f"単一HTML {index_path} および {root_index_path} を出力中...")
    _write_pair(index_path, root_index_path, html_content)

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
    _write_pair(sw_path, base_dir / "sw.js", sw_content)

    manifest_path = dist_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    _write_pair(manifest_path, base_dir / "manifest.json", _MANIFEST_CONTENT)

    # GitHub Pages用 .nojekyll の配置
    (dist_dir / ".nojekyll").touch(exist_ok=True)
    (base_dir / ".nojekyll").touch(exist_ok=True)

    # プロジェクト直下の配布用ZIP (LoLDB_dist.zip) も自動同期更新
    zip_path = base_dir / "LoLDB_dist.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                full_p = Path(root) / file
                zf.write(full_p, full_p.relative_to(dist_dir))

    html_size_kb = index_path.stat().st_size / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")
