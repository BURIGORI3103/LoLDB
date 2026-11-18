"""HTML、Service Worker、マニフェストと配布 ZIP を出力する。"""

import hashlib
import os
import zipfile
from pathlib import Path


def write_distribution(base_dir: Path, dist_dir: Path, html_content: str, latest_version: str) -> None:
    """同じ PWA をルートと dist に出力し、dist の内容を ZIP にまとめる。"""
    index_path = dist_dir / "index.html"
    root_index_path = base_dir / "index.html"
    print(f"単一HTML {index_path} および {root_index_path} を出力中...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(root_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Service Worker (sw.js) の生成 (バージョン＆HTMLハッシュ連動でキャッシュ名を自動更新)
    html_short_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()[:8]
    dynamic_core_cache = f"loldb-core-{latest_version}-{html_short_hash}"
    sw_content = (base_dir / "service_worker_template.js").read_text(encoding="utf-8")
    sw_content = sw_content.replace("__VER_HASH__", f"{latest_version}-{html_short_hash}").replace("__DYNAMIC_CORE_CACHE__", dynamic_core_cache).replace("__HTML_HASH__", hashlib.sha256(html_content.encode("utf-8")).hexdigest())
    sw_path = dist_dir / "sw.js"
    root_sw_path = base_dir / "sw.js"
    print(f"Service Worker {sw_path} を出力中...")
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)
    with open(root_sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)

    # PWA Manifest (manifest.json) の生成
    manifest_content = """{
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
    manifest_path = dist_dir / "manifest.json"
    root_manifest_path = base_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)
    with open(root_manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

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

    html_size_kb = os.path.getsize(index_path) / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")
