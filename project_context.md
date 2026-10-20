---
project: LoLDB
status: active
last_reviewed: 2026-10-20
summary: LoL のチャンピオン・アイテム・対面情報を集約し、スマートフォンでも使えるオフライン対応 PWA を生成するプロジェクト。
---

# LoLDB — Project Context

## 目的と公開先

League of Legends のチャンピオン、アイテム、ロール別ビルド、ルーン、スキル、対面情報を検索・閲覧する PWA です。公開先は GitHub Pages の https://burigori3103.github.io/LoLDB/ です。パッチやデータの鮮度は生成データ側で確認し、この文書の日付だけから最新版と判断しません。

## データと生成フロー

1. fetch_champions.py が Data Dragon から基礎データを取得します。
2. process_url_list.py が docs/LoL_URL_list.md を参照し、攻略情報を収集します。
3. merge_data.py / update_champion_damage_types.py / update_champion_attack_types.py / sync_all_roles_complete.py / build_advanced_champion_data.py / scratch/generate_matchup_reasons.py / build_comprehensive_matchups.py が収集データを統合・正規化・補完します。
   - AA通常攻撃タイプは公式の `stats.attackrange` に基づき、近接（Melee: <=250）、遠隔（Ranged: >250）、および特殊可変形態（Jayce, Nidalee, Elise, Gnar, Kayle: HYBRID）を厳密に判定して保持。
   - ダメージ属性（AD/AP/タンク/両型）およびサステイン特性を付与し、UI上の一覧・シミュレーター双方で複合絞り込み（AND条件）をサポート。
   - マッチアップは正規スキーマ（champion_id, name, winrate, winrate_display, reason, role, patch, source, is_estimated）で管理。
   - 実測データ（opgg_stats）と推定相性（synergy_estimate）を厳格に分離し、ハッシュ値による疑似勝率生成は廃止。
   - role_data とトップレベルの詳細理由を同期管理し、理由がない場合は定型文を乱発せず「理由データなし」と明記。
4. build_pwa.py が単一 HTML、マニフェスト、Service Worker を生成します。

詳細なデータスキーマは docs/LoL_Database_Specification.md、攻略情報の参照先は docs/LoL_URL_list.md を確認してください。収集元の構造や記載内容は変わるため、スクレイピング結果を検証せずに正しい最新情報とみなしません。

## 生成物と運用上の制約

- index.html と dist/index.html は生成物です。UI の変更は可能な限り生成元の build_pwa.py に反映し、ビルド後に出力を確認します。
- build_pwa.py の再ビルド時は、merged_data/all_champions.json および個別JSONが正本として同一同期されていることを保証します。
- Service Worker のキャッシュ名・ルートパス・GitHub Pages の /LoLDB/ サブパスを変更すると、オフライン更新に影響します。sw.js と build_pwa.py を併せて確認します（現行: loldb-core-v20）。
- 旧URL（Netlify等）からの移転案内用パッケージとして dist_old_url_migration/ および LoLDB_old_url_migration.zip を管理し、旧URLアクセス者を新URLへ自動誘導します。
- 配布用ZIP（LoLDB_dist.zip 等）はプロジェクト直下（c:\Project\LoLDB\）のみで生成・管理し、デスクトップへの自動出力は行いません。
- GitHub Pages への反映はリポジトリへのプッシュ後です。公開操作とローカル編集を区別します。

## 主な参照ファイル

- README.md: 利用者向け公開説明と PWA の導入手順
- docs/LoL_Database_Specification.md: データスキーマ
- fetch_champions.py、process_url_list.py、merge_data.py: データ収集・統合
- build_pwa.py、sw.js、manifest.json: アプリ生成とオフライン動作
- UPDATE.md: 直近の変更要約
- graviXObsidian/Topics/LoLDB/Update_History.md: 変更履歴
