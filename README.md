# LoLDB - League of Legends 攻略データベース & 対面相性シミュレーター

> **🚀 公開WebアプリURL**: [https://burigori3103.github.io/LoLDB/](https://burigori3103.github.io/LoLDB/)  
> PC・スマホのブラウザから直接アクセス可能！ホーム画面に追加すればオフラインでも動作するPWA（Progressive Web App）です。

---

## 📖 概要

**LoLDB** は、League of Legends（LoL）の試合前やローディング画面中に、サクッと対面相性やスキル、推奨ビルド、立ち回りの要点を確認できる攻略データベース＆対面シミュレーターアプリです。

- **全173体のチャンピオン完全網羅**: 公式Data Dragon最新パッチ（16.20.1）準拠の基礎ステータス、スキル詳細（Passive / Q / W / E / R）、コンボ、特徴、強み・弱み
- **全283個のアイテム図鑑**: 合成ツリー（Builds From / Into）、ステータス複数AND検索、カテゴリ別フィルター
- **対面対策シミュレーター**: 自分と敵チャンピオンを選ぶだけで、対面有利不利・具体的理由・注意すべきスキル・推奨アイテム・実戦コンボを即座にシミュレーション
- **完全オフライン動作 (PWA)**: Service WorkerとIndexed Cacheにより、通信が不安定な環境や完全オフラインでも爆速で軽快に動作

---

## ✨ 主な機能

### 1. ⚔️ 対面対策シミュレーター
- 相手と自分のチャンピオンを選択してリアルタイム分析
- **相性判定**: 「有利」「警戒・不利」「互角・五分」の3段階と、なぜそうなるのかの実戦的理由を明記
- **対策アイテム提案**: 相手の主属性（AD/AP/タンク/両刀）やサステイン（回復）特性に応じたメタアイテムを自動選出
- **ワンタップ詳細確認**: 相手や自分のスキル詳細・職人コンボへ1タップでジャンプ可能

### 2. 🛡️ チャンピオン図鑑 & ロール別ビルド
- 各ロール（TOP / JUG / MID / ADC / SUP）ごとの専用推奨ビルド・ルーン・サモナースペル
- スキル取得順（Lv 1〜18 マトリクス表）
- 実戦で即使えるスキルコンボ（AA / Flash 連携含む）

### 3. 🧪 アイテム図鑑 & 合成ツリー
- ゲーム内ショップ風の合成素材（Builds From）および派生先（Builds Into）の相互ナビゲーション
- 14種類のステータス（AD, AP, HP, AR, MR, AHなど）による複数AND検索
- ひらがな検索（「てぃあまと」「どらん」など）対応

---

## 📱 スマホへのインストール方法 (PWA)

1. スマホのブラウザ（iOS Safari または Android Chrome）で [https://burigori3103.github.io/LoLDB/](https://burigori3103.github.io/LoLDB/) にアクセス
2. **iOS Safari の場合**: 画面下の「共有」ボタン ➔「ホーム画面に追加」
3. **Android Chrome の場合**: 画面右上のメニュー ➔「アプリをインストール」または「ホーム画面に追加」
4. ホーム画面にアイコンが追加され、ネイティブアプリ同様に全画面・オフラインで利用可能になります。

---

## 🛠️ 技術スタック & アーキテクチャ

- **フロントエンド**: 単一HTML（Vanilla JS + CSS3 + Tailwind配色）、Service Worker（Cache-First / Dual Cache Architecture）
- **データ収集・生成パイプライン (Python)**:
  - `fetch_champions.py`: 公式Data Dragon APIからの基礎データ抽出
  - `process_url_list.py`: OP.GG / Wikiからの統計・立ち回りデータ取得
  - `merge_data.py`: マスターデータの統合・ロール別最適化
  - `build_pwa.py`: 単一HTML（`dist/index.html` およびルート `index.html`）およびService Worker、マニフェストの自動生成
- **ホスティング**: GitHub Pages（`git push` で自動反映）

---

## 📄 ライセンス & 免責事項

本ツールは Riot Games の公式製品ではなく、Riot Games または League of Legends の制作・管理に関与するいかなる組織とも提携していません。League of Legends および Riot Games は Riot Games, Inc. の商標または登録商標です。
