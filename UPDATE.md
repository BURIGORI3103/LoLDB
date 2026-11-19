# LoLDB アップデート履歴

本ファイルは、直近の最新アップデート情報です。すべての過去履歴は Obsidian (XO) Vault で一元管理されています。

---

# アップデート（2026年11月19日 - v2.8.2 / 配布物の置き換えを一括化し中断時の版混在を防止）

## 概要
レビュー指摘L3への対応。pwa_builder/packager.py の write_distribution で、ルートと dist の index.html・sw.js・manifest.json を一時ファイルへ書き終えてから os.replace で置き換えるようにした。LoLDB_dist.zip も一時ファイル経由で作る。中断で残った一時ファイルはZIPに含めない。生成物は修正前とバイト一致。tests/test_packager_atomic.py を追加し、テスト94件成功。
