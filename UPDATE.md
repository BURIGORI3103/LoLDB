# LoLDB アップデート履歴

本ファイルは、直近の最新アップデート情報です。すべての過去履歴は Obsidian (XO) Vault で一元管理されています。

---

# アップデート（2026年10月22日 - v2.6.0 / レーン別相性行列の完全分離・OP.GG検証強化・XSS/SW修正・PWA軽量化）

## 概要
- 相性データを(自分, 相手, レーン, パッチ)単位のmatchup_matrix_by_roleに分離し、シミュレーターにレーン選択UIと実測/推定メタデータ表示を追加\n- OP.GG RSCパーサーのエスケープ引用符対応と必須データ検証、fetch_championsのタイムアウト設定を追加\n- インラインJSONのscriptエスケープ、DOM XSS対策、Service Workerキャッシュ削除スコープ限定、分割JSON出力によるPWA HTML約60%軽量化(14MB→5.65MB)を実装
