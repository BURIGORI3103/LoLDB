# LoLDB アップデート履歴

本ファイルは、直近の最新アップデート情報です。すべての過去履歴は Obsidian (XO) Vault で一元管理されています。

---

# アップデート（2026年11月18日 - v2.8.0 / build_pwa.pyのテンプレート/ビルダー分離と回帰テスト拡充）

## 概要
3,373行のbuild_pwa.pyをpwa_builder/（changelog, sources, rendering, packager）4モジュールとpwa_templates/（index.html.tmpl, styles.css, app.js）へ分離し、単一パス置換で単一HTML配布を維持。テンプレート等価性・補助データ更新スクリプト等のテスト31件を追加し、Python 91件・UI/SWのNode検証・データ整合性チェックが全成功。
