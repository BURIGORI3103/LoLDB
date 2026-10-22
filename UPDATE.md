# LoLDB アップデート履歴

本ファイルは、直近の最新アップデート情報です。すべての過去履歴は Obsidian (XO) Vault で一元管理されています。

---

# アップデート（2026年10月22日 - v2.6.1 / アプデ履歴・バージョンバッジ・SWキャッシュの完全自動生成化とadd_update.py自動リビルド連携）

## 概要
- 【アプデ履歴＆バージョンバッジの完全自動生成化】build_pwa.py内のハードコードされた履歴HTMLを撤廃し、UPDATE.mdおよびObsidianのUpdate_History.mdを動的パースしてヘッダーバッジ(#patchBadge)とアプデ履歴モーダル(#changelogModal)を100%自動生成する仕組みを実装
- 【v2.6.0および全過去履歴の完全反映】漏れていたv2.6.0（レーン別相性分離・OP.GG検証強化・XSS/SW保護・PWA約60%軽量化）を含む全履歴をモーダルへ完全同期
- 【add_update.py自動リビルド連携】add_update.py実行時にbuild_pwa.pyを自動呼び出しするフックを追加し、アップデート記帳と同時にPWA成果物・配布ZIPが確実に最新バージョンへ書き換わる設計を実現
- 【Service Workerキャッシュ名のバージョン＋ハッシュ自動連動】CORE_CACHE名を loldb-core-{version}-{hash} としてビルド時に自動算出し、更新時のブラウザキャッシュ残留を防止
