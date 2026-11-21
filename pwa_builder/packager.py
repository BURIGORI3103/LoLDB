"""HTML、Service Worker、マニフェストと配布 ZIP を出力する。"""

import hashlib
import io
import os
import re
import zipfile
from pathlib import Path

from data_transaction import publish_locked, update_lock


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


def _distribution_zip(dist_dir: Path, generated: dict[str, bytes]) -> bytes:
    """今回生成した内容と既存素材を組み合わせて、配布ZIPを先に完成させる。"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dist_dir.rglob("*")):
            name = path.relative_to(dist_dir).as_posix()
            if name in generated or path.name.endswith(_TEMP_SUFFIX):
                continue
            if path.is_file():
                archive.write(path, name)
        for name, content in generated.items():
            archive.writestr(name, content)
    return output.getvalue()


def write_distribution(
    base_dir: Path,
    dist_dir: Path,
    html_content: str,
    latest_version: str,
    *,
    changelog_history: str | None = None,
) -> None:
    """配布物作成の単独入口。"""
    base_dir = base_dir.resolve()
    with update_lock(base_dir):
        write_distribution_locked(base_dir, dist_dir.absolute(), html_content, latest_version,
                                  changelog_history=changelog_history)


def write_distribution_locked(
    base_dir: Path,
    dist_dir: Path,
    html_content: str,
    latest_version: str,
    *,
    changelog_history: str | None,
) -> None:
    """排他中に、ルート・dist・ZIPを一回の更新で配布する。"""
    html_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()
    version_hash = f"{latest_version}-{html_hash[:8]}"
    worker_values = {
        "__VER_HASH__": version_hash,
        "__DYNAMIC_CORE_CACHE__": f"loldb-core-{version_hash}",
        "__HTML_HASH__": html_hash,
    }
    sw_template = (base_dir / "service_worker_template.js").read_text(encoding="utf-8")
    sw_content = _SERVICE_WORKER_TOKEN.sub(lambda match: worker_values[match.group()], sw_template)
    texts = {"index.html": html_content, "sw.js": sw_content, "manifest.json": _MANIFEST_CONTENT}
    if changelog_history is not None:
        texts["data/changelog_history.json"] = changelog_history
    # Windowsでも従来のテキスト出力と同じ改行で書き出す。
    generated = {name: content.replace("\n", os.linesep).encode("utf-8") for name, content in texts.items()}

    distribution = {}
    for directory in (dist_dir, base_dir):
        marker = directory / ".nojekyll"
        distribution[directory] = {
            **generated,
            ".nojekyll": marker.read_bytes() if marker.is_file() else b"",
        }
    zip_content = _distribution_zip(dist_dir, distribution[dist_dir])
    outputs = [
        (directory / name, content)
        for directory, files in distribution.items()
        for name, content in files.items()
    ]
    outputs.append((base_dir / "LoLDB_dist.zip", zip_content))
    for path, _ in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    publish_locked(base_dir, outputs, publication=True)

    index_path = dist_dir / "index.html"
    html_size_kb = index_path.stat().st_size / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {dist_dir / 'sw.js'}")
    print(f"Manifest: {dist_dir / 'manifest.json'}")
