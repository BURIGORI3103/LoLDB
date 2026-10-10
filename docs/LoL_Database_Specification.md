---
tags:
  - LoLDB
---
League of Legends 攻略データベース自動収集・統合システム 仕様書
​作成日: 2026-10-02
対象パッチ: 最新パッチ対応型

​【1. システム概要】
​本システムは、League of Legends（LoL）に登場する全チャンピオンの基本ステータス、スキル情報、推奨サモナースペル、推奨ビルド、ルーン構成、有利不利な対面相性、立ち回りメモを自動で収集・統合し、オフライン環境（スマートフォンおよびPC）で快適に閲覧できる単一Webアプリケーション（PWA）の基礎データを構築するための仕組みです。
公式データ、統計サイト、攻略wikiの各長所を抽出し、単一のマスターデータ（all_champions.json）へと集約します。  

​【2. 設計方針とアーキテクチャ選定理由】
​・Obsidian単体管理を採用しない理由
マークダウンファイルによる管理はデータ量（160体以上）が増えると端末同期の競合や動作遅延が発生しやすくなります。また、OP.GGのような視覚的なカード型UIをスマートフォン上で再現するにはプラグイン負荷が大きすぎるため、最終閲覧環境は単一HTMLによるPWA（プログレッシブウェブアプリ）を採用します。  

​・AIによる手作業登録（Gemini Notebook）を自動化へ切り替えた理由
初期構想ではGemini NotebookにURLを1件ずつ投入して要約させる方式を検討しましたが、登録件数上限の制限に抵触すること、および手作業による人為的ミスやフォーマット崩れが多発することから廃止しました。データ収集はすべてAntigravity（Python実行環境）による自動スクレイピングおよびAPI通信へ移行しています。  

​・旧スクリプトの廃止と一本化
初期に検討していた旧スクリプト（fetch_opgg_strategy.py）はOP.GGの取得のみを担当していましたが、後から開発したURLリスト連携スクリプト（process_url_list.py）がURLリスト（LoL_URL_list.md）の参照、進捗チェックボックスの自動更新、日本語wikiからの立ち回り抽出機能を内包した上位互換となったため、完全廃止としました。

​【3. ディレクトリ構成】
​ローカルPC（Cドライブ直下）における正式なディレクトリ構成は以下の通りです。
​C:\Project\LoLDB
│
├─ docs\ （設計資材格納フォルダ）
│   ├─ LoL_Database_Specification.md
│   ├─ LoL_URL_list.md
│   ├─ 01_fetch_champions.py.md
│   ├─ 02_process_url_list.py.md
│   ├─ 03_merge_data.py.md
│   └─ Patchnote_URL.md
│
├─ fetch_champions.py （docsから抽出・実体化）
├─ process_url_list.py （docsから抽出・実体化）
├─ merge_data.py （docsから抽出・実体化）
├─ build_pwa.py （後続の単一HTML生成用スクリプト）
│
├─ champions_data\ （fetch_champions.pyの出力先JSON群）
├─ strategy_data\ （process_url_list.pyの出力先JSON群）
├─ merged_data\ （merge_data.pyの出力先）
│   └─ all_champions.json （統合マスターデータ）
└─ dist\ （完成アプリ出力先）
├─ index.html （オフライン動作Webアプリ本体）
└─ sw.js （Service Workerキャッシュスクリプト）

​【4. 実行手順と各コンポーネントの役割】
​ステップ1：公式基礎データの取得
実行ファイル：fetch_champions.py
役割：Riot Gamesが提供する公式Data Dragonのエンドポイントへアクセスし、全チャンピオンの基本ステータス（体力、攻撃力、防御力等）、スキル詳細テキスト、クールダウン、消費リソース、画像ファイル名を一括取得します。
出力先：champions_data フォルダ（Aatrox.json, Garen.json など）  

​ステップ2：統計攻略データの収集と進捗更新
実行ファイル：process_url_list.py
役割：docs/LoL_URL_list.md を上から読み込み、未チェック（- [ ]）のチャンピオンに対して順次処理を行います。  
​OP.GGから最新のサモナースペル、コアアイテム、推奨靴、スタートアイテム、ルーンツリー、対面勝率データを取得し、公式日本語辞書と照合して日本語名へ自動変換します。  
​OP.GGの統計から実際に運用されているポジション（TOP、JUG、MID、ADC、SUP）を抽出し、正規化して保持します。  
​日本語wikiから立ち回り概要テキストを抽出します。  
​取得結果を strategy_data フォルダに保存します。  
​処理が正常終了した行のチェックボックスを（- [x]）へ自動更新します。途中で通信が中断しても、再実行時は未チェック行から即座に再開可能です。
出力先：strategy_data フォルダ  

​ステップ3：データの結合とマスターファイル出力
実行ファイル：merge_data.py
役割：champions_data（公式基礎値）と strategy_data（攻略統計値）をチャンピオンIDをキーにして突合し、完全な構造体として統合します。
公式側のクラス情報（FighterやTankなど）は破棄し、process_url_list.py で取得した実運用レーン情報（TOPやMIDなど）でrolesを上書きします。また、サモナースペル情報も追加統合します。攻略データが未取得のチャンピオンが存在する場合でも、空のテンプレートを補完してエラー落ちを防ぎます。
出力先：merged_data/all_champions.json  

​【5. 最終統合データ（JSON）のスキーマ定義】
​all_champions.json 内の各チャンピオンオブジェクトは以下の完全な構造を持ちます。ガレンの全スキル（パッシブおよびQ・W・E・R）と現行メタの推奨アイテムを適用した完全な見本です。  

{
  "id": "Garen",
  "name": "ガレン",
  "title": "デマーシアの勇士",
  "patch": "14.20.1",
  "roles": ["TOP"],
  "resource": "なし",
  "summoner_spells": ["フラッシュ", "イグナイト"],
  "stats": {
    "hp": 690,
    "hp_growth": 98,
    "attack_damage": 69,
    "ad_growth": 4.5,
    "armor": 38,
    "magic_resist": 32,
    "attack_range": 175
  },
  "abilities": [
    {
      "slot": "Passive",
      "name": "タフガイ",
      "description": "一定時間ダメージを受けずにいると、最大体力の一定割合を毎秒回復する。",
      "image": "Garen_Passive.png"
    }
  ],
  "spells": [
    {
      "slot": "Q",
      "name": "断固たる一撃",
      "description": "自身にかかっているすべてのスロウ効果を解除し、移動速度が増加する。次の通常攻撃が強化され、追加物理ダメージを与えて対象にサイレンスを付与する。",
      "cooldown": "8",
      "cost": "0",
      "image": "GarenQ.png"
    },
    {
      "slot": "W",
      "name": "勇気の護り",
      "description": "敵ユニット撃破時に物理防御と魔法防御が恒久的に増加する。発動すると短時間シールドと行動妨害耐性を得て、被ダメージを軽減する。",
      "cooldown": "23/21/19/17/15",
      "cost": "0",
      "image": "GarenW.png"
    },
    {
      "slot": "E",
      "name": "ジャッジメント",
      "description": "剣を構えて高速回転し、周囲の敵に複数回物理ダメージを与える。最も近くにいる敵にはダメージが増加し、複数回命中した敵の物理防御を低下させる。",
      "cooldown": "9",
      "cost": "0",
      "image": "GarenE.png"
    },
    {
      "slot": "R",
      "name": "デマーシアの正義",
      "description": "敵チャンピオンにデマーシアの正義をもたらし、対象の減少体力に応じた確定ダメージを与える。",
      "cooldown": "120/100/80",
      "cost": "0",
      "image": "GarenR.png"
    }
  ],
  "matchups": {
    "favorable": [
      { "champion_id": "Nasus", "name": "ナサス", "reason": "勝率 53.8%（統計的に有利）" },
      { "champion_id": "Jax", "name": "ジャックス", "reason": "勝率 52.4%（統計的に有利）" },
      { "champion_id": "Riven", "name": "リヴェン", "reason": "勝率 51.9%（統計的に有利）" }
    ],
    "unfavorable": [
      { "champion_id": "Camille", "name": "カミール", "reason": "勝率 47.1%（統計的に不利）" },
      { "champion_id": "Darius", "name": "ダリウス", "reason": "勝率 46.5%（統計的に不利）" },
      { "champion_id": "Kayle", "name": "ケイル", "reason": "勝率 45.8%（統計的に不利）" }
    ]
  },
  "build": {
    "starter": [
      { "item_id": "1055", "name": "ドラン ブレード" },
      { "item_id": "2003", "name": "体力ポーション" }
    ],
    "boots": [
      { "item_id": "3006", "name": "バーサーカー ブーツ", "condition": "攻撃速度と回転数重視（標準）" },
      { "item_id": "3047", "name": "プレート スチールキャップ", "condition": "敵ADが重い場合" }
    ],
    "core": [
      { "step": 1, "item_id": "6631", "name": "ストライドブレイカー", "description": "接近力強化とスロウ付与の最重要アイテム" },
      { "step": 2, "item_id": "3046", "name": "ファントム ダンサー", "description": "移動速度と攻撃速度の確保" },
      { "step": 3, "item_id": "3071", "name": "ブラック クリーバー", "description": "物理防御低下と体力・攻撃力の向上" }
    ],
    "situational": [
      { "item_id": "3143", "name": "ランデュイン オーメン", "condition": "敵のクリティカル火力が高い場合" },
      { "item_id": "4401", "name": "自然の力", "condition": "敵の継続魔法ダメージが重い場合" }
    ]
  },
  "runes": {
    "primary": {
      "path": "魔道",
      "keystone": "8230",
      "keystone_name": "フェイズラッシュ",
      "choices": ["ニンバスクローク", "追い風", "強風"]
    },
    "secondary": {
      "path": "不撓",
      "choices": ["息継ぎ", "過剰成長"]
    },
    "shards": ["アダプティブフォース", "移動速度", "体力（レベル比例）"]
  },
  "gameplay_notes": {
    "laning": "序盤は相手のスキル使用後にQで接近しEでトレードを行う。体力が減ったらパッシブで回復してレーン戦を有利に進める。",
    "teamfight": "ストライドブレイカーとQの加速を活かして敵後衛キャリーに張り付き、沈黙と高火力EからのRで確実に仕留める。"
  }
}

【6. 今後の開発展開（Webアプリ化）】
​生成された all_champions.json を読み込み、Tailwind CSSを用いたダークテーマの単一HTMLファイルをAntigravityで生成します。
roles（TOP、JUG、MID、ADC、SUP）を用いたタブ切り替えフィルター、名前検索バー、対面相性カードを配置し、Service Workerを登録して完全オフライン動作を実現します。