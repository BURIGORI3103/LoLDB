【LoLDB 全体レビュー 2026-11-11】

結論。前回の2件を現行mainで再現し、対面マトリクスで取得条件が欠けたデータを実測に分類する経路と合わせて修正しました。P2が3件です。

【対象と確認範囲】

- main 8a96db6bdc0efe494f252376d3b0bfca4cc45ad8、604ファイル。AGENTS、README、仕様書、取得・統合スクリプト、検証・テスト、テンプレート、表示・Service Workerを確認。fix/audit-001-009 は別ブランチ。CI・依存マニフェストの登録なし。
- Data Dragon、OP.GG取得検証、攻略Wiki、正規化、統合、PWAへの出力を追跡。全保存データの検証を実行。各Wiki本文の出典や個別の数値のオンライン照合、全端末の表示確認、過去の配布物本文は棚卸しまたは未検証。

【前回との照合と追加指摘】

| ID | 優先度 | 修正前の対象 | 発生条件・期待と実際・修正結果 |
| --- | --- | --- | --- |
| LOL-01 | P2 | merge_data.py:66 | 未修正。全体パッチを維持したままロールの古いパッチ・未検証・検証欄の数値1を設定しても統合した。正式パッチ、取得元の短縮パッチ、ロール、真偽値Trueを確認して拒否する。 |
| LOL-02 | P2 | sync_all_roles_complete.py:425、migrate_matchups.py:199 | 未修正。旧同期が保存済みのロール取得元等を再構成し、同系統の旧移行も試合数等を失う。両方の入口でデータを開く前に非0終了し、現行フローを案内する。 |
| LOL-03 | P2 | build_comprehensive_matchups.py:223、294 | 新規。取得元、パッチ、試合数のいずれかがない合成エントリが実測として扱われた。実測分類には取得条件を要求し、再構築時は全件を検証してから保存する。 |

【検証】

- 基準Python 33件、Node 2件成功。修正後Python 37件、Node 2件成功。NodeでUIの検索・フィルター・戻る、Service Workerの旧キャッシュ拒否、オフライン復帰等を検証。
- 保存済みパッチ16.21.1は173体、264ロール、225アイテム、3,647実測ペア。verify_patch_data.py、verify_matchup_fix.py、PWA再生成が成功。HTML、Service Worker、マニフェストは追跡版と一致。一時ディレクトリで対面マトリクスの再構築を実行し、同じ3,647ペアと174 JSONの生成を確認。
- 取得元の現時点の値、モバイル実機、インストール済みPWAでの更新は未実施。統合中に複数の書き込み処理を同時実行した場合の全ファイル単位のトランザクションは未検証。

【導入・復帰】

1. 専用ブランチで python -m unittest discover -s tests と node --test tests/test_service_worker.cjs tests/test_ui_behavior.cjs を実行。
2. 取得済みデータで python verify_patch_data.py、python verify_matchup_fix.py、python build_pwa.py を実行。旧処理の入口は書き込み前に停止する。更新作業はREADME・仕様書の現行取得経路を使う。
3. 中断後は先にマスターと個別JSONの整合を確認し、検証済みデータの控えから再生成する。
