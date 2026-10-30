---
project: LoLDB
status: active
last_reviewed: 2026-10-30
summary: LoL のチャンピオン・アイテム・対面情報を集約し、スマートフォンでも使えるオフライン対応 PWA を生成するプロジェクト。
---

# LoLDB — Project Context

## 目的と公開先

League of Legends のチャンピオン、アイテム、ロール別ビルド、ルーン、スキル、対面情報を検索・閲覧する PWA です。公開先は GitHub Pages の https://burigori3103.github.io/LoLDB/ です。パッチやデータの鮮度は生成データ側で確認し、この文書の日付だけから最新版と判断しません。

## データと生成フロー

1. fetch_champions.py が Data Dragon から基礎データを取得します。
2. process_url_list.py が docs/LoL_URL_list.md を参照し、攻略情報を収集します。
3. merge_data.py / update_champion_damage_types.py / update_champion_attack_types.py / update_champion_sustain.py / sync_all_roles_complete.py / build_advanced_champion_data.py / scratch/generate_matchup_reasons.py / build_comprehensive_matchups.py が収集データを統合・正規化・補完します。
   - AA通常攻撃タイプは公式の `stats.attackrange` に基づき、近接（Melee: <=250）、遠隔（Ranged: >250）、および特殊可変形態（Jayce, Nidalee, Elise, Gnar, Kayle: HYBRID）を厳密に判定して保持。
   - サステイン能力は公式スキル・パッシブ説明文から体力回復（吸血・リジェネ強化）および自己シールドを厳密解析し `sustain_info` として保持。
   - ダメージ属性（AD/AP/タンク/両型）およびサステイン特性を付与し、UI上の一覧・シミュレーター双方で複合絞り込み（AND条件）をサポート。
   - マッチアップは正規スキーマ（champion_id, name, winrate, winrate_display, reason, role, patch, source, is_estimated）で管理。
   - 実測データ（opgg_stats）と推定相性（synergy_estimate）を厳格に分離し、ハッシュ値による疑似勝率生成は廃止。
   - 相性解説は data/matchup_reason_evidence.json に出典付きで登録し、対面・ロール・有利不利の方向が一致した文献確認済みのものだけを表示する。未確認の対面カードには解説を出さず、勝率を保持する。文献上の相性説明と現在パッチの勝率の因果関係は区別する。
4. build_pwa.py が単一 HTML、マニフェスト、Service Worker を生成します。

詳細なデータスキーマは docs/LoL_Database_Specification.md、攻略情報の参照先は docs/LoL_URL_list.md を確認してください。収集元の構造や記載内容は変わるため、スクレイピング結果を検証せずに正しい最新情報とみなしません。

- refresh_wiki.py は公式取得済みチャンピオン一覧から日本語名と参照URLを再生成し、現行の www.loljp-wiki.jp/wiki/?Champion/<英語ID> から「考察」「相性・対策」の短い抜粋を再取得します。
- wikiの取得結果は strategy_data の wiki_info と docs/wiki_refresh_report.json に、出典URL・取得日時・成否を付けて保存します。wikiのパッチ対応は未検証であり、OP.GGの取得チェックとは別に管理します。失敗時は本文を生成して成功扱いにしません。
- OP.GGの正式slugはウーコンが monkeyking、レナータが renata。process_url_list.py --refresh --reuse-wiki で全件を再取得し、ページ表示のパッチを検証します。refresh_role_stats.py が実運用ロールごとのページから統計を取得し、表示ロールとパッチを検証して role_data へ保存します。
- merge_data.py はパッチ・ロール別の取得が未完了なら停止し、検証済みデータで統計を置換します。コンボ・スキル順などの既存補完を保持し、ダメージ属性・AAタイプ・サステインと対面マトリクスを後段で再計算します。sync_all_roles_complete.py の固定相性・固定ビルドによる補完はパッチ更新フローでは実行しません。
- apply_matchup_reasons.py は文献確認済み解説をマスター・個別JSON・対面マトリクスへ同期する。基礎特性から推測した説明は相性理由として採用しない。シミュレーターも確認済み解説がない場合は未確認と表示する。
- collect_wiki_matchups.py --refresh は全173体のwiki相性欄を取得し、CSSで折りたたまれた本文も対象画像群・有利不利・敵味方・説明文に分けて data/wiki_matchups.json へ集計する。保存済みHTMLからの再集計は引数なし。本文中の補足参照や例外を対象画像群へ追加しない。結果と取得不可・抽出項目なしのページは docs/wiki_matchup_collection_report.json に記録する。
- アプリの「wiki掲載の敵・味方との相性」は自動抽出した掲載文として独立表示する。ロール・現在パッチの検証済み統計ではなく、OP.GGの勝率・有利不利判定へ自動転用しない。

## 生成物と運用上の制約

- チャンプピック早見表は、ガレンを優先する4体の手動登録候補を検索・絞り込みできる。パッチ26.21を基準にした暫定判断であり、全対面を網羅した統計や勝率の保証ではない。追加候補は対面の特性とチーム構成、プレイヤーの習熟度を踏まえて検討する。
- index.html と dist/index.html は生成物です。UI の変更は可能な限り生成元の build_pwa.py に反映し、ビルド後に出力を確認します。
- build_pwa.py の再ビルド時は、merged_data/all_champions.json および個別JSONが正本として同一同期されていることを保証します。
- アプリ上部のバージョンバッジ（`#patchBadge`）およびアップデート履歴モーダル（`#changelogModal`）は、`build_pwa.py` 実行時に `UPDATE.md` および `graviXObsidian/Topics/LoLDB/Update_History.md`（ならびに `data/changelog_history.json`）を動的パースして100%自動生成されます。さらに `c:\Project\add_update.py` 実行時に `build_pwa.py` が自動呼び出しされ、アップデート記帳と同時にPWA成果物が最新バージョンへ再ビルドされます。
- Service Worker のキャッシュ名（`CORE_CACHE`）は `loldb-core-{latest_version}-{html_hash}` としてビルド時に自動算出され、更新時のキャッシュ残留を防止します。
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
