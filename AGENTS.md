■ LoLDB プロジェクト専用 AGENTS.md

【1. プロジェクト概要・目的】
1. 名称：LoLDB
2. 目的：League of Legends（LoL）のチャンピオン、アイテム、ロール別ビルド、ルーン、スキル、対面（マッチアップ）相性情報を集約・正規化し、スマートフォンでも高速に使えるオフライン対応PWA（Progressive Web App）を生成するプロジェクト。
3. 公開先：GitHub Pages（https://burigori3103.github.io/LoLDB/）

【2. Git管理ステータス】
- 分類：グループA（Git管理あり・独立Gitリポジトリ）
- パス：C:\Project\LoLDB
- デフォルトブランチ：main
- 注意事項：Git操作やデータ更新・PWAビルド・テストを行う際は、親フォルダ（C:\Project）ではなく必ず C:\Project\LoLDB へ移動（cd）してから実行すること。

【3. 主要なファイル構成と役割】
1. データ収集・統合・補完スクリプト群：
   - fetch_champions.py：Data Dragonからチャンピオン基礎データを取得
   - generate_all_items.py / enhance_items_data.py：アイテムデータの生成・詳細強化
   - process_url_list.py：docs/LoL_URL_list.md を参照して攻略情報を収集
   - merge_data.py：収集データを merged_data/all_champions.json および個別JSONへ統合
   - update_champion_attack_types.py：公式 stats.attackrange に基づき近接（Melee）・遠隔（Ranged）・特殊可変形態（HYBRID）を判定
   - update_champion_damage_types.py：ダメージ属性（AD/AP/タンク/両型）を判定・付与
   - update_champion_sustain.py：スキル・パッシブ説明文から体力回復・自己シールド（sustain_info）を解析・付与
   - enrich_role_builds.py / sync_all_roles_complete.py / build_advanced_champion_data.py / build_comprehensive_matchups.py / migrate_matchups.py：ロール別ビルド・マッチアップ相性データの正規化・統合（実測 opgg_stats と推定 synergy_estimate の厳格分離）
2. PWA生成・検証・配布スクリプト群：
   - build_pwa.py：merged_data/all_champions.json や UPDATE.md、Update_History.md を読み込み、単一HTML（index.html, dist/index.html）、manifest.json、sw.js（キャッシュ名自動ハッシュ化）、および配布パッケージを生成するコアビルドスクリプト
   - build_migration_package.py：旧URLからの移転誘導用パッケージ（dist_old_url_migration/）を生成
   - verify_matchup_fix.py / tests/test_opgg_and_matchups.py：データ整合性・マッチアップ検証テスト
3. ドキュメント・仕様書：
   - project_context.md：本プロジェクトの正本仕様書（Source of Truth）
   - docs/LoL_Database_Specification.md：データスキーマ仕様書
   - docs/LoL_URL_list.md：攻略情報参照元URLリスト
   - README.md / UPDATE.md：公開説明および直近のアップデート要約

【4. 実行コマンド・Python環境・テスト手順】
1. 使用Python環境：
   - システム共通Python：C:\Users\gorir\AppData\Local\Programs\Python\Python312\python.exe
2. 実行コマンド（必ず cd C:\Project\LoLDB 後に実行）：
   - PWAビルド生成：python build_pwa.py
   - データ統合：python merge_data.py
   - マッチアップ整合性チェック：python verify_matchup_fix.py
   - 注意事項：index.html および dist/index.html は build_pwa.py による自動生成物である。UIやロジックを変更する際は生成元の build_pwa.py を編集してから再ビルドすること。
3. テスト手順（必ず cd C:\Project\LoLDB 後に実行）：
   - 単体テスト実行：python -m unittest discover -s tests

【5. 開発ツールとしてのCodexとスクリプト内部API・推論処理の境界線】
1. 本プロジェクトのデータ収集・解析・PWA生成スクリプト群、および関連するAI補助処理（Gemini APIの2段構え運用等を使うスクリプトが存在する場合を含む）は意図した設計である。
2. 開発ツールとしてOpenAI Codexを使用していても、濱田くんからの明示的な指示がない限り、既存の外部データ取得ロジックや内部API呼び出しを勝手にOpenAI APIへ書き換えたり削除したりしてはならない。

【6. Obsidian（XO）およびGoogle Driveとの連携情報】
1. 正本仕様書（ローカル）：C:\Project\LoLDB\project_context.md
2. Obsidian Vault側ミラー仕様書：C:\Project\graviXObsidian\Topics\LoLDB\project_context.md
3. Obsidian Vault側アップデート履歴：C:\Project\graviXObsidian\Topics\LoLDB\Update_History.md
4. Google Drive同期コードバンドル出力先：C:\Users\gorir\マイドライブ\GeminiBook_Sources\LoLDB\LoLDB_CodeBundle.md（および C:\Project\GeminiBook_Sources\LoLDB\LoLDB_CodeBundle.md）
5. 参照・更新ルール：
   - 作業前に必ず C:\Project\LoLDB\project_context.md と docs/LoL_Database_Specification.md を確認すること。
   - build_pwa.py は UPDATE.md と C:\Project\graviXObsidian\Topics\LoLDB\Update_History.md を動的パースしてアプリ内の更新履歴モーダルとバージョンバッジを自動生成する。
   - 区切りのタイミングで python c:\Project\add_update.py --project LoLDB --version <Ver> --title <Title> --desc <Desc> を実行すると、XO履歴記帳と同時に build_pwa.py も自動実行される（コミット・同期不要の指示がある場合は除く）。
