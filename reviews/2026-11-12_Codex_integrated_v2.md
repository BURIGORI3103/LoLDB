# データ更新の安全性と自動検証

基点は `1b25127`。既知のロール別のパッチ検証と旧処理の停止は既存回帰テストで確認した。

## 変更と結果

- 公式入力が空・欠落・nullの場合、旧版は統合を成功としてマスターを書き換えた。既存チャンピオンの欠落、混在パッチ、無効な公式レコードで保存前に停止し、保存中の各JSONは原子的に置換する。
- 合成データで旧版の再現3件を確認。修正後は単体46件成功。置換拒否を注入して旧JSONと一時ファイルの後始末を確認した。
- 現行の16.22.1で173体、263ロール、225アイテム、3,659件の対面実測統計を読み取り検証した。HTMLとService Workerの生成物、JavaScriptの構文、既存NodeのUI・オフライン検証も対象にした。
- Riot Data Dragonは第三者開発者向けの公式ゲームデータ。OP.GGは出典表示とサービス運用に影響しない取得を求めている。収録済みのOP.GG取得日時とLoLJPWikiの取得日時はそれぞれのメタデータで確認した。LoLJPWikiの再利用条件は未確認。

## 手動更新の確認順

1. 公式基礎値と対象パッチの統計を隔離チェックアウトに取得する。
2. `python merge_data.py --check` で保存前の統合条件を確認する。
3. 正本を更新し、既定の対面統合とPWA生成を実行した後、`python verify_patch_data.py --check` と `python verify_matchup_fix.py` を実行する。
4. PRの差分とCI結果を確認する。個別JSON群の途中でプロセスが強制終了すると新旧が混在する場合がある。マスターは最後に置換されるため、入力を保ったまま再実行し、個別JSONとの一致を検証できる。

[Riot Data Dragon](https://developer.riotgames.com/docs/lol) [OP.GG データ利用](https://help.op.gg/hc/en-us/articles/31091405109401-Can-I-use-OP-GG-data) [LoLJPWiki](https://www.loljp-wiki.jp/wiki/index.php)
