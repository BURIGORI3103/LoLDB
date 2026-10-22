# LoLDB アップデート履歴

本ファイルは、直近の最新アップデート情報です。すべての過去履歴は Obsidian (XO) Vault で一元管理されています。

---

# アップデート（2026年10月22日 - v2.6.0 / レーン別相性厳格分離・OP.GG検証強化・SWスコープ保護・約60%軽量化）

## 概要
### 修正内容
1. **レーン別相性データの厳格分離と実測・推定メタ情報表示**:
   - `build_comprehensive_matchups.py` で `(自分, 相手, レーン, パッチ)` ごとに実測相性（`matchup_matrix_by_role`）を分離し、別レーンの統計混入を解消。
   - シミュレーターにレーン切り替えタブ（自動/TOP/JUG/MID/ADC/SUP）と、実測データの参照元・地域・ランク・取得日表示、および特性推定時の推定要因・限界説明を追加。
2. **OP.GGスクレイピング成功判定の厳密化とFixtureテスト導入**:
   - `process_url_list.py` に `validate_parsed_opgg_data` を実装し、HTTP 200 だけでなく必須項目（ロール・キーストーン・コアビルド・カウンター統計・対象slug）を検証してからチェック済みにするよう改善。
   - `tests/test_opgg_and_matchups.py` および RSC fixture を新設。
3. **HTML/JSデータ埋め込み安全化・XSS対策・パッチ一元管理・大幅軽量化**:
   - `<script>` 内のJSONシリアライズ時に `<`, `>`, `&` をエスケープし、`innerHTML` 挿入箇所に `escapeHtml` を徹底。
   - パッチ番号を `DEFAULT_PATCH` に一元管理し、`fetch_champions.py` にネットワークタイムアウトを設定。
   - 冗長な推定オブジェクトをクライアントサイド推定エンジン＋実測差分辞書化（および `data/` 分割出力）し、`index.html` を約14MBから約5.7MBへ約60%軽量化。
4. **Service Worker (`sw.js`) の他アプリキャッシュ保護**:
   - `activate` 時に `loldb-` プレフィックスで始まるキャッシュのみを削除するよう限定し、同一オリジン上の別アプリキャッシュを保護。
