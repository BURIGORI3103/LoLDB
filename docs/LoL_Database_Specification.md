# LoLDB データ・生成仕様

## 正本と統合

設計上の正本は `project_context.md`、実データの正本は `merged_data/all_champions.json` と `all_items.json`。個別チャンピオンJSONはマスターと一致させる。

1. `fetch_champions.py` が公式の基礎値・パッシブ・通常スキルを取得する。
2. `process_url_list.py` と `refresh_role_stats.py` がOP.GGのチャンピオン・ロール・パッチを照合する。
3. `merge_data.py` が取得済み統計を統合し、手動補完と同一パッチの新しい対面取得結果を保持する。未検証パッチやロール不足では停止する。
4. `audit_normalization.py` が説明文・見出し・ビルド属性・ID参照・確認済み攻略根拠を正規化する。汎用コンボや固定ビルドを欠損補完として生成しない。
5. `build_pwa.py` がHTML、マニフェスト、Service Worker、ZIPを生成する。`ui_helpers.js` はHTMLへ埋め込む。

パッチ指定対応の収集スクリプトは `--patch` で対象を明示でき、省略時は最新を取得する。統合時はパッチ混在を拒否する。`repair_audit_data.py` は `--patch` を必須とし、正本との一致を要求する。

## チャンピオン

| 項目 | 内容 |
|---|---|
| `id` / `key` / `name` / `title` / `patch` | 公式ID、数値ID、日本語名、二つ名、Data Dragonパッチ |
| `classes` / `roles` | 公式クラスと取得済み運用ロールを別々に保持 |
| `stats` | 公式ステータス |
| `abilities` | パッシブ配列。`slot` は `Passive` |
| `spells` | Q・W・E・R配列。`slot`、名称、説明、CD、コスト、画像 |
| `role_data` | `TOP`・`JUG`・`MID`・`ADC`・`SUP` をキーとするロール別情報 |
| `build` / `runes` / `build_patterns` | 第1ロールに対応する情報 |
| `matchups` / `matchup_matrix_by_role` | 検証済み対面統計とロール別正規化結果 |
| `wiki_info` / `wiki_matchups` | wiki考察抜粋と掲載相性。統計と分離 |
| `overview` | 確認済み概要の `summary` と出典。汎用の強み・弱みを生成しない |
| `attack_type` / `damage_profile` / `sustain_info` | 通常攻撃タイプ、ダメージ属性、回復・シールド情報 |

説明文は独自タグを除去し、改行を保持する。`abilities` と `spells` は役割が異なるため両方を保持する。

## ビルド・ルーン・アイテム

- `build` の `starter`・`boots`・`core`・`situational` は `item_id` と `name` を持つ配列。
- `build_patterns` の `core_items`・`starter_items`・`boots_items`・`situational_items` もID付き配列。旧 `core`・`starter`・`boots`・`situational` は互換用に保持し、描画はID付き配列を使う。
- 不明なアイテムを既定の別アイテムへ置換しない。カシオペアの靴は全保存層・全パターンで空とする。
- コアは取得元の完成品の組み合わせから採用する。通常の素材と `specialRecipe` 等による変身・専用強化を区別し、不足枠を推測で補わない。
- `runes.primary` は `path`・`keystone`・`keystone_name`・`choices`、`secondary` は `path`・`choices`、`shards` は日本語名配列。
- `rune_reference.json` は公式ルーン名と親ツリーの対応を対象パッチ付きで保存する。
- 図鑑は通常サモナーズリフト用を選別する。6桁のモード別クローン、内部ペットIDを除外し、変身後の正当なアイテムは保持する。`from`・`into` は存在するIDだけを参照する。
- `name` は公式名を保持する。正当な専用品の同名は `requiredChampion` で区別し、`display_name` に専用条件を付ける。価格・ステータス・合成先はIDで参照する。

## 攻略根拠と欠落

`role_guidance_evidence.json` は `champion_id`・`role`・`field`・`value`・`source_url`・`source_patch`・`checked_at`・`verified` を持つレコード配列。対象と確認済み状態を照合して適用し、明示パッチが正本と違う情報は適用しない。文章のパッチ対応未検証は表示する。

Lux ADC・Sion MID・Tristana MIDはOP.GGのパッチ16.22で再確認したスキル順（16.21から変化なし）と、対象ロールを明示したMobalyticsの文章攻略を参照する。パッチ16.22ではLux ADCがOP.GGの運用ロールから外れたため表示対象外とし、記録は保持する。取得表は掲載されたLv1〜15のみを保存する。未取得は未取得と表示し、別ロールや汎用テンプレートを専用情報として出さない。

対面の相性理由は別の `matchup_reason_evidence.json` を使用する。チャンピオン・相手・ロール・有利不利方向が一致する文献確認済み理由のみを表示し、文章攻略を勝率の根拠へ転用しない。

## 配布・描画・検証

- 配布HTMLだけで共通情報の重複を減らし、正本JSONは削らない。廃止シミュレーターの処理と未使用の分割チャンピオン・アイテムJSONは配布しない。
- `script` 内JSONの境界文字をエスケープする。動的テキスト、属性値、外部URL、画像URL、CSSクラスは別々に検証する。
- モーダルは種類・ID・選択ロールを履歴へ保存し、戻る・進むで復元する。最上位だけを操作可能とし、終了時にスクロールとフォーカスを戻す。
- HTMLは最新優先、画像はキャッシュを使いながら更新する。省データ・低速回線では画像の一括先読みを止める。未キャッシュ画像と外部出典のオフライン利用は保証しない。
- `python -m unittest discover -s tests`、`node tests/test_ui_behavior.cjs`、`python verify_patch_data.py`、`python verify_matchup_fix.py` で生成物・パッチ・ロール・個別JSON・文献照合・キャッシュを検証する。

## HTMLキャッシュの内容検証

- `service_worker_template.js` を生成元とし、インストール時はHTTPキャッシュを再利用せず、HTML本文のSHA-256がビルド時の値と一致した場合だけキャッシュとSWを切り替える。
- オンラインで別ビルドのHTMLを受け取っても、現在の検証済みオフラインキャッシュを上書きしない。オフライン時は現在のコアキャッシュだけを参照する。
- `node tests/test_service_worker.cjs` で旧HTMLの混入拒否、切替順序、切断後の復帰、他アプリのキャッシュ保護を検証する。
