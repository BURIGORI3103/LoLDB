# LoLDB 総合レビュー（Claude Code）

- **実施日時**：2026-11-18 21:40〜22:30（JST）
- **実施者**：Claude Code（デスクトップアプリ Code タブ）
- **対象**：`main`、基点コミット `d24d218`（XO フォルダ改名に合わせた参照更新の直後）
- **同時に確認したリポジトリ**：GoriVoice_Win、XObsidian（各 `reviews/` に同日付の記録あり）
- **コミット・プッシュ**：依頼の指示により実施していない（作業ツリーに未コミット差分として残している）。

## 結論

PWA の描画、配布物の生成、複数 JSON の更新トランザクションに、実害のある欠陥は確認できなかった。データ取得スクリプト1本の通信タイムアウト欠落だけを修正した。Critical・High はなし。

## 確認した範囲と所見

- **PWA の XSS**：`pwa_templates/app.js` の `innerHTML` に入る補間を全件洗い出した。テキストは `escapeHtml`、URL は `safeImageUrl`（`https://ddragon.leagueoflegends.com` の画像パスのみ許可）・`safeExternalUrl`（`https` のみ）、CSS クラスは許可リストを通っている。埋め込み JSON は `safe_json_for_script` で `<` `>` `&` と U+2028/2029 をエスケープしている。問題なし。
- **更新履歴の HTML**：`pwa_builder/changelog.py` は版・日付・各項目を `html.escape` している。問題なし。
- **更新トランザクション**：`data_transaction.py` はロック、ジャーナル、置換前のハッシュ照合、中断時の復元を備えている。準備段階で失敗した場合のジャーナルは次回の `publish` / `recover` で回収される。問題なし。
- **XO 改名の影響**：`pwa_builder/changelog.py` の `XO_HISTORY_PATH` は `C:\Project\XObsidian` に更新済み。

## 発見事項と対応

| ID | 重大度 | 状態 | 内容 |
|---|---|---|---|
| L1 | Low | 修正済み | `generate_all_items.py` の `urlopen` 2か所にタイムアウトがなく、Data Dragon の応答が止まると無期限に待つ。ほかの取得スクリプトはすべて10〜30秒を指定している |
| L2 | Low | 未対応 | 更新履歴が `C:\Project\XObsidian\...\Update_History.md` の固定パスに依存し、別環境では `data/changelog_history.json` のキャッシュに頼る。ローカル単一環境の運用前提の設計として据え置き |
| L3 | Low | 未対応 | `write_distribution` はルートと `dist/` の HTML・`sw.js`・マニフェストを順に上書きし、途中で中断すると版の異なる組み合わせが残り得る。再ビルドで回復できるため据え置き |

## 変更ファイル

- `generate_all_items.py`：`FETCH_TIMEOUT_SECONDS = 30` を追加し、両方の `urlopen` に指定
- `tests/test_pipeline_helpers.py`：既存の取得テストに、2回の取得へ期限が渡ることの検証を追加

## 検証結果

| コマンド（`C:\Project\LoLDB` で実行） | 結果 |
|---|---|
| `python -m unittest discover -s tests`（修正前） | 91件成功 |
| `python -m unittest discover -s tests`（修正後） | 91件成功（追加の検証は既存テスト内） |
| `python -m py_compile`（変更ファイル） | 成功 |

## 実施できなかった検証

- 実ネットワークでのデータ取得、PWA の再ビルド（`index.html` などの生成物が更新されるため実行していない）。
- ブラウザでの PWA 表示確認（今回は描画コードに変更なし）。
- ruff・pyflakes は未導入のため Lint は未実施。

## 次のエージェントへの推奨作業

1. 濱田くんの承認後、差分をコミット・プッシュする。
2. L3 を直す場合は、生成物を一時ファイルへ書いてから `os.replace` する形にし、既存の生成物比較テストで等価性を確認する。
