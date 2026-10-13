---
project: LoLDB
status: active
last_reviewed: 2026-10-13
summary: LoL のチャンピオン・アイテム・対面情報を集約し、スマートフォンでも使えるオフライン対応 PWA を生成するプロジェクト。
---

# LoLDB — Project Context

## 目的と公開先

League of Legends のチャンピオン、アイテム、ロール別ビルド、ルーン、スキル、対面情報を検索・閲覧する PWA です。公開先は GitHub Pages の https://burigori3103.github.io/LoLDB/ です。パッチやデータの鮮度は生成データ側で確認し、この文書の日付だけから最新版と判断しません。

## データと生成フロー

1. fetch_champions.py が Data Dragon から基礎データを取得します。
2. process_url_list.py が docs/LoL_URL_list.md を参照し、攻略情報を収集します。
3. merge_data.py などの補助スクリプトが収集データを統合・補完します。
4. build_pwa.py が単一 HTML、マニフェスト、Service Worker を生成します。

詳細なデータスキーマは docs/LoL_Database_Specification.md、攻略情報の参照先は docs/LoL_URL_list.md を確認してください。収集元の構造や記載内容は変わるため、スクレイピング結果を検証せずに正しい最新情報とみなしません。

## 生成物と運用上の制約

- index.html と dist/index.html は生成物です。UI の変更は可能な限り生成元の build_pwa.py に反映し、ビルド後に出力を確認します。
- champions_data、strategy_data、merged_data、dist には生成データまたは配布物があります。再生成で手作業の変更が失われないか確認します。
- Service Worker のキャッシュ名・ルートパス・GitHub Pages の /LoLDB/ サブパスを変更すると、オフライン更新に影響します。sw.js と build_pwa.py を併せて確認します。
- GitHub Pages への反映はリポジトリへのプッシュ後です。公開操作とローカル編集を区別します。

## 主な参照ファイル

- README.md: 利用者向け公開説明と PWA の導入手順
- docs/LoL_Database_Specification.md: データスキーマ
- fetch_champions.py、process_url_list.py、merge_data.py: データ収集・統合
- build_pwa.py、sw.js、manifest.json: アプリ生成とオフライン動作
- UPDATE.md: 直近の変更要約
- graviXObsidian/Topics/LoLDB/Update_History.md: 変更履歴
