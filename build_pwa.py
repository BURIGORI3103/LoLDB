"""
build_pwa.py - 統合マスターデータを内包したオフラインPWAアプリケーションの生成
================================================================================
merged_data/all_champions.json をインラインで内包し、
完全オフライン動作可能な単一HTML（dist/index.html）および
Service Worker（dist/sw.js）、PWAマニフェスト（dist/manifest.json）を構築します。
"""

import json
import os
import hashlib
import html
import re
import zipfile
from pathlib import Path

# 過去バージョンの詳細箇条書き定義（Update_History.md側が1段落要約のみの古いエントリをリッチ表示するための補完辞書）
CURATED_CHANGELOG_ITEMS = {
    "v2.5.2": [
        "【サステイン絞り込み機能の修正＆公式スキル解析】全173体のスキル・パッシブ説明文から体力回復（吸血・リジェネ強化）・自己シールド能力を厳密解析しDBへ格納。サステイン絞り込みでヒット数0になっていた不具合を解消（全99体が正常ヒット）",
        "【詳細モーダルへのサステイン情報反映】チャンピオン詳細画面に対象スキルの名称や回復・シールド特性、重傷推奨ガイダンスを正確に表示",
    ],
    "v2.5.1": [
        "【アプリ上部ヘッダーバッジのバージョン同期】ページ上部のバージョンバッジ（#patchBadge）およびアップデート履歴モーダルの表示を同期",
        "【Service Workerキャッシュ更新】ブラウザ側で最新の更新履歴が即時反映されるようコアキャッシュを更新",
    ],
    "v2.5.0": [
        "【AA通常攻撃タイプ判定・バッジ表示】外部推測・ハルシネーションを排除し、公式ステータス（stats.attackrange）のみに基づいて全173体を厳密判定。カード画像右上に属性バッジ（[AD]等）と並び、AAタイプバッジ（[🗡️ 近接] / [🏹 遠隔] / [🔄 両用]）を常時表示",
        "【詳細画面へのAA射程情報追加】チャンピオン詳細モーダル上部にも「🎯 通常攻撃 (AA): 近接 (メレー) [射程 175]」のように射程・特性の詳細を明記",
        "【多機能複合絞り込みフィルター新設】チャンピオン一覧および対面シミュレーターピッカーに、通常攻撃（近接/遠隔/両用）、ダメージ属性（AD/AP/TANK）、特性（サステイン所持/両型あり）をワンタップで絞り込めるチップスバーを追加。ロールや検索クエリとのAND複合検索に対応",
        "【シミュレーターピッカーへのミニアイコン表示】ピッカー内のチャンピオンにもAAタイプ（🗡️/🏹/🔄）と属性を表示し、五十音順（あいうえお順）ソートを維持したまま直感的に選べるよう改善",
        "【パイプライン恒久統合】データ更新スクリプトにAAタイプ判定を組み込み、今後のパッチ更新時にも自動付与を保証",
    ],
    "v2.4.1": [
        "【配布用ZIP出力先のプロジェクト直下集約】配布用ZIP（LoLDB_dist.zip等）の生成・管理をプロジェクト直下（c:\\Project\\LoLDB\\）に統一し、デスクトップへの自動出力を廃止",
    ],
    "v2.4.0": [
        "【全173体最新パッチ環境データ完全更新】最新パッチ統計出揃いに伴い、Data Dragon基礎データ再取得、OP.GG統計および日本語wiki攻略データの再収集・統合を完遂",
        "【全対面1行戦術理由の自動生成・同期】全チャンピオンの対面戦術理由およびオフラインPWAを最新パッチ環境へ再ビルド",
    ],
    "v2.3.1": [
        "【旧URL向け移転案内パッケージ新設】旧ホスティング（Netlify等）専用の移転案内UI・自動リダイレクト・旧SWキャッシュ一括クリアを備えた配布パッケージ（dist_old_url_migration）を新設",
    ],
    "v2.3.0": [
        "【マッチアップ正規スキーマ移行・勝率と戦術理由の厳格分離】チャンピオン詳細モーダルにおいて、勝率バッジと「何のスキル・特性でどう立ち回るか」の具体的戦術理由を完全に独立した表示へ分離",
        "【ロール別マッチアップの同期・正確性向上】ロール切り替え（TOP/JUG/MID/ADC/SUP）時に、選択中ロール固有の対面データを正確に表示するよう同期・改善",
        "【ハッシュ疑似勝率の完全撤廃】対面シミュレーターにおいて、実測データがない場合の疑似勝率算出を廃止し、「推定有利」「推定警戒・不利」「推定五分」と明記して実測統計と明確に区別",
        "【安全なテキスト描画】HTMLエスケープ処理を導入し、チャンピオン名や戦術理由テキストを安全かつ確実にレンダリング",
    ],
    "v2.2.0": [
        "【GitHub Pages公開＆クラウド完全移行】本番公開先をGitHub Pages（https://burigori3103.github.io/LoLDB/）へ完全移行。サブパスでのPWA動作およびService Workerキャッシュを最適化",
        "【.nojekyll自動配備＆README新設】GitHub Pages用の静的配信構成を整え、オフラインPWAとしての自動更新と安定性を強化",
    ],
    "v2.1.1": [
        "【キャラの強み・弱み項目の完全復元】パッチ16.20更新時にマージ不備で欠落していた全173体の特徴・要約・強み（Strengths 3項目）・弱み（Weaknesses 3項目）を完全復元・再搭載",
        "【対面相性の詳細理由の完全復元】パッチ更新で消失していた対面相性の実戦的解説文（「なぜ有利なのか」「なぜ不利なのか」の理由テキスト）を全173体・1036件すべて復元",
        "【表示耐性・フォールバック強化】相性理由の分割処理を改修し、理由テキストが絶対に抜け落ちないよう堅牢化。強み・弱み項目も多重防御で恒久保証",
    ],
    "v2.1.0": [
        "【公式パッチ 16.20.1（26.20）完全対応】全173体のチャンピオン基礎ステータス・スキル詳細および全283個のアイテムデータを最新パッチ16.20.1に完全アップデート",
        "【Worldsバランシング反映】アンベッサのパッシブ調整、アッシュの基本AD低下、ダイアナのWシールド強化、ケネンのE攻撃速度Buff、キンドレッドのW/E強化等を完全網羅",
        "【アイテムデータ最新化】ロケットベルトのNerfを含むサモナーズリフト全アイテムの最新ステータス・価格・合成ツリーを同期",
    ],
    "v2.0.1": [
        "【対面シミュレーターの有利・不利判定の修正】大文字小文字の照合不一致を修正し、個別収集データ（ウディア vs エイトロックス等）を最優先反映。「有利」「警戒・不利」「互角・五分」をシンプルかつ確実に判定・表示するよう改善",
        "【勝率％数値の非表示化】パーセンテージ数値を排し、実戦的で分かりやすい3分類（有利 / 警戒・不利 / 互角・五分）と具体的な相性理由に特化",
        "【アイテム図鑑のステータスアイコン・絵文字の完全撤廃】カテゴリタブ、サイドバー絞り込み、詳細モーダル内のステータス一覧からすべての絵文字やアイコンを削除し、見やすくクリーンなテキスト表示へ変更",
    ],
    "v2.0.0": [
        "【対面シミュレーターの勝率・有利不利を100%完全網羅】全173体×全173体（約3万通り）の対面マトリクスデータベースを完全搭載！五分ばかりの表示を解消し、対面勝率（%）と実戦的な相性理由を全対面で確実に表示",
        "【ピッカー選択画面のあいうえお順（五十音順）ソート】自キャラ・敵キャラ選択画面を日本語五十音順で並べ替え、直感的に探せるよう改善",
        "【すべての検索窓でひらがな＆部分一致検索に対応】メイン検索・ピッカー検索・アイテム検索の全検索窓で「がれん」「せと」「どらん」等のひらがな入力や部分文字列検索に対応",
        "【アイテム図鑑の大幅進化・スタートアップ新設】ドラン系、涙、ペット、ポーション等を網羅した「🧪 スタートアップ」ジャンルを新設",
        "【ステータス複数チェックボックス絞り込み】UI左側にステータス一覧（AD, AP, AS, AR, MR, HP, AH等）をチェックボックス配置し、複数選択（AND検索）での絞り込みが可能に",
        "【ゲーム内ショップ風 合成ツリー (Builds From & Into)】アイテム詳細モーダル上部に、合成素材と派生先上位アイテムをカード形式で大きく表示。タップで自由に相互ジャンプ可能に",
    ],
    "v1.9.0": [
        "【AD/APダメージ属性の一目判別】全173体のチャンピオンカードおよび詳細画面に「AD (物理)」「AP (魔法)」「AD/AP (ハイブリッド)」「TANK」の属性バッジを明記",
        "【AD/AP両型対応 ＆ ビルド別属性表記】カタリナ、ヴァルス、マルファイト、ケイル、トゥイッチ、ボリベア等の両型持ちに注意アラートを新設。推奨ビルド名に[AD][AP][TANK]を明記",
        "【対面時の防具選択ガイド】「相手がADならAR（物理防御）」「相手がAPならMR（魔法耐性）」を積むべき明確な指針を詳細画面・シミュレーターに表示",
        "【対面シミュレーターから詳細・スキル確認へ1タップジャンプ】シミュレーターでピックした自分・相手のカードに「🔍 スキル・詳細を見る」ボタンを新設。ワンタップでスキル仕様やコンボを確認可能",
    ],
    "v1.8.0": [
        "【実戦コンボのQWER表記化・職人技網羅】全チャンピオンのコンボ表記をスキル名から「Q/W/E/R/AA/Flash」へと統一。ガレンのAA➜Q➜E➜W➜RやセトのW詠唱中Flash軸合わせ直撃など実戦的かつ高レート直伝のテクニックを網羅",
        "【サモナースペル上位2セット表示】最高採用率の王道セット（TP+Flash等）と攻撃的・対面別セット（Ignite+Flash等）の上位2セットを並べて表示",
        "【スキル取得順テーブル (Lv 1〜18)】各レベルでどのスキルを取得するかが一目で分かる横スクロール対応マトリクス表を新設",
        "【レーン別立ち回り・スキルの吐きどころ刷新】レーン定型文を廃止し、チャンピオン固有スキル特性を活かした実戦的ガイドに全面刷新",
        "【対面シミュレーターの推奨アイテム拡充】対面属性・サステイン対策、主戦力コア、生存保険アイテムを網羅した実戦的複数アイテム提示に進化",
        "【オフライン閲覧時の画像表示根本修正】Service Workerの2層キャッシュ化（画像永続キャッシュ）とopaqueレスポンス対応、および全アイコン自動プリフェッチにより、オフラインでもガレンアイコンに化けず全画像が正常表示されるよう修正",
    ],
    "v1.7.3": [
        "【スキル順・立ち回り・ルーン・相性の全同期】全78体の複数ロール持ちチャンピオンにおいて、ロールタブ切替時にスキル上げ順、序盤/集団戦の立ち回りメモ、推奨ルーン構成、レーン専用の対面相性（有利/不利）が完全同期されるよう全面改修",
        "【ジャングル/サポート/ADC/MID/TOP完全個別化】JUGは巡回立ち回りと対面ジャングラー相性、SUPは視界支配立ち回りとサポート対面相性、MID/ADC/TOPも各レーン固有の攻略情報へと美しく切り替え可能",
    ],
    "v1.7.2": [
        "【ロール別アイテムビルド完全同期】エイトロックスのジャングル（JUG）をはじめ、全78体の複数ロール持ちチャンピオンの全レーンにおいて、スタートアイテム・靴・コアアイテム・スペルを各ロール専用に完全最適化",
        "【ジャングル/サポート適正化】JUGロールはジャングルペット（モスストンパー/ガストウォーカー/スコーチクロウ＋スマイト）、SUPロールはサポートアイテム（ワールド アトラス/セレスティアル/ザズ＝ザク等）を全チャンプに正確同期",
        "【レーン別立ち回り同期】TOP/MID/ADC/SUP/JUGのレーン特性とAP/AD属性に合わせた3パターンのビルド（標準・対面別・状況別）を完全同期",
    ],
    "v1.7.1": [
        "【アイテム基礎ステータス完全表示】アイテム図鑑の全アイテムに攻撃力・魔力・防御・体力・ヘイスト等のステータスおよび効果説明を表示",
        "【アイテムカテゴリ絞り込み修正】AD/AP/タンク/靴/サポート/消耗品の絞り込み判定を大幅改修し、0件になる問題を完全解消",
        "【アイテムカード改善】図鑑一覧カードに上昇ステータス要約バッジを表示し、一覧から一目で性能が分かるよう改良",
    ],
    "v1.7.0": [
        "【対面対策シミュレーター】自分と相手のチャンピオンを選択する対面リアルタイム分析エンジンを新設",
        "【ロール別絞り込み】ピッカーで自分・相手ともにレーン別（ALL/TOP/JUG/MID/ADC/SUP）にサクッと絞り込み可能",
        "【リアルタイム対策分析】対面勝率判定、相手のサステイン警告＆警戒スキル、積むべき対策アイテム、狙い目コンボを即座に提示",
        "【対策アイテムジャンプ】シミュレーター内の対策アイテムをタップすると即座にアイテム詳細モーダルへジャンプ可能",
    ],
    "v1.6.0": [
        "【スキル上げ順】全173体の最大化優先度（例: Q > E > W）をバッジ明記",
        "【サステイン＆重傷判定】強力な回復スキル所持者への「🩸 サステイン所持（対面時: 重傷推奨）」警告バッジと理由を新設",
        "【キャラ概要】全チャンピオンの特徴・強み3選（Strengths）・弱み3選（Weaknesses）を完全網羅",
        "【立ち回り＆スキル吐きどころ】定型文を一新し、レーン戦・集団戦・重要スキルの温存/吐きどころの極意を徹底解説",
        "【実戦コンボ】基本ショートトレード・オールイン・Flash併用テクニック（Q3+FlashやEQベイブレード等）を体系化",
        "【複数ビルドパターン】サイオン（対AD/対AP/脅威）をはじめとする状況別・対面別の複数アイテム構成切り替えに対応",
        "【複数ロールタブ】複数レーン適応チャンピオンのレーン別タブ切り替え（推奨スペル・役割・ビルド）を新設",
    ],
    "v1.5.0": [
        "【アイテム図鑑】サモナーズリフト現役全254アイテムのマスターデータベースを新設",
        "アイテム名・通称・効果検索、価格昇降順・名前順ソート、カテゴリ絞り込み（AD/AP/Tank/靴/サポート/消耗品）に対応",
        "アイテム詳細モーダル新設（価格・売却額・基本ステータス・パッシブ/アクティブ効果・素材/派生先ツリー完備）",
        "【アイテム詳細ジャンプ】チャンピオン詳細画面のアイテム（スタート・靴・コア）をタップすると、直接アイテム詳細へジャンプ可能に",
        "アイテム詳細モーダル内での素材・派生先タップによるスムーズなアイテム間ジャンプに対応",
    ],
    "v1.4.0": [
        "タイトルのシンプル化（「LoLDB」へ改名）とバージョンバッジの最適化",
        "メインナビゲーション（チャンピオン／アイテム図鑑／対面シミュレーター）の設置",
        "スマホのスワイプ戻るジェスチャーでアプリが終了せずトップに戻る History API 対応",
        "チャンピオン詳細を開いた際、必ず最上部からスクロール開始するよう修正",
        "本リリースノート（バージョン履歴）モーダル機能の新設",
    ],
    "v1.3.0": [
        "全173チャンピオンのOP.GG最新統計データを総ざらい再スクレイピング",
        "モルデカイザー(TOP)、アジール(MID)、カリスタ(ADC)、スレッシュ(SUP)等のロール誤認（ハルシネーション）完全根絶",
        "全件自動監査スクリプトによるロール整合性100%検証",
    ],
    "v1.2.0": [
        "全173チャンピオンの対面有利不利に「1行戦術理由（勝率％＋立ち回り）」を自動生成・付与",
        "セラフィーンの担当ロール是正（SUP/ADC）およびサポート推奨ビルドへの更新",
        "対面相性カードをスマホで読みやすい2段組デザインへUI刷新",
    ],
    "v1.1.0": [
        "Riot公式Data Dragon CDN連携による全スキル・アイテム・スペルのアイコン画像表示対応",
        "PWA Service Workerをオンライン時最新優先（Network-First）へ強化",
    ],
    "v1.0.0": [
        "LoLDB 初回正式リリース",
        "公式Data Dragon基礎データ ＋ OP.GG攻略統計 ＋ 日本語wiki立ち回り統合PWA",
        "完全オフライン動作対応（Service Worker + 単一HTML内包アーキテクチャ）",
    ],
}

VERSION_ICONS = {
    "v1.7.1": "🛡️",
    "v1.6.0": "⚡",
    "v1.5.0": "🛡️",
    "v1.4.0": "🚀",
    "v1.3.0": "🛡️",
    "v1.1.0": "🎨",
    "v1.0.0": "✨",
}


def _parse_version_tuple(ver_str: str) -> tuple[int, ...]:
    nums = [int(x) for x in re.findall(r"\d+", ver_str)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def _parse_markdown_update_block(block_text: str) -> dict | None:
    """UPDATE.md または Update_History.md の1ブロックから version, date, title, items を自動抽出する"""
    text = block_text.replace("\\n", "\n").strip()
    date_str = ""
    ver_str = ""
    title_str = ""

    m_top = re.search(r"### 📅 (\d{4}-\d{2}-\d{2})\s*\|\s*📢 アップデート \(([^)]+)\)", text)
    if m_top:
        date_str = m_top.group(1)
        ver_str = m_top.group(2).strip()

    for m_hdr in re.finditer(
        r"# アップデート（(\d{4})年(\d{1,2})月(\d{1,2})日\s*-\s*([^\s/]+)\s*/\s*(.+)）\s*$",
        text,
        flags=re.MULTILINE,
    ):
        if not date_str:
            date_str = f"{int(m_hdr.group(1)):04d}-{int(m_hdr.group(2)):02d}-{int(m_hdr.group(3)):02d}"
        ver_str = m_hdr.group(4).strip()
        title_str = m_hdr.group(5).strip()

    if not ver_str:
        return None
    if not ver_str.startswith("v"):
        ver_str = "v" + ver_str

    parts = re.split(r"^## 概要\s*$", text, flags=re.MULTILINE)
    body = parts[-1] if len(parts) > 1 else text

    items = []
    current_group = ""
    pending_bold_header = ""

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<!--") or line.startswith("# ") or line.startswith("### 📅") or line == "---":
            continue
        if line.startswith("本ファイルは、"):
            continue
        if re.match(r"^###\s+(主な|修正内容|概要)", line):
            continue

        m_num = re.match(r"^\d+\.\s*\*\*(.+?)\*\*[:：]?\s*(.*)$", line)
        if m_num:
            current_group = m_num.group(1).strip()
            rest = m_num.group(2).strip()
            if rest:
                items.append(f"【{current_group}】{rest}")
                current_group = ""
            continue

        m_b_only = re.match(r"^[-*]\s*\*\*(.+?)\*\*[:：]\s*$", line)
        if m_b_only:
            pending_bold_header = m_b_only.group(1).strip()
            continue

        m_b_inline = re.match(r"^[-*]\s*\*\*(.+?)\*\*[:：]\s*(.+)$", line)
        if m_b_inline:
            items.append(f"【{m_b_inline.group(1).strip()}】{m_b_inline.group(2).strip()}")
            continue

        m_bul = re.match(r"^[-*]\s+(.+)$", line)
        if m_bul:
            content = m_bul.group(1).strip()
            content = re.sub(r"\*\*(.+?)\*\*", r"\1", content)
            if current_group:
                items.append(f"【{current_group}】{content}")
                current_group = ""
            else:
                items.append(content)
            continue

        clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        if pending_bold_header:
            items.append(f"【{pending_bold_header}】{clean_line}")
            pending_bold_header = ""
        else:
            if title_str and not clean_line.startswith("【"):
                items.append(f"【{title_str}】{clean_line}")
            else:
                items.append(clean_line)

    if not items and title_str:
        items.append(title_str)

    return {
        "version": ver_str,
        "date": date_str or "2026-10-03",
        "title": title_str,
        "items": items,
    }


def load_and_render_changelog(base_dir: Path, dist_dir: Path) -> tuple[str, str]:
    """
    UPDATE.md、ObsidianのUpdate_History.md、およびdata/changelog_history.jsonを統合・自動パースし、
    最新バージョン文字列（例: 'v2.6.0'）と #changelogModal 内のHTMLリストを動的生成する。
    """
    entries_by_ver: dict[str, dict] = {}

    # 1. ローカル保存済み changelog_history.json があれば読み込む（単体環境用バックアップ）
    history_json_path = base_dir / "data" / "changelog_history.json"
    if history_json_path.exists():
        try:
            cached_list = json.loads(history_json_path.read_text(encoding="utf-8"))
            for item in cached_list:
                v = item.get("version", "")
                if v:
                    entries_by_ver[v] = item
        except Exception:
            pass

    # 2. Obsidian (XO) の全履歴マスター Update_History.md をパース
    xo_history_path = Path(r"C:\Project\graviXObsidian\Topics\LoLDB\Update_History.md")
    if xo_history_path.exists():
        xo_text = xo_history_path.read_text(encoding="utf-8")
        chunks = re.split(r"(?=### 📅 \d{4}-\d{2}-\d{2}\s*\|\s*📢 アップデート)", xo_text)
        for chunk in chunks[1:]:
            parsed = _parse_markdown_update_block(chunk)
            if parsed and parsed["version"] != "v0.1.0":
                v = parsed["version"]
                if v in CURATED_CHANGELOG_ITEMS and len(parsed["items"]) <= 1:
                    parsed["items"] = CURATED_CHANGELOG_ITEMS[v]
                elif v in CURATED_CHANGELOG_ITEMS and v in ("v2.5.0", "v2.5.2"):
                    parsed["items"] = CURATED_CHANGELOG_ITEMS[v]
                entries_by_ver[v] = parsed

    # 3. プロジェクト直下の最新 UPDATE.md を最優先でパース・反映
    local_update_path = base_dir / "UPDATE.md"
    if local_update_path.exists():
        u_text = local_update_path.read_text(encoding="utf-8")
        parsed_u = _parse_markdown_update_block(u_text)
        if parsed_u:
            v = parsed_u["version"]
            if v in CURATED_CHANGELOG_ITEMS and len(parsed_u["items"]) <= 1:
                parsed_u["items"] = CURATED_CHANGELOG_ITEMS[v]
            entries_by_ver[v] = parsed_u

    # 4. CURATED_CHANGELOG_ITEMS にあるが万が一ファイルから漏れていた過去バージョンを補完
    default_dates = {
        "v2.5.2": "2026-10-20", "v2.5.1": "2026-10-20", "v2.5.0": "2026-10-20",
        "v2.4.1": "2026-10-16", "v2.4.0": "2026-10-16", "v2.3.1": "2026-10-16",
        "v2.3.0": "2026-10-14", "v2.2.0": "2026-10-12", "v2.1.1": "2026-10-11",
        "v2.1.0": "2026-10-10", "v2.0.1": "2026-10-09", "v2.0.0": "2026-10-07",
        "v1.9.0": "2026-10-06", "v1.8.0": "2026-10-05", "v1.7.3": "2026-10-04",
        "v1.7.2": "2026-10-04", "v1.7.1": "2026-10-04", "v1.7.0": "2026-10-04",
        "v1.6.0": "2026-10-04", "v1.5.0": "2026-10-04", "v1.4.0": "2026-10-04",
        "v1.3.0": "2026-10-03", "v1.2.0": "2026-10-03", "v1.1.0": "2026-10-03",
        "v1.0.0": "2026-10-03",
    }
    for ver, c_items in CURATED_CHANGELOG_ITEMS.items():
        if ver not in entries_by_ver:
            entries_by_ver[ver] = {
                "version": ver,
                "date": default_dates.get(ver, "2026-10-03"),
                "title": "",
                "items": c_items,
            }

    # セマンティックバージョン降順（最新が先頭）でソート
    sorted_entries = sorted(
        entries_by_ver.values(),
        key=lambda e: (_parse_version_tuple(e["version"]), e.get("date", "")),
        reverse=True,
    )

    # ローカルおよびdistの data/changelog_history.json に保存（常に同期）
    for d_base in (base_dir / "data", dist_dir / "data"):
        d_base.mkdir(parents=True, exist_ok=True)
        (d_base / "changelog_history.json").write_text(
            json.dumps(sorted_entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    latest_version = sorted_entries[0]["version"] if sorted_entries else "v2.6.0"

    # HTMLの生成
    html_blocks = []
    for entry in sorted_entries:
        ver = entry["version"]
        date = entry.get("date", "")
        icon = VERSION_ICONS.get(ver, "⚔️")
        li_rows = []
        for it in entry.get("items", []):
            escaped_it = html.escape(it, quote=True)
            li_rows.append(f"              <li>{escaped_it}</li>")
        li_joined = "\n".join(li_rows)
        block_html = (
            f'          <div class="changelog-item">\n'
            f'            <div class="changelog-header">\n'
            f'              <span class="changelog-ver">{icon} {html.escape(ver)}</span>\n'
            f'              <span class="changelog-date">{html.escape(date)}</span>\n'
            f'            </div>\n'
            f'            <ul class="changelog-ul">\n'
            f'{li_joined}\n'
            f'            </ul>\n'
            f'          </div>'
        )
        html_blocks.append(block_html)

    return latest_version, "\n".join(html_blocks)

def build():
    base_dir = Path(__file__).resolve().parent
    master_file = base_dir / "merged_data" / "all_champions.json"
    items_file = base_dir / "merged_data" / "all_items.json"
    dist_dir = base_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not master_file.exists():
        print(f"エラー: マスターデータファイル {master_file} が見つかりません。")
        return

    print("マスターデータを読み込み中...")
    with open(master_file, "r", encoding="utf-8") as f:
        all_champs = json.load(f)

    all_items = {}
    if items_file.exists():
        print("アイテムデータを読み込み中...")
        with open(items_file, "r", encoding="utf-8") as f:
            all_items = json.load(f)
        print(f"合計 {len(all_items)} 件のアイテムデータを読み込みました。")

    print(f"合計 {len(all_champs)} 体のチャンピオンデータを読み込みました。")

    # パッチ番号をマスターデータから一元抽出
    first_champ = next(iter(all_champs.values()), {})
    build_patch = first_champ.get("patch", "16.20.1")
    short_patch = ".".join(build_patch.split(".")[:2])
    latest_version, changelog_items_html = load_and_render_changelog(base_dir, dist_dir)
    print(f"最新バージョン検出: {latest_version} (Patch {short_patch})")

    # 分割JSONファイルとしても data/ に出力
    for d_base in (dist_dir / "data", base_dir / "data"):
        d_base.mkdir(parents=True, exist_ok=True)
        (d_base / "champions.json").write_text(
            json.dumps(all_champs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        (d_base / "items.json").write_text(
            json.dumps(all_items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )

    def safe_json_for_script(obj) -> str:
        raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        return (
            raw.replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    # HTML <script> 内への安全なシリアライズ (</script> 等の混入を完全防止)
    json_str = safe_json_for_script(all_champs)
    items_json_str = safe_json_for_script(all_items)

    html_content = f"""<!DOCTYPE html>
<html lang="ja" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>LoLDB</title>
  <meta name="theme-color" content="#0f172a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="description" content="全チャンピオンのスキル、推奨ビルド、ルーン、レーン別対面相性を網羅した攻略PWA（コアデータ即時オフライン・画像オンデマンド＆段階キャッシュ対応）">
  <link rel="icon" type="image/png" href="icon.png">
  <link rel="apple-touch-icon" href="icon.png">
  <link rel="manifest" href="manifest.json">
  <style>
    :root {{
      --bg-base: #0b0f19;
      --bg-surface: #151d30;
      --bg-card: #1c2640;
      --bg-card-hover: #233152;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --accent: #f59e0b;
      --border: #2e3c5d;
      --favorable: #10b981;
      --unfavorable: #f43f5e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }}
    header {{
      background: linear-gradient(180deg, #162035 0%, #0e1626 100%);
      border-bottom: 1px solid var(--border);
      padding: 12px 16px;
      position: sticky;
      top: 0;
      z-index: 40;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    .header-container {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .logo-area {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .logo-badge {{
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      color: #fff;
      font-weight: 900;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 14px;
      letter-spacing: 1px;
    }}
    .app-title {{
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.5px;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .patch-badge {{
      font-size: 11px;
      background: #1e293b;
      color: #38bdf8;
      border: 1px solid #334155;
      padding: 3px 10px;
      border-radius: 9999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
    }}
    .patch-badge:hover {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }}
    .main-nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      border-bottom: 1px solid #1e293b;
      padding-bottom: 8px;
    }}
    .nav-tab {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .nav-tab:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}
    .nav-tab.active {{
      background: #1e293b;
      color: var(--primary);
      border-color: #334155;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }}
    .pick-guide {{ max-width: 1000px; margin: 20px auto; padding: 0 12px; }}
    .pick-guide p {{ color: #cbd5e1; line-height: 1.6; }}
    .pick-filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }}
    .pick-filters button {{ background: #1e293b; color: #e2e8f0; border: 1px solid #475569; border-radius: 8px; padding: 8px 12px; cursor: pointer; }}
    .pick-filters button.active {{ border-color: #38bdf8; color: #38bdf8; }}
    .pick-list {{ display: grid; gap: 8px; }}
    .pick-row {{ background: #172235; border: 1px solid #334155; border-radius: 10px; padding: 12px; }}
    .pick-row strong {{ color: #7dd3fc; }}
    .pick-choice-garen {{ color: #fcd34d; }}
    .pick-choice-mordekaiser {{ color: #d8b4fe; }}
    .pick-choice-malphite {{ color: #86efac; }}
    .pick-choice-olaf {{ color: #fda4af; }}
    .pick-row p {{ margin: 5px 0 0; }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .search-input {{
      flex: 1;
      min-width: 180px;
      background-color: #0b0f19;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-input:focus {{
      border-color: var(--primary);
    }}
    .role-tabs {{
      display: flex;
      gap: 4px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .role-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .role-btn:hover {{
      background: #1c2640;
      color: #fff;
    }}
    .role-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }}
    main {{
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 16px;
      flex: 1;
    }}
    .count-status {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 12px;
      font-weight: 500;
    }}
    .grid-container {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }}
    @media (min-width: 640px) {{
      .grid-container {{
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 16px;
      }}
    }}
    .champ-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
      display: flex;
      flex-direction: column;
    }}
    .champ-card:hover {{
      transform: translateY(-3px);
      border-color: var(--primary);
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }}
    .champ-card-img-wrap {{
      width: 100%;
      aspect-ratio: 1;
      background: #0b0f19;
      position: relative;
      overflow: hidden;
    }}
    .champ-card-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .champ-card-img-placeholder {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 32px;
      color: #475569;
      background: #111827;
    }}
    .role-badge-list {{
      position: absolute;
      top: 6px;
      left: 6px;
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }}
    .mini-badge {{
      font-size: 9px;
      font-weight: 800;
      padding: 2px 5px;
      border-radius: 4px;
      text-transform: uppercase;
      color: #fff;
      box-shadow: 0 2px 4px rgba(0,0,0,0.6);
    }}
    .badge-top {{ background-color: #dc2626; }}
    .badge-jug {{ background-color: #16a34a; }}
    .badge-mid {{ background-color: #2563eb; }}
    .badge-adc {{ background-color: #eab308; color: #000; }}
    .badge-sup {{ background-color: #9333ea; }}
    .badge-default {{ background-color: #475569; }}
    /* ダメージタイプバッジ (一覧カード右上 & 詳細モーダル用) */
    .damage-badge-wrap {{
      position: absolute;
      top: 6px;
      right: 6px;
      z-index: 2;
    }}
    .damage-badge {{
      font-size: 9.5px;
      font-weight: 900;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.7);
      backdrop-filter: blur(2px);
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }}
    .badge-ad {{
      background: rgba(220, 38, 38, 0.9);
      color: #fff;
      border: 1px solid #ef4444;
    }}
    .badge-ap {{
      background: rgba(147, 51, 234, 0.9);
      color: #fff;
      border: 1px solid #c084fc;
    }}
    .badge-hybrid {{
      background: linear-gradient(135deg, rgba(220, 38, 38, 0.92) 0%, rgba(147, 51, 234, 0.92) 100%);
      color: #fff;
      border: 1px solid #fbbf24;
    }}
    .badge-tank {{
      background: rgba(16, 185, 129, 0.9);
      color: #fff;
      border: 1px solid #34d399;
    }}
    /* カード右上バッジコンテナ (ダメージ属性 & AAタイプ) */
    .card-top-badges {{
      position: absolute;
      top: 6px;
      right: 6px;
      z-index: 2;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 3px;
    }}
    /* AA攻撃タイプバッジ (近接 / 遠隔 / 両用) */
    .attack-type-badge {{
      font-size: 9px;
      font-weight: 800;
      padding: 2px 5px;
      border-radius: 4px;
      letter-spacing: 0.3px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.7);
      backdrop-filter: blur(2px);
      display: inline-flex;
      align-items: center;
      gap: 2px;
      color: #fff;
    }}
    .badge-melee {{
      background: rgba(180, 83, 9, 0.92);
      border: 1px solid #f59e0b;
      color: #fef3c7;
    }}
    .badge-ranged {{
      background: rgba(2, 132, 199, 0.92);
      border: 1px solid #38bdf8;
      color: #e0f2fe;
    }}
    .badge-att-hybrid {{
      background: rgba(124, 58, 237, 0.92);
      border: 1px solid #a855f7;
      color: #f3e8ff;
    }}

    /* 多機能フィルターチップスバー (メイン一覧用 & シミュレーターピッカー用) */
    .filter-chips-bar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-top: 8px;
      padding: 6px 10px;
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 8px;
    }}
    .filter-group {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding-right: 8px;
      border-right: 1px solid rgba(255, 255, 255, 0.1);
    }}
    .filter-group:last-of-type {{
      border-right: none;
    }}
    .filter-label {{
      font-size: 11px;
      font-weight: 800;
      color: var(--text-muted);
      margin-right: 2px;
      white-space: nowrap;
    }}
    .chip-btn {{
      padding: 3px 9px;
      font-size: 11px;
      font-weight: 700;
      background: #1e293b;
      border: 1px solid #334155;
      color: #94a3b8;
      border-radius: 9999px;
      cursor: pointer;
      transition: all 0.15s ease;
      white-space: nowrap;
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }}
    .chip-btn:hover {{
      background: #334155;
      color: #f8fafc;
      border-color: #475569;
    }}
    .chip-btn.active {{
      background: var(--primary);
      color: #0b0f19;
      border-color: var(--primary-light);
      font-weight: 900;
      box-shadow: 0 0 8px rgba(200, 155, 60, 0.4);
    }}
    .chip-btn.toggle-chip.active {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 8px rgba(14, 165, 233, 0.4);
    }}
    .chip-reset-btn {{
      margin-left: auto;
      padding: 3px 8px;
      font-size: 10.5px;
      font-weight: 700;
      background: transparent;
      border: 1px dashed #475569;
      color: #94a3b8;
      border-radius: 9999px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .chip-reset-btn:hover {{
      border-color: #ef4444;
      color: #f87171;
    }}
    
    /* モーダル内AA表示 */
    .modal-attack-type-wrap {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      padding: 8px 12px;
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .modal-attack-type-desc {{
      font-size: 11.5px;
      color: var(--text-muted);
      margin-left: auto;
    }}
    .sim-picker-mini-badge {{
      position: absolute;
      bottom: 2px;
      right: 2px;
      font-size: 10px;
      padding: 1px 3px;
      border-radius: 3px;
      background: rgba(0, 0, 0, 0.75);
      line-height: 1;
    }}
    /* 詳細モーダル用ダメージ属性・防具対策ガイド */
    .modal-damage-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      padding: 8px 12px;
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
    }}
    .modal-damage-title {{
      font-size: 11px;
      font-weight: 800;
      color: var(--text-muted);
    }}
    .modal-damage-counter {{
      font-size: 11.5px;
      color: #38bdf8;
      font-weight: 700;
      margin-left: auto;
    }}
    .dual-build-alert {{
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: #fde68a;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 11.5px;
      line-height: 1.5;
      margin-bottom: 10px;
    }}
    /* 対面シミュレーター 詳細モーダルジャンプボタン */
    .sim-view-detail-btn {{
      background: #0284c7;
      color: #fff;
      border: 1px solid #38bdf8;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
      white-space: nowrap;
      margin-top: 4px;
    }}
    .sim-view-detail-btn:hover {{
      background: #0369a1;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.4);
    }}
    .champ-info {{
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .champ-name {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .champ-title {{
      font-size: 11px;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    /* モーダル */
    .modal-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 12px;
    }}
    .modal-overlay.open {{
      display: flex;
    }}
    .modal-content {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      width: 100%;
      max-width: 800px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0,0,0,0.7);
      display: flex;
      flex-direction: column;
      animation: modalSlide 0.2s ease-out;
    }}
    @keyframes modalSlide {{
      from {{ transform: scale(0.96) translateY(10px); opacity: 0; }}
      to {{ transform: scale(1) translateY(0); opacity: 1; }}
    }}
    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid var(--border);
      background: #111827;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .modal-title-wrap {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .modal-close-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 24px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      line-height: 1;
    }}
    .modal-close-btn:hover {{
      color: #fff;
      background: #1f2937;
    }}
    .modal-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    /* リリースノートスタイル */
    .changelog-list {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .changelog-item {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .changelog-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      padding-bottom: 6px;
    }}
    .changelog-ver {{
      font-weight: 800;
      font-size: 14px;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .changelog-date {{
      font-size: 11px;
      color: var(--text-muted);
    }}
    .changelog-ul {{
      list-style-type: disc;
      padding-left: 20px;
      font-size: 12.5px;
      color: #cbd5e1;
      line-height: 1.6;
    }}
    .detail-section {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
    }}
    .detail-heading {{
      font-size: 14px;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
      gap: 8px;
    }}
    .stat-box {{
      background: #101726;
      border: 1px solid #1e293b;
      padding: 8px;
      border-radius: 6px;
      font-size: 12px;
    }}
    .stat-label {{ color: var(--text-muted); font-size: 10px; margin-bottom: 2px; }}
    .stat-val {{ font-weight: 700; color: #fff; }}
    /* スキル */
    .skill-card {{
      display: flex;
      gap: 12px;
      padding: 10px;
      background: #101726;
      border-radius: 8px;
      margin-bottom: 8px;
      border: 1px solid #1e293b;
      align-items: flex-start;
    }}
    .skill-icon-wrap {{
      position: relative;
      width: 48px;
      height: 48px;
      border-radius: 8px;
      overflow: hidden;
      background: #0b0f19;
      flex-shrink: 0;
      border: 1px solid #334155;
    }}
    .skill-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .skill-slot-badge {{
      position: absolute;
      bottom: 0;
      right: 0;
      background: rgba(15, 23, 42, 0.9);
      color: #38bdf8;
      font-weight: 900;
      font-size: 11px;
      padding: 1px 4px;
      border-top-left-radius: 4px;
      border-left: 1px solid #0284c7;
      border-top: 1px solid #0284c7;
    }}
    .skill-content {{
      flex: 1;
    }}
    .skill-name {{
      font-weight: 700;
      font-size: 13px;
      margin-bottom: 4px;
      color: #fff;
    }}
    .skill-meta {{
      font-size: 11px;
      color: var(--accent);
      margin-bottom: 4px;
      font-weight: 600;
    }}
    .skill-desc {{
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.4;
    }}
    /* 相性カード */
    .matchups-container {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }}
    @media (min-width: 600px) {{
      .matchups-container {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    .matchup-col {{
      background: #101726;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid #1e293b;
    }}
    .matchup-item {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 10px 0;
      border-bottom: 1px solid #1e293b;
    }}
    .matchup-item:last-child {{ border-bottom: none; }}
    .matchup-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .matchup-champ-info {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .matchup-champ-img {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
      border: 1px solid #334155;
      background: #0b0f19;
      flex-shrink: 0;
    }}
    .matchup-champ-name {{
      font-weight: 700;
      font-size: 13px;
      color: #f1f5f9;
    }}
    .badge-fav {{
      color: var(--favorable);
      font-weight: 800;
      font-size: 12px;
      background: rgba(16, 185, 129, 0.12);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .badge-unfav {{
      color: var(--unfavorable);
      font-weight: 800;
      font-size: 12px;
      background: rgba(244, 63, 94, 0.12);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}
    .matchup-reason {{
      font-size: 11.5px;
      color: #cbd5e1;
      line-height: 1.45;
      background: #0b0f19;
      padding: 6px 10px;
      border-radius: 6px;
      border-left: 3px solid #38bdf8;
    }}
    /* ビルド */
    .build-group {{
      margin-bottom: 12px;
    }}
    .build-group-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}
    .item-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .item-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid #1e293b;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      color: #e2e8f0;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .item-pill:hover {{
      border-color: var(--primary);
      background: #1e293b;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.2);
    }}
    .item-img {{
      width: 24px;
      height: 24px;
      border-radius: 4px;
      object-fit: cover;
      flex-shrink: 0;
      border: 1px solid #334155;
    }}
    /* 複数ロール切り替えサブタブ */
    .modal-role-tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .modal-role-btn {{
      background: #101726;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}
    .modal-role-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .modal-role-btn.active {{
      background: #0284c7;
      border-color: var(--primary);
      color: #fff;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }}
    /* サステイン & スキル上げ優先度バッジ */
    .champ-highlight-badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 10px;
    }}
    .badge-sustain {{
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.4);
      color: #fb7185;
      font-weight: 800;
      font-size: 11.5px;
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .badge-skill-order {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: #38bdf8;
      font-weight: 800;
      font-size: 11.5px;
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .sustain-reason-box {{
      font-size: 11.5px;
      color: #cbd5e1;
      background: rgba(244, 63, 94, 0.08);
      border-left: 3px solid #f43f5e;
      padding: 6px 10px;
      border-radius: 6px;
      margin-bottom: 14px;
      line-height: 1.45;
    }}
    /* 特徴・強み・弱み */
    .overview-text {{
      font-size: 12.5px;
      color: #e2e8f0;
      line-height: 1.6;
      margin-bottom: 10px;
    }}
    .pros-cons-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }}
    @media (min-width: 600px) {{
      .pros-cons-grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    .pros-box {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 8px;
      padding: 10px;
    }}
    .cons-box {{
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: 8px;
      padding: 10px;
    }}
    .pros-cons-title {{
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .pros-title {{ color: var(--favorable); }}
    .cons-title {{ color: var(--accent); }}
    .pros-cons-ul {{
      list-style: none;
      font-size: 11.5px;
      color: #cbd5e1;
      line-height: 1.5;
    }}
    .pros-cons-ul li {{
      margin-bottom: 4px;
      position: relative;
      padding-left: 14px;
    }}
    .pros-box li::before {{
      content: "✓";
      color: var(--favorable);
      position: absolute;
      left: 0;
      font-weight: bold;
    }}
    .cons-box li::before {{
      content: "!";
      color: var(--accent);
      position: absolute;
      left: 0;
      font-weight: bold;
    }}
    /* 実戦コンボ */
    .combo-grid {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .combo-card {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
    }}
    .combo-name {{
      font-size: 12.5px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 4px;
    }}
    .combo-recipe {{
      font-size: 12px;
      font-weight: 700;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid rgba(56, 189, 248, 0.2);
      margin-bottom: 6px;
      word-break: break-all;
    }}
    .combo-desc {{
      font-size: 11.5px;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    /* 複数アイテムビルドタブ */
    .build-pat-tabs {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      margin-bottom: 10px;
      padding-bottom: 2px;
    }}
    .build-pat-btn {{
      background: #101726;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }}
    .build-pat-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .build-pat-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
    }}
    .build-pat-desc {{
      font-size: 12px;
      color: #cbd5e1;
      background: #0b0f19;
      border-left: 3px solid var(--accent);
      padding: 6px 10px;
      border-radius: 6px;
      margin-bottom: 10px;
      line-height: 1.4;
    }}
    /* 対面対策シミュレーター スタイル (Phase 4) */
    .sim-container {{
      max-width: 800px;
      margin: 0 auto;
      padding: 10px 0 40px;
    }}
    .sim-slots-wrap {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 20px;
    }}
    .sim-slot {{
      flex: 1;
    }}
    .sim-slot-label {{
      font-size: 12px;
      font-weight: 800;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}
    .sim-slot-card {{
      background: var(--bg-card);
      border: 2px dashed var(--border);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      transition: all 0.2s;
      min-height: 68px;
    }}
    .sim-slot-card:hover {{
      border-color: var(--primary);
      background: var(--bg-card-hover);
      transform: translateY(-2px);
    }}
    .sim-slot-card.selected {{
      border-style: solid;
      border-color: var(--primary);
      background: #151d30;
      box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    }}
    .sim-slot-icon-wrap {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      background: #0b0f19;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex-shrink: 0;
      border: 1px solid var(--border);
    }}
    .sim-slot-plus {{
      font-size: 24px;
      font-weight: 300;
      color: var(--text-muted);
    }}
    .sim-slot-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .sim-slot-info {{
      flex: 1;
      overflow: hidden;
    }}
    .sim-slot-name {{
      font-size: 13.5px;
      font-weight: 800;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .sim-slot-sub {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .sim-vs-wrap {{
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .sim-vs-badge {{
      background: #0b0f19;
      border: 2px solid var(--border);
      color: var(--accent);
      font-size: 12px;
      font-weight: 900;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }}
    .sim-result-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 14px;
    }}
    .sim-result-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .sim-result-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: #fff;
    }}
    .sim-adv-badge {{
      font-size: 12px;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 6px;
    }}
    .sim-adv-fav {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--favorable);
    }}
    .sim-adv-unfav {{
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.4);
      color: var(--unfavorable);
    }}
    .sim-adv-even {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: var(--accent);
    }}
    .sim-picker-controls {{
      margin-bottom: 12px;
    }}
    .sim-role-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .sim-role-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .sim-role-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
    }}
    .sim-picker-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
      gap: 8px;
      max-height: 50vh;
      overflow-y: auto;
      padding-right: 4px;
    }}
    .sim-picker-item {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 4px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: all 0.2s;
      text-align: center;
    }}
    .sim-picker-item:hover {{
      border-color: var(--primary);
      background: #1e293b;
      transform: translateY(-2px);
    }}
    .sim-picker-img {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      object-fit: cover;
    }}
    .sim-picker-name {{
      font-size: 11px;
      font-weight: 700;
      color: #f1f5f9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
    }}
    /* 対面シミュレーター 推奨アイテム複数グリッド表示 */
    .sim-items-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .sim-item-card {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .sim-item-card:hover {{
      border-color: var(--primary);
      background: #151e33;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}
    .sim-item-img {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      border: 1px solid #334155;
      flex-shrink: 0;
      object-fit: cover;
    }}
    .sim-item-info {{
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .sim-item-top {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .sim-item-tag {{
      font-size: 10px;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #38bdf8;
      white-space: nowrap;
    }}
    .sim-item-name {{
      font-size: 12.5px;
      font-weight: 700;
      color: #f1f5f9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .sim-item-reason {{
      font-size: 11px;
      color: var(--text-muted);
      line-height: 1.3;
    }}
    /* アイテム図鑑スタイル */
    .item-controls {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .item-controls-row {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .item-search-input {{
      flex: 1;
      min-width: 180px;
      background-color: #0b0f19;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .item-search-input:focus {{
      border-color: var(--primary);
    }}
    .item-sort-select {{
      background: #151d30;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      outline: none;
      cursor: pointer;
    }}
    .item-category-tabs {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .item-cat-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }}
    .item-cat-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .item-cat-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }}
    .items-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 12px;
    }}
    @media (min-width: 600px) {{
      .items-grid {{
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      }}
    }}
    .item-grid-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
      text-align: center;
    }}
    .item-grid-card:hover {{
      transform: translateY(-3px);
      border-color: var(--primary);
      box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    }}
    .item-card-icon {{
      width: 48px;
      height: 48px;
      border-radius: 8px;
      object-fit: cover;
      border: 1px solid #334155;
      background: #0b0f19;
    }}
    .item-card-name {{
      font-size: 12px;
      font-weight: 700;
      color: #f1f5f9;
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 30px;
    }}
    .item-card-price {{
      font-size: 11px;
      font-weight: 800;
      color: var(--accent);
      background: rgba(245, 158, 11, 0.12);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(245, 158, 11, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    .item-card-stats {{
      font-size: 10px;
      font-weight: 600;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid rgba(56, 189, 248, 0.2);
      padding: 3px 6px;
      border-radius: 4px;
      width: 100%;
      box-sizing: border-box;
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 32px;
      text-align: left;
    }}
    .stat-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: rgba(56, 189, 248, 0.12);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: #e0f2fe;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 700;
      margin-right: 6px;
      margin-bottom: 6px;
    }}
    /* スペル2セット表示 */
    .spells-sets-wrap {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .spell-set-card {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 12px;
    }}
    .spell-set-title {{
      font-size: 11px;
      font-weight: 800;
      color: #38bdf8;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    /* スキル取得順マトリクス表 */
    .skill-matrix-container {{
      margin-top: 10px;
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}
    .skill-matrix-scroll {{
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }}
    .skill-matrix-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      text-align: center;
      min-width: 520px;
    }}
    .skill-matrix-table th, .skill-matrix-table td {{
      padding: 6px 3px;
      border: 1px solid rgba(51, 65, 85, 0.4);
    }}
    .skill-matrix-table th {{
      background: #101726;
      color: var(--text-muted);
      font-weight: 700;
    }}
    .skill-matrix-table .sticky-col {{
      position: sticky;
      left: 0;
      background: #101726 !important;
      font-weight: 800;
      color: #fff !important;
      z-index: 2;
      width: 44px;
    }}
    .skill-point-active {{
      background: #0284c7 !important;
      color: #fff !important;
      font-weight: 800;
      border-radius: 4px;
    }}
    /* アイテム詳細モーダル */
    .item-detail-header-wrap {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .item-detail-big-icon {{
      width: 56px;
      height: 56px;
      border-radius: 10px;
      border: 2px solid var(--primary);
      object-fit: cover;
      background: #0b0f19;
      flex-shrink: 0;
    }}
    .recipe-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 6px;
    }}
    .recipe-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));
      gap: 8px;
      margin-top: 6px;
    }}
    .recipe-item-card {{
      display: flex;
      align-items: center;
      gap: 8px;
      background: #111827;
      border: 1px solid var(--border);
      padding: 6px 10px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .recipe-item-card:hover {{
      border-color: var(--primary);
      background: #1e293b;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
    }}
    .recipe-item-card img {{
      width: 32px;
      height: 32px;
      border-radius: 6px;
      border: 1px solid #334155;
      flex-shrink: 0;
      background: #0b0f19;
    }}
    .recipe-item-info {{
      display: flex;
      flex-direction: column;
      min-width: 0;
      overflow: hidden;
    }}
    .recipe-item-name {{
      font-size: 11.5px;
      font-weight: 700;
      color: #f1f5f9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .recipe-item-price {{
      font-size: 10.5px;
      font-weight: 800;
      color: var(--accent);
    }}
    .recipe-section-title {{
      font-size: 12px;
      font-weight: 800;
      color: var(--accent);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .recipe-item-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      color: #f1f5f9;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .recipe-item-pill:hover {{
      border-color: var(--primary);
      background: #1e293b;
    }}
    .recipe-item-pill img {{
      width: 20px;
      height: 20px;
      border-radius: 4px;
    }}
    /* アイテム図鑑 2カラムレイアウト & 左側ステータスフィルター */
    .items-layout-container {{
      display: flex;
      gap: 16px;
      align-items: flex-start;
    }}
    .item-stats-sidebar {{
      width: 210px;
      flex-shrink: 0;
      background: #111827;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      position: sticky;
      top: 130px;
      max-height: calc(100vh - 150px);
      overflow-y: auto;
    }}
    .stats-sidebar-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }}
    .stats-sidebar-title {{
      font-size: 12.5px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .stat-count-pill {{
      background: var(--primary);
      color: #fff;
      font-size: 10px;
      font-weight: 800;
      padding: 1px 6px;
      border-radius: 10px;
    }}
    .stat-clear-btn {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #f87171;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .stat-clear-btn:hover {{
      background: rgba(239, 68, 68, 0.3);
    }}
    .stats-filter-list {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .stat-chk-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: #cbd5e1;
      cursor: pointer;
      padding: 4px 6px;
      border-radius: 6px;
      transition: background 0.15s;
      user-select: none;
    }}
    .stat-chk-item:hover {{
      background: rgba(255,255,255,0.05);
      color: #fff;
    }}
    .stat-chk-item input {{
      accent-color: var(--primary);
      cursor: pointer;
      width: 14px;
      height: 14px;
    }}
    .items-main-area {{
      flex: 1;
      min-width: 0;
    }}
    @media (max-width: 768px) {{
      .items-layout-container {{
        flex-direction: column;
      }}
      .item-stats-sidebar {{
        width: 100%;
        position: static;
        max-height: none;
        padding: 10px;
      }}
      .stats-filter-list {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 4px;
      }}
    }}
    .item-step {{
      background: #0284c7;
      color: #fff;
      font-size: 10px;
      font-weight: 800;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    .spell-img {{
      width: 20px;
      height: 20px;
      border-radius: 4px;
      object-fit: cover;
      border: 1px solid #334155;
    }}
    /* ルーン */
    .rune-row {{
      font-size: 12px;
      margin-bottom: 6px;
      color: #e2e8f0;
      line-height: 1.4;
    }}
    .rune-title {{
      font-weight: 700;
      color: var(--accent);
      margin-right: 6px;
    }}
    .spells-badge-list {{
      display: flex;
      gap: 8px;
      margin-top: 4px;
      flex-wrap: wrap;
    }}
    .spell-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid #38bdf8;
      color: #38bdf8;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-container">
      <div class="header-top">
        <div class="logo-area">
          <span class="logo-badge">PWA</span>
          <span class="app-title">LoLDB</span>
          <span class="patch-badge" id="patchBadge" title="タップして更新履歴を表示">Patch {short_patch} / {latest_version} ℹ️</span>
        </div>
      </div>
      <nav class="main-nav">
        <button class="nav-tab active" data-tab="champions">👑 チャンピオン</button>
        <button class="nav-tab" data-tab="items">🛡️ アイテム図鑑</button>
        <button class="nav-tab" data-tab="simulator">⚔️ 対面シミュレーター</button>
        <button class="nav-tab" data-tab="picks">📋 チャンプピック早見表</button>
      </nav>
      <div class="controls" id="champControls">
        <input type="text" id="searchInput" class="search-input" placeholder="チャンピオン名・英語名・ひらがなで検索..." autocomplete="off">
        <div class="role-tabs">
          <button class="role-btn active" data-role="ALL">ALL</button>
          <button class="role-btn" data-role="TOP">TOP</button>
          <button class="role-btn" data-role="JUG">JUG</button>
          <button class="role-btn" data-role="MID">MID</button>
          <button class="role-btn" data-role="ADC">ADC</button>
          <button class="role-btn" data-role="SUP">SUP</button>
        </div>
        <!-- 複合絞り込みフィルターバー (AA近接/遠隔・AD/AP/タンク・特性) -->
        <div class="filter-chips-bar" id="champFilterBar">
          <div class="filter-group">
            <span class="filter-label">通常攻撃:</span>
            <button class="chip-btn active" data-filter="attack" data-val="ALL">すべて</button>
            <button class="chip-btn" data-filter="attack" data-val="MELEE">🗡️ 近接</button>
            <button class="chip-btn" data-filter="attack" data-val="RANGED">🏹 遠隔</button>
          </div>
          <div class="filter-group">
            <span class="filter-label">属性:</span>
            <button class="chip-btn active" data-filter="damage" data-val="ALL">すべて</button>
            <button class="chip-btn" data-filter="damage" data-val="AD">⚔️ AD</button>
            <button class="chip-btn" data-filter="damage" data-val="AP">🔮 AP</button>
            <button class="chip-btn" data-filter="damage" data-val="TANK">🛡️ タンク</button>
          </div>
          <div class="filter-group">
            <span class="filter-label">特性:</span>
            <button class="chip-btn toggle-chip" data-filter="trait" data-val="SUSTAIN" title="高サステイン・回復持ち">🩸 サステイン</button>
            <button class="chip-btn toggle-chip" data-filter="trait" data-val="DUAL" title="AD/AP両型対応ビルド">⚡ 両型あり</button>
          </div>
          <button class="chip-reset-btn" id="chipResetBtn" title="追加フィルターをリセット">リセット</button>
        </div>
      </div>
    </div>
  </header>

  <main>
    <!-- チャンピオン一覧ビュー -->
    <div id="viewChampions">
      <div class="count-status" id="countStatus">表示中: 0 体</div>
      <div class="grid-container" id="champGrid"></div>
    </div>

    <!-- アイテム図鑑ビュー (Phase 2 & 濱田くんの機能拡張) -->
    <div id="viewItems" style="display: none;">
      <div class="item-controls">
        <div class="item-controls-row">
          <input type="text" id="itemSearchInput" class="item-search-input" placeholder="アイテム名・通称・ひらがな（例: bc, 帽子, ドラン, 時計）で検索..." autocomplete="off">
          <select id="itemSortSelect" class="item-sort-select">
            <option value="price_desc">価格が高い順</option>
            <option value="price_asc">価格が安い順</option>
            <option value="name_asc">名前順</option>
          </select>
        </div>
        <div class="item-category-tabs">
          <button class="item-cat-btn active" data-cat="ALL">ALL</button>
          <button class="item-cat-btn" data-cat="STARTUP">スタートアップ</button>
          <button class="item-cat-btn" data-cat="AD">攻撃力(AD)</button>
          <button class="item-cat-btn" data-cat="AP">魔力(AP)</button>
          <button class="item-cat-btn" data-cat="TANK">防具・タンク</button>
          <button class="item-cat-btn" data-cat="BOOTS">靴</button>
          <button class="item-cat-btn" data-cat="SUPPORT">サポート</button>
          <button class="item-cat-btn" data-cat="CONSUMABLE">消耗品/その他</button>
        </div>
      </div>

      <!-- 2カラム構成: 左側ステータスフィルター + 右側アイテム一覧 -->
      <div class="items-layout-container">
        <aside class="item-stats-sidebar" id="itemStatsSidebar">
          <div class="stats-sidebar-header">
            <div class="stats-sidebar-title">
              <span>ステータス絞り込み</span>
              <span id="activeStatBadge" class="stat-count-pill" style="display:none;">0</span>
            </div>
            <button id="clearStatFiltersBtn" class="stat-clear-btn" type="button" title="全ステータスフィルターをクリア">全解除</button>
          </div>
          <div class="stats-filter-list">
            <label class="stat-chk-item"><input type="checkbox" value="AD" class="stat-filter-chk"><span>攻撃力 (AD)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="AP" class="stat-filter-chk"><span>魔力 (AP)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="AS" class="stat-filter-chk"><span>攻撃速度 (AS)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="AR" class="stat-filter-chk"><span>物理防御 (AR)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="MR" class="stat-filter-chk"><span>魔法防御 (MR)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="HP" class="stat-filter-chk"><span>体力 (HP)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="AH" class="stat-filter-chk"><span>スキルヘイスト</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="CRIT" class="stat-filter-chk"><span>クリティカル</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="MS" class="stat-filter-chk"><span>移動速度 (MS)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="LETHALITY" class="stat-filter-chk"><span>脅威 (Lethality)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="MAGICPEN" class="stat-filter-chk"><span>魔防貫通</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="VAMP" class="stat-filter-chk"><span>吸血/ヴァンプ</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="MANA" class="stat-filter-chk"><span>マナ (Mana)</span></label>
            <label class="stat-chk-item"><input type="checkbox" value="HPREGEN" class="stat-filter-chk"><span>体力自動回復</span></label>
          </div>
        </aside>

        <div class="items-main-area">
          <div class="count-status" id="itemCountStatus">表示中: 0 個</div>
          <div class="items-grid" id="itemsGrid"></div>
        </div>
      </div>
    </div>

    <div id="viewPicks" style="display: none;">
      <section class="pick-guide">
        <h2>チャンプピック早見表</h2>
        <p>ガレンの習熟度を優先。相性が僅差ならガレン、APが必要ならモルデカイザーも検討。オラフは習得後に選択。</p>
        <p>パッチ26.21を基準にした実戦用の暫定判断です。勝率を検証した統計表ではありません。相手チームにAPが多い場合はマルファイトを再検討してください。</p>
        <input id="pickSearch" class="search-input" type="search" placeholder="相手チャンピオン名で検索" aria-label="相手チャンピオン名で検索">
        <div class="pick-filters" aria-label="推奨チャンピオンで絞り込み">
          <button type="button" class="active" data-pick="すべて" aria-pressed="true">すべて</button><button type="button" data-pick="ガレン" aria-pressed="false">ガレン</button><button type="button" data-pick="モルデカイザー" aria-pressed="false">モルデカイザー</button><button type="button" data-pick="マルファイト" aria-pressed="false">マルファイト</button><button type="button" data-pick="オラフ" aria-pressed="false">オラフ</button>
        </div>
        <p id="pickCount" aria-live="polite"></p><div id="pickList" class="pick-list"></div>
        <h3>先出し・BANの目安</h3>
        <p>先出しはガレン。味方がAD過多ならモルデカイザーも候補。ガレンのBANはダリウスかカミール、モルデカイザーのBANはオラフかグウェンを検討。</p>
        <p>相手がモルデカイザーなら、習得後のオラフを検討。マルファイトは避けたい対面です。未習得のチャンピオンより、使い慣れたガレンを優先して構いません。</p>
      </section>
    </div>
    <!-- 対面シミュレータービュー (Phase 4 実装) -->
    <div id="viewSimulator" style="display: none;">
      <div class="sim-container">
        <!-- ピッカーエリア (自分 vs 相手) -->
        <div class="sim-slots-wrap">
          <!-- 自分のチャンピオン -->
          <div class="sim-slot" id="simSlotMe">
            <div class="sim-slot-label">👑 あなたのピック</div>
            <div class="sim-slot-card empty" id="simCardMe" onclick="openSimPicker('me')">
              <div class="sim-slot-icon-wrap">
                <div class="sim-slot-plus">+</div>
                <img id="simImgMe" class="sim-slot-img" src="" alt="" style="display: none;">
              </div>
              <div class="sim-slot-info">
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                  <div class="sim-slot-name" id="simNameMe">チャンピオンを選択</div>
                  <span id="simDamageBadgeMe" class="damage-badge" style="display: none;"></span>
                </div>
                <div class="sim-slot-sub" id="simRoleMe">タップして選択</div>
                <button id="simDetailBtnMe" class="sim-view-detail-btn" style="display: none;" onclick="viewSimChampDetail(event, 'me')">🔍 スキル・詳細を見る</button>
              </div>
            </div>
          </div>

          <div class="sim-vs-wrap">
            <div class="sim-vs-badge">VS</div>
          </div>

          <!-- 対面の相手チャンピオン -->
          <div class="sim-slot" id="simSlotOpp">
            <div class="sim-slot-label">👿 対面の相手ピック</div>
            <div class="sim-slot-card empty" id="simCardOpp" onclick="openSimPicker('opp')">
              <div class="sim-slot-icon-wrap">
                <div class="sim-slot-plus">+</div>
                <img id="simImgOpp" class="sim-slot-img" src="" alt="" style="display: none;">
              </div>
              <div class="sim-slot-info">
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                  <div class="sim-slot-name" id="simNameOpp">チャンピオンを選択</div>
                  <span id="simDamageBadgeOpp" class="damage-badge" style="display: none;"></span>
                </div>
                <div class="sim-slot-sub" id="simRoleOpp">タップして選択</div>
                <button id="simDetailBtnOpp" class="sim-view-detail-btn" style="display: none;" onclick="viewSimChampDetail(event, 'opp')">🔍 スキル・詳細を見る</button>
              </div>
            </div>
          </div>
        </div>

        <!-- 分析結果表示エリア -->
        <div id="simEmptyPrompt" style="padding: 40px 16px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 40px; margin-bottom: 10px;">⚔️</div>
          <div style="font-size: 14px; font-weight: 700; color: #fff;">自分と相手のチャンピオンを選択してください</div>
          <div style="font-size: 12px; margin-top: 4px;">相性・統計勝率・警戒スキル・対策アイテムを瞬時に分析します。</div>
        </div>

        <div id="simResultArea" style="display: none;">
          <!-- 1. 相性・勝率メーター (レーン別厳格分離 ＆ 実測/推定メタ情報明示) -->
          <div class="sim-result-card" id="simAdvantageCard">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; margin-bottom:8px;">
              <span class="sim-result-title">⚖️ レーン別 対面相性判定</span>
              <div class="role-tabs" id="simMatchupLaneTabs" style="margin:0;">
                <button class="chip-btn sim-lane-tab active" data-lane="AUTO">自動(主ロール)</button>
                <button class="chip-btn sim-lane-tab" data-lane="TOP">TOP</button>
                <button class="chip-btn sim-lane-tab" data-lane="JUG">JUG</button>
                <button class="chip-btn sim-lane-tab" data-lane="MID">MID</button>
                <button class="chip-btn sim-lane-tab" data-lane="ADC">ADC</button>
                <button class="chip-btn sim-lane-tab" data-lane="SUP">SUP</button>
              </div>
            </div>
            <div class="sim-result-header">
              <span id="simMatchupSourceTag" style="font-size:11px; color:var(--text-muted); font-weight:600;">判定区分: -</span>
              <span id="simAdvantageBadge" class="sim-adv-badge">判定中</span>
            </div>
            <div id="simAdvantageDesc" style="font-size: 13px; color: #e2e8f0; line-height: 1.5; margin-top: 6px;"></div>
            <div id="simAdvantageMeta" style="font-size: 11px; color: var(--text-muted); line-height: 1.4; margin-top: 8px; padding-top: 6px; border-top: 1px dashed var(--border);"></div>
          </div>

          <!-- 2. レーン戦の注意点 ＆ 相手の警戒スキル -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">⚠️ レーン戦の注意点 ＆ 警戒スキル</span>
            </div>
            <div id="simSustainWarning" style="display: none;" class="sustain-reason-box"></div>
            <div id="simLaningTips" style="font-size: 12.5px; color: #cbd5e1; line-height: 1.6; margin-top: 6px;"></div>
          </div>

          <!-- 3. 積むべき対策アイテムリスト -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">🛡️ 積むべき対策おすすめアイテム（タップで詳細）</span>
            </div>
            <div id="simItemList" class="sim-items-grid"></div>
          </div>

          <!-- 4. 狙い目コンボ ＆ 仕掛けどころ -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">🥊 有効なショートトレード ＆ 仕掛けどころ</span>
            </div>
            <div id="simCombosArea" class="combo-grid" style="margin-top: 8px;"></div>
          </div>
        </div>
      </div>
    </div>
  </main>

  <!-- アップデート履歴（リリースノート）モーダル -->
  <div class="modal-overlay" id="changelogModal">
    <div class="modal-content" style="max-width: 650px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 style="font-size: 17px; font-weight: 800; color: #fff;">📜 LoLDB アップデート履歴</h2>
        </div>
        <button class="modal-close-btn" id="changelogCloseBtn">&times;</button>
      </div>
      <div class="modal-body">
        <div class="changelog-list">
{changelog_items_html}
        </div>
      </div>
    </div>
  </div>

  <!-- 詳細モーダル -->
  <div class="modal-overlay" id="detailModal">
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 id="modalChampName" style="font-size: 18px; font-weight: 800;">チャンピオン名</h2>
          <span id="modalChampTitle" style="font-size: 12px; color: var(--text-muted);">二つ名</span>
        </div>
        <button class="modal-close-btn" id="modalCloseBtn">&times;</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>

  <!-- アイテム詳細モーダル -->
  <div class="modal-overlay" id="itemDetailModal" style="z-index: 120;">
    <div class="modal-content" style="max-width: 620px;">
      <div class="modal-header">
        <div class="item-detail-header-wrap">
          <img id="itemDetailIcon" class="item-detail-big-icon" src="" alt="" onerror="this.style.display='none';">
          <div>
            <h2 id="itemDetailName" style="font-size: 17px; font-weight: 800; color: #fff;">アイテム名</h2>
            <div id="itemDetailPrices" style="margin-top: 4px;"></div>
          </div>
        </div>
        <button class="modal-close-btn" id="itemDetailCloseBtn">&times;</button>
      </div>
      <div class="modal-body" id="itemDetailBody">
        <!-- 基本ステータス -->
        <div class="detail-section" id="itemDetailStatsSec">
          <div class="detail-heading">📊 基本ステータス</div>
          <div id="itemDetailStatsText" style="font-size: 13px; color: #e2e8f0; line-height: 1.6; font-weight: 600;"></div>
        </div>
        <!-- レシピツリー (ゲーム内ショップ風: ステータス直後に大きく配置) -->
        <div class="detail-section" id="itemDetailRecipeSec">
          <div class="detail-heading">🔨 合成ツリー (素材 ＆ 派生先)</div>
          <div class="recipe-tree-wrap">
            <div id="itemRecipeFromBox" style="margin-bottom: 12px;">
              <div class="recipe-section-title">🔽 合成素材アイテム (Builds From):</div>
              <div id="itemRecipeFromList" class="recipe-grid"></div>
            </div>
            <div id="itemRecipeIntoBox">
              <div class="recipe-section-title">🔼 派生先上位アイテム (Builds Into):</div>
              <div id="itemRecipeIntoList" class="recipe-grid"></div>
            </div>
          </div>
        </div>
        <!-- 効果説明 -->
        <div class="detail-section" id="itemDetailDescSec">
          <div class="detail-heading">✨ 特殊効果（パッシブ / アクティブ）</div>
          <div id="itemDetailDescText" style="font-size: 12.5px; color: #cbd5e1; line-height: 1.6; white-space: pre-line;"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- チャンピオン選択ピッカーモーダル (ロール絞り込み付き) -->
  <div class="modal-overlay" id="simPickerModal" style="z-index: 150;">
    <div class="modal-content" style="max-width: 650px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 id="simPickerTitle" style="font-size: 16px; font-weight: 800; color: #fff;">チャンピオンを選択</h2>
        </div>
        <button class="modal-close-btn" id="simPickerCloseBtn">&times;</button>
      </div>
      <div class="modal-body" style="padding: 12px;">
        <!-- 検索 ＆ ロール絞り込みタブ (濱田くんの重要指定！) -->
        <div class="sim-picker-controls">
          <input type="text" id="simSearchInput" class="item-search-input" placeholder="名前・英語名で検索..." autocomplete="off">
          <div class="role-tabs" style="margin-top: 8px;">
            <button class="sim-role-btn active" data-sim-role="ALL">ALL</button>
            <button class="sim-role-btn" data-sim-role="TOP">TOP</button>
            <button class="sim-role-btn" data-sim-role="JUG">JUG</button>
            <button class="sim-role-btn" data-sim-role="MID">MID</button>
            <button class="sim-role-btn" data-sim-role="ADC">ADC</button>
            <button class="sim-role-btn" data-sim-role="SUP">SUP</button>
          </div>
          <!-- ピッカー用AAタイプ＆属性絞り込み -->
          <div class="filter-chips-bar" style="margin-top: 6px; padding: 4px 8px;">
            <div class="filter-group">
              <span class="filter-label">AA:</span>
              <button class="chip-btn sim-chip-btn active" data-sim-filter="attack" data-val="ALL">すべて</button>
              <button class="chip-btn sim-chip-btn" data-sim-filter="attack" data-val="MELEE">🗡️ 近接</button>
              <button class="chip-btn sim-chip-btn" data-sim-filter="attack" data-val="RANGED">🏹 遠隔</button>
            </div>
            <div class="filter-group">
              <span class="filter-label">属性:</span>
              <button class="chip-btn sim-chip-btn active" data-sim-filter="damage" data-val="ALL">すべて</button>
              <button class="chip-btn sim-chip-btn" data-sim-filter="damage" data-val="AD">⚔️ AD</button>
              <button class="chip-btn sim-chip-btn" data-sim-filter="damage" data-val="AP">🔮 AP</button>
              <button class="chip-btn sim-chip-btn" data-sim-filter="damage" data-val="TANK">🛡️ タンク</button>
            </div>
          </div>
        </div>
        <div class="sim-picker-grid" id="simPickerGrid"></div>
      </div>
    </div>
  </div>

  <script>
    // 安全なテキスト描画用HTMLエスケープ
    function escapeHtml(str) {{
      if (str === null || str === undefined) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    }}

    // ビルド時一元管理パッチ番号
    const DEFAULT_PATCH = "{build_patch}";

    // インライン内包されたマスターデータ (<script>安全エスケープ済)
    const CHAMPIONS = {json_str};
    const ITEMS = {items_json_str};

    // クライアントサイド・ヒューリスティック特性推定エンジン (実測データがないペア・レーン用)
    function computeHeuristicMatchup(me, opp, role) {{
      const patch = me.patch || DEFAULT_PATCH;
      if (me.id === opp.id) {{
        return {{
          winrate: null,
          winrate_display: null,
          advantage: "even",
          advantage_label: "五分（ミラーマッチ）",
          reason: "同チャンピオン対決です。ルーン選択、スキルの命中率、ウェーブコントロール等の技量勝負になります。",
          source: "mirror",
          is_estimated: false,
          role: role || "ALL",
          patch: patch,
          estimation_factors: [],
          estimation_limitation: ""
        }};
      }}
      let score = 0;
      const meDp = me.damage_profile || {{}};
      const oppDp = opp.damage_profile || {{}};
      const meSustain = !!(me.sustain_info && me.sustain_info.has_sustain);
      const oppSustain = !!(opp.sustain_info && opp.sustain_info.has_sustain);
      const reasons = [];
      const factors = [];

      if (["Malphite", "Rammus"].includes(me.id) && oppDp.primary_type === "AD") {{
        score += 3;
        factors.push("対AD物理防御特化 (+3)");
        reasons.push("物理防御(AR)スケールにより、相手のAD物理ダメージを大幅に軽減できます");
      }} else if (["Malphite", "Rammus"].includes(opp.id) && meDp.primary_type === "AD") {{
        score -= 3;
        factors.push("相手の対AD物理防御特化 (-3)");
        reasons.push("相手の高い物理防御と通常攻撃反射により、ADダメージが通りにくい対面です");
      }}

      if (["Galio", "Kassadin"].includes(me.id) && oppDp.primary_type === "AP") {{
        score += 3;
        factors.push("対AP魔法耐性特化 (+3)");
        reasons.push("魔法耐性パッシブと魔法シールドにより、相手のAPバーストを容易に耐えきれます");
      }} else if (["Galio", "Kassadin"].includes(opp.id) && meDp.primary_type === "AP") {{
        score -= 3;
        factors.push("相手の対AP魔法耐性特化 (-3)");
        reasons.push("相手の対AP防御性能とシールドにより、こちらの魔法バーストが軽減されます");
      }}

      if (meSustain && !oppSustain) {{
        score += 1;
        factors.push("サステイン優位 (+1)");
        reasons.push("高い固有サステインによりショートトレード後の体力差でレーン主導権を握れます");
      }} else if (!meSustain && oppSustain) {{
        score -= 1;
        factors.push("相手サステイン優位 (-1)");
        reasons.push("相手のサステイン回復により消耗戦で不利になりやすいため、早期の重傷アイテム購入が有効です");
      }}

      const meClasses = me.classes || me.tags || [];
      const oppClasses = opp.classes || opp.tags || [];
      const isOppAssassin = oppClasses.includes("Assassin") || ["Zed", "Talon", "Qiyana", "Katarina"].some(k => opp.id.includes(k));
      const isMeAssassin = meClasses.includes("Assassin") || ["Zed", "Talon", "Qiyana", "Katarina"].some(k => me.id.includes(k));

      if ((meClasses.includes("Tank") || meDp.primary_type === "TANK") && isOppAssassin) {{
        score += 2;
        factors.push("タンク対アサシン耐久優位 (+2)");
        reasons.push("アサシンの瞬間バーストを耐久力で受け止め、CCで拘束して反撃できます");
      }} else if ((oppClasses.includes("Tank") || oppDp.primary_type === "TANK") && isMeAssassin) {{
        score -= 2;
        factors.push("アサシン対タンク突破難 (-2)");
        reasons.push("相手の高耐久を削りきれず、アサシン側のバーストが通りにくい構成です");
      }}

      if (["Vayne", "Fiora", "Gwen", "KogMaw"].includes(me.id) && oppDp.primary_type === "TANK") {{
        score += 2;
        factors.push("対タンク割合・確定ダメージ (+2)");
        reasons.push("最大体力割合ダメージと確定ダメージにより、相手の防具を無視して削れます");
      }} else if (["Vayne", "Fiora", "Gwen", "KogMaw"].includes(opp.id) && meDp.primary_type === "TANK") {{
        score -= 2;
        factors.push("相手の対タンク割合・確定ダメージ (-2)");
        reasons.push("相手の割合ダメージ・確定ダメージにより、防具を積んでも耐えきれないリスクがあります");
      }}

      const meRange = me.stats?.attackrange || 175;
      const oppRange = opp.stats?.attackrange || 175;
      if (meRange >= 500 && oppRange <= 200) {{
        score += 1;
        factors.push(`通常攻撃射程優位 (${{meRange}} vs ${{oppRange}}, +1)`);
        reasons.push("射程差を活かしたアウトレンジポークで安全にハラスできます");
      }} else if (oppRange >= 500 && meRange <= 200) {{
        score -= 1;
        factors.push(`相手射程優位 (${{meRange}} vs ${{oppRange}}, -1)`);
        reasons.push("相手の遠距離ポークにより序盤の被弾に注意し、不用意なヘルスロスを避ける必要があります");
      }}

      if (factors.length === 0) factors.push("標準ステータス均衡 (0)");

      let adv = "even";
      let advLabel = "判定材料不足（実測統計なし）";
      let reasonText = reasons.length ? reasons.join(" ＆ ") + "。これだけでは有利・不利を判定できません。" : "このレーンの実測統計がなく、基礎特性だけでは有利・不利を判定できません。";
      if (score >= 2) {{
        adv = "fav";
        advLabel = "特性推定: 有利傾向 (実測統計なし)";
        reasonText = reasons.join(" ＆ ");
      }} else if (score <= -2) {{
        adv = "unfav";
        advLabel = "特性推定: 警戒傾向 (実測統計なし)";
        reasonText = reasons.join(" ＆ ");
      }}

      return {{
        winrate: null,
        winrate_display: null,
        advantage: adv,
        advantage_label: advLabel,
        reason: reasonText,
        source: "synergy_estimate",
        is_estimated: true,
        role: role || "ESTIMATED",
        patch: patch,
        estimation_factors: factors,
        estimation_limitation: "基礎ステータス（射程・ダメージ属性・サステイン・クラス特性）に基づくヒューリスティック推定であり、OP.GGの実戦統計勝率ではありません。"
      }};
    }}

    let currentRole = "ALL";
    let searchKeyword = "";
    let currentAttackFilter = "ALL";
    let currentDamageFilter = "ALL";
    const currentTraitFilters = new Set();

    const gridEl = document.getElementById("champGrid");
    const countStatusEl = document.getElementById("countStatus");
    const searchInput = document.getElementById("searchInput");
    const modalEl = document.getElementById("detailModal");
    const modalCloseBtn = document.getElementById("modalCloseBtn");
    const modalNameEl = document.getElementById("modalChampName");
    const modalTitleEl = document.getElementById("modalChampTitle");
    const modalBodyEl = document.getElementById("modalBody");

    function getRoleBadgeClass(role) {{
      switch(role) {{
        case "TOP": return "badge-top";
        case "JUG": return "badge-jug";
        case "MID": return "badge-mid";
        case "ADC": return "badge-adc";
        case "SUP": return "badge-sup";
        default: return "badge-default";
      }}
    }}

    // ひらがな・カタカナ相互変換 & 柔軟検索ユーティリティ (全検索窓で共通利用)
    function toHiragana(str) {{
      if (!str) return "";
      return str.replace(/[\u30a1-\u30f6]/g, match => {{
        return String.fromCharCode(match.charCodeAt(0) - 0x60);
      }});
    }}

    function toKatakana(str) {{
      if (!str) return "";
      return str.replace(/[\u3041-\u3096]/g, match => {{
        return String.fromCharCode(match.charCodeAt(0) + 0x60);
      }});
    }}

    function matchSearch(text, query) {{
      if (!query) return true;
      if (!text) return false;
      const t = text.toLowerCase();
      const q = query.toLowerCase();
      if (t.includes(q)) return true;
      const th = toHiragana(t);
      const qh = toHiragana(q);
      if (th.includes(qh)) return true;
      const tk = toKatakana(t);
      const qk = toKatakana(q);
      if (tk.includes(qk)) return true;
      return false;
    }}

    function renderList() {{
      gridEl.innerHTML = "";
      const query = searchKeyword.trim();
      let matched = 0;

      Object.values(CHAMPIONS).forEach(champ => {{
        // 1. ロールフィルター
        if (currentRole !== "ALL") {{
          if (!champ.roles || !champ.roles.includes(currentRole)) return;
        }}

        // 2. AA攻撃タイプフィルター (近接 / 遠隔)
        if (currentAttackFilter !== "ALL") {{
          const attType = champ.attack_type?.type || (champ.stats?.attackrange <= 250 ? "MELEE" : "RANGED");
          if (currentAttackFilter === "MELEE") {{
            if (attType !== "MELEE" && attType !== "HYBRID") return;
          }} else if (currentAttackFilter === "RANGED") {{
            if (attType !== "RANGED" && attType !== "HYBRID") return;
          }}
        }}

        // 3. ダメージ属性フィルター (AD / AP / TANK)
        if (currentDamageFilter !== "ALL") {{
          const pType = champ.damage_profile?.primary_type || "AD";
          if (currentDamageFilter === "AD") {{
            if (pType !== "AD" && pType !== "HYBRID") return;
          }} else if (currentDamageFilter === "AP") {{
            if (pType !== "AP" && pType !== "HYBRID") return;
          }} else if (currentDamageFilter === "TANK") {{
            if (pType !== "TANK") return;
          }}
        }}

        // 4. 特性フィルター (サステイン / 両型あり)
        if (currentTraitFilters.has("SUSTAIN")) {{
          if (!champ.sustain_info?.has_sustain) return;
        }}
        if (currentTraitFilters.has("DUAL")) {{
          if (!champ.damage_profile?.has_dual_build) return;
        }}

        // 5. 検索クエリ (ひらがな・カタカナ・英字部分一致対応)
        if (query) {{
          const isHit = matchSearch(champ.name, query) ||
                        matchSearch(champ.id, query) ||
                        matchSearch(champ.title, query);
          if (!isHit) return;
        }}

        matched++;

        const card = document.createElement("div");
        card.className = "champ-card";
        card.onclick = () => openDetail(champ.id);

        const rolesHtml = (champ.roles || []).map(r => 
          `<span class="mini-badge ${{getRoleBadgeClass(r)}}">${{r}}</span>`
        ).join("");

        // ダメージ属性バッジ (AD / AP / HYBRID / TANK)
        const dp = champ.damage_profile || {{}};
        const dmgBadgeHtml = dp.badge_text ? 
          `<span class="damage-badge ${{dp.badge_class || 'badge-ad'}}">${{dp.badge_text}}</span>` : "";

        // AA攻撃タイプバッジ (近接 / 遠隔 / 両用)
        const att = champ.attack_type || {{}};
        const attRange = champ.stats?.attackrange || 175;
        let attClass = "badge-melee";
        let attIcon = "🗡️";
        let attBadge = att.badge || (attRange <= 250 ? "近接" : "遠隔");
        if (att.type === "RANGED" || (!att.type && attRange > 250)) {{
          attClass = "badge-ranged";
          attIcon = "🏹";
        }} else if (att.type === "HYBRID") {{
          attClass = "badge-att-hybrid";
          attIcon = "🔄";
        }}
        const attBadgeHtml = `<span class="attack-type-badge ${{attClass}}" title="${{escapeHtml(att.label || `${{attBadge}} [射程 ${{attRange}}]`)}}">${{attIcon}} ${{attBadge}}</span>`;

        // Data Dragon公式CDNまたはフォールバック
        const patch = champ.patch || DEFAULT_PATCH;
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{champ.id}}.png`;

        card.innerHTML = `
          <div class="champ-card-img-wrap">
            <img class="champ-card-img" src="${{imgUrl}}" alt="${{champ.name}}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="champ-card-img-placeholder" style="display:none;">${{champ.name.charAt(0)}}</div>
            <div class="role-badge-list">${{rolesHtml}}</div>
            <div class="card-top-badges">
              ${{dmgBadgeHtml}}
              ${{attBadgeHtml}}
            </div>
          </div>
          <div class="champ-info">
            <div class="champ-name">${{champ.name}}</div>
            <div class="champ-title">${{champ.title || ""}}</div>
          </div>
        `;
        gridEl.appendChild(card);
      }});

      countStatusEl.textContent = `表示中: ${{matched}} 体 / 全 ${{Object.keys(CHAMPIONS).length}} 体`;
    }}

    function openDetail(champId, activeRole = null) {{
      const c = CHAMPIONS[champId];
      if (!c) return;

      const patch = c.patch || DEFAULT_PATCH;
      modalNameEl.textContent = c.name;
      modalTitleEl.textContent = `${{c.id}} - ${{c.title || ""}} (Patch ${{patch}})`;

      const SPELL_IMG_MAP = {{
        "フラッシュ": "SummonerFlash.png",
        "イグナイト": "SummonerDot.png",
        "テレポート": "SummonerTeleport.png",
        "スマイト": "SummonerSmite.png",
        "ヒール": "SummonerHeal.png",
        "バリア": "SummonerBarrier.png",
        "イグゾースト": "SummonerExhaust.png",
        "ゴースト": "SummonerHaste.png",
        "クレンズ": "SummonerBoost.png"
      }};

      // 選択中ロール（未指定時は第1ロール）
      const currentSelectedRole = activeRole || (c.roles && c.roles.length > 0 ? c.roles[0] : "TOP");
      const roleSpecificData = (c.role_data && c.role_data[currentSelectedRole]) ? c.role_data[currentSelectedRole] : {{}};
      const currentSpells = roleSpecificData.spells || c.summoner_spells || ["フラッシュ", "テレポート"];

      // 複数ロール切り替えサブタブ
      let roleTabsHtml = "";
      if (c.roles && c.roles.length > 1) {{
        roleTabsHtml = `
          <div class="modal-role-tabs">
            ${{c.roles.map(r => `
              <button class="modal-role-btn ${{r === currentSelectedRole ? "active" : ""}}" data-modal-role="${{r}}">
                <span class="mini-badge ${{getRoleBadgeClass(r)}}">${{r}}</span>
                <span>${{r}} レーン</span>
              </button>
            `).join("")}}
          </div>
        `;
      }}

      // 通常攻撃 (AA) 射程タイプ (メレー / レンジ / 両用)
      const att = c.attack_type || {{}};
      const attRange = c.stats?.attackrange || 175;
      let attBadgeClass = "badge-melee";
      let attIcon = "🗡️";
      let attBadge = att.badge || (attRange <= 250 ? "近接" : "遠隔");
      if (att.type === "RANGED" || (!att.type && attRange > 250)) {{
        attBadgeClass = "badge-ranged";
        attIcon = "🏹";
      }} else if (att.type === "HYBRID") {{
        attBadgeClass = "badge-att-hybrid";
        attIcon = "🔄";
      }}
      const attackTypeHeaderHtml = `
        <div class="modal-attack-type-wrap">
          <span class="modal-damage-title">🎯 通常攻撃 (AA):</span>
          <span class="attack-type-badge ${{attBadgeClass}}">${{attIcon}} ${{escapeHtml(att.label || `${{attBadge}} [射程 ${{attRange}}]`)}}</span>
          ${{att.desc ? `<span class="modal-attack-type-desc">${{escapeHtml(att.desc)}}</span>` : ""}}
        </div>
      `;

      // ダメージ属性 ＆ 両刀プロファイル
      const dp = c.damage_profile || {{}};
      let damageBadgeHtml = "";
      let dualBuildAlertHtml = "";
      if (dp.badge_text) {{
        damageBadgeHtml = `
          <div class="modal-damage-header">
            <span class="modal-damage-title">⚡ 主ダメージ属性:</span>
            <span class="damage-badge ${{dp.badge_class || "badge-ad"}}">${{dp.badge_text}} (${{dp.label || ""}})</span>
            <span class="modal-damage-counter">🛡️ 対面時の推奨防具: <strong>${{dp.counter_defense || "AR/MR"}}</strong></span>
          </div>
        `;
      }}
      if (dp.has_dual_build) {{
        dualBuildAlertHtml = `
          <div class="dual-build-alert">
            ⚡ <strong>【AD / AP 両型ビルド対応】</strong> ${{dp.dual_build_desc}}
          </div>
        `;
      }}

      // サステイン & スキル上げ優先度バッジ
      const sustainInfo = c.sustain_info || {{}};
      let sustainBadgeHtml = "";
      let sustainReasonHtml = "";
      if (sustainInfo.has_sustain) {{
        let badgeLabel = "🩸 サステイン所持 (重傷推奨)";
        if (sustainInfo.type === "BOTH") {{
          badgeLabel = "🩸 回復＆シールド所持";
        }} else if (sustainInfo.type === "SHIELD") {{
          badgeLabel = "🛡️ シールド所持";
        }}
        const susReason = sustainInfo.summary || sustainInfo.reason || "固有の体力回復またはシールド能力を持ちます。";
        sustainBadgeHtml = `<span class="badge-sustain">${{badgeLabel}}</span>`;
        sustainReasonHtml = `<div class="sustain-reason-box">⚠️ <strong>【対面注意・維持能力】</strong> ${{escapeHtml(susReason)}}</div>`;
      }}

      const skillOrder = roleSpecificData.skill_order || c.skill_order || "Q > E > W";
      const skillOrderBadgeHtml = `<span class="badge-skill-order">⚡ スキル上げ順: ${{skillOrder}}</span>`;

      // サモナースペル（採用率上位2セット）
      const spellSets = roleSpecificData.spell_sets || c.spell_sets || [
        {{ name: "第1採用セット（王道・最高採用率）", spells: currentSpells }}
      ];
      const spellsHtml = `
        <div class="spells-sets-wrap">
          ${{spellSets.map(ss => `
            <div class="spell-set-card">
              <div class="spell-set-title">⚡ ${{ss.name}}</div>
              <div class="spells-badge-list">
                ${{ss.spells.map(s => {{
                  const sImg = SPELL_IMG_MAP[s] || "SummonerFlash.png";
                  const sUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/spell/${{sImg}}`;
                  return `
                    <span class="spell-pill">
                      <img class="spell-img" src="${{sUrl}}" alt="${{s}}" onerror="this.style.display='none';">
                      <span>${{s}}</span>
                    </span>
                  `;
                }}).join("")}}
              </div>
            </div>
          `).join("")}}
        </div>
      `;

      // スキル取得順マトリクス表 (Lv 1〜18)
      const skillMatrix = roleSpecificData.skill_matrix || c.skill_matrix || {{
        Q: [1, 4, 5, 7, 9], W: [3, 14, 15, 17, 18], E: [2, 8, 10, 12, 13], R: [6, 11, 16]
      }};
      const matrixSlots = ["Q", "W", "E", "R"];
      let matrixTableRows = matrixSlots.map(slot => {{
        const points = skillMatrix[slot] || [];
        let cells = "";
        for (let lv = 1; lv <= 18; lv++) {{
          const isActive = points.includes(lv);
          cells += `<td class="${{isActive ? "skill-point-active" : ""}}">${{isActive ? slot : ""}}</td>`;
        }}
        return `<tr><td class="sticky-col">${{slot}}</td>${{cells}}</tr>`;
      }}).join("");

      const skillMatrixHtml = `
        <div class="skill-matrix-container">
          <div class="skill-matrix-scroll">
            <table class="skill-matrix-table">
              <thead>
                <tr>
                  <th class="sticky-col">Lv</th>
                  ${{Array.from({{length: 18}}, (_, i) => `<th>${{i+1}}</th>`).join("")}}
                </tr>
              </thead>
              <tbody>
                ${{matrixTableRows}}
              </tbody>
            </table>
          </div>
        </div>
      `;

      // 特徴・強み・弱み (フォールバック保証付き)
      const ov = c.overview || {{}};
      let strengthsList = (Array.isArray(ov.strengths) && ov.strengths.length > 0) ? ov.strengths : [
        `${{c.name}}の主力スキルを活かした強力なダメージトレード能力`,
        `集団戦や局所戦における高い影響力と主導権の掌握`,
        `安定したピック性能と明確なパワースパイク`
      ];
      let weaknessesList = (Array.isArray(ov.weaknesses) && ov.weaknesses.length > 0) ? ov.weaknesses : [
        `主要スキルのクールダウン中における無防備さ`,
        `敵のハードCCや集中フォーカスに対する脆さ`,
        `レーンでの立ち位置やウェーブ管理の精度が要求される点`
      ];
      const strengthsHtml = strengthsList.map(s => `<li>${{s}}</li>`).join("");
      const weaknessesHtml = weaknessesList.map(w => `<li>${{w}}</li>`).join("");

      // 立ち回りメモ
      const gn = roleSpecificData.gameplay_notes || c.gameplay_notes || {{}};
      const roleNoteHtml = roleSpecificData.role_note ? `<div style="font-size:12px; margin-bottom:8px; color:#38bdf8; line-height:1.5;"><strong>【${{currentSelectedRole}}ロールの主務】</strong> ${{roleSpecificData.role_note}}</div>` : "";
      const laningNote = gn.laning || "相手のスキルクールダウンやミニオンウェーブの位置を注視してトレードを行う。";
      const tfNote = gn.teamfight || "集団戦では味方とフォーカスを合わせ、自身の役割を完遂する。";
      const tipNote = gn.key_tips || "";

      // 実戦コンボ
      const combos = c.combos || [];
      const combosHtml = combos.map(cb => `
        <div class="combo-card">
          <div class="combo-name">🥊 ${{cb.name}}</div>
          <div class="combo-recipe">${{cb.recipe}}</div>
          <div class="combo-desc">${{cb.desc}}</div>
        </div>
      `).join("");

      // 複数ビルドパターン
      const buildPatterns = roleSpecificData.build_patterns || c.build_patterns || [];
      let buildTabsHtml = "";
      let buildContentHtml = "";

      function renderBuildPatternInner(bp) {{
        const pCoreHtml = (bp.core_items || []).map((ci, sIdx) => {{
          const cImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{ci.item_id}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{ci.item_id}}" title="タップして詳細を表示">
              <span class="item-step">${{sIdx + 1}}</span>
              <img class="item-img" src="${{cImg}}" alt="${{ci.name}}" onerror="this.src='icon.png';">
              <span>${{ci.name}}</span>
            </span>
          `;
        }}).join("");

        const pStarterHtml = (bp.starter || []).map(sName => {{
          const sItem = Object.values(ITEMS).find(it => it.name === sName);
          const sId = sItem ? sItem.id : "1055";
          const sImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{sId}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{sId}}" title="タップして詳細を表示">
              <img class="item-img" src="${{sImg}}" alt="${{sName}}" onerror="this.src='icon.png';">
              <span>${{sName}}</span>
            </span>
          `;
        }}).join("");

        const bootName = bp.boots || "プレート スチールキャップ";
        const bootItem = Object.values(ITEMS).find(it => it.name === bootName);
        const bootId = bootItem ? bootItem.id : "3047";
        const bootImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{bootId}}.png`;
        const pBootsHtml = `
          <span class="item-pill clickable-item" data-item-id="${{bootId}}" title="タップして詳細を表示">
            <img class="item-img" src="${{bootImg}}" alt="${{bootName}}" onerror="this.src='icon.png';">
            <span>${{bootName}}</span>
          </span>
        `;

        const pSitHtml = (bp.situational || []).map(sitName => {{
          const sitItem = Object.values(ITEMS).find(it => it.name === sitName);
          const sitId = sitItem ? sitItem.id : "1001";
          const sitImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{sitId}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{sitId}}" title="タップして詳細を表示">
              <img class="item-img" src="${{sitImg}}" alt="${{sitName}}" onerror="this.src='icon.png';">
              <span>${{sitName}}</span>
            </span>
          `;
        }}).join("");

        return `
          <div class="build-pat-desc">💡 ${{bp.desc}}</div>
          <div class="build-group">
            <div class="build-group-title">スタートアイテム</div>
            <div class="item-tags">${{pStarterHtml}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨靴</div>
            <div class="item-tags">${{pBootsHtml}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨コアアイテム（進行順）</div>
            <div class="item-tags">${{pCoreHtml}}</div>
          </div>
          ${{pSitHtml ? `
            <div class="build-group">
              <div class="build-group-title">状況別・後半選択アイテム</div>
              <div class="item-tags">${{pSitHtml}}</div>
            </div>
          ` : ""}}
        `;
      }}

      if (buildPatterns.length > 0) {{
        buildTabsHtml = `
          <div class="build-pat-tabs">
            ${{buildPatterns.map((bp, idx) => `
              <button class="build-pat-btn ${{idx === 0 ? "active" : ""}}" data-build-idx="${{idx}}">${{bp.name}}</button>
            `).join("")}}
          </div>
        `;
        buildContentHtml = `<div id="buildPatternContent">${{renderBuildPatternInner(buildPatterns[0])}}</div>`;
      }}

      // 相性 (勝率と戦術理由を厳格分離、安全な描画、ロール固有対面データ完全対応)
      const curMatchups = roleSpecificData.matchups || c.matchups || {{}};

      function renderMatchupCard(m, isFav) {{
        const oppImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{escapeHtml(m.champion_id)}}.png`;
        const oppName = escapeHtml(m.name || m.champion_id);

        // 1. 勝率バッジの抽出
        let winrateText = isFav ? "有利" : "不利";
        if (m.winrate_display) {{
          winrateText = m.winrate_display;
        }} else if (m.winrate) {{
          winrateText = `勝率 ${{m.winrate}}`;
        }} else if (m.reason && typeof m.reason === "string") {{
          const wrMatch = m.reason.match(/(\\d+(?:\\.\\d+)?%)/);
          if (wrMatch) {{
            winrateText = `勝率 ${{wrMatch[1]}}`;
          }}
        }}

        // 2. 戦術的理由の抽出
        let reasonText = "";
        if (m.reason && typeof m.reason === "string") {{
          let raw = m.reason.trim();
          if (raw.includes(" | ")) {{
            const parts = raw.split(" | ");
            raw = parts.slice(1).join(" | ").trim();
          }}
          // "勝率 XX%（統計的に有利/不利）" などの純粋な統計文を除外
          const isStatsOnly = /勝率\\s*\\d+(?:\\.\\d+)?%/.test(raw) || /統計的に(?:有利|不利)/.test(raw);
          if (!isStatsOnly && raw.length > 5) {{
            reasonText = raw;
          }}
        }}

        // 3. フォールバック (matchup_matrix から具体的理由を取得)
        if (!reasonText && c.matchup_matrix && c.matchup_matrix[m.champion_id]?.reason) {{
          const matR = c.matchup_matrix[m.champion_id].reason;
          if (matR && !matR.includes("統計的に有利") && !matR.includes("統計的に不利")) {{
            reasonText = matR;
          }}
        }}

        // 4. 因果関係が未検証の場合は、確認できる基礎特性を参考情報として示す。
        if (!reasonText || reasonText === "理由データなし") {{
          const opponent = CHAMPIONS[m.champion_id];
          const myRange = c.stats?.attackrange;
          const oppRange = opponent?.stats?.attackrange;
          const facts = [];
          if (Number.isFinite(myRange) && Number.isFinite(oppRange)) facts.push(`通常攻撃射程は${{c.name}} ${{myRange}}、${{opponent.name}} ${{oppRange}}`);
          if (opponent?.sustain_info?.has_sustain) facts.push(`${{opponent.name}}は回復または自己シールドを持つ`);
          reasonText = facts.length ? `参考特性：${{facts.join("。")}}。勝率の原因は未検証。` : "勝率の原因は未検証。";
        }}

        const badgeClass = isFav ? "badge-fav" : "badge-unfav";
        const isNoReason = reasonText === "理由データなし";
        const reasonStyle = isNoReason ? "color:var(--text-muted); font-size:12px; font-style:italic;" : "";

        return `
          <div class="matchup-item">
            <div class="matchup-header">
              <div class="matchup-champ-info">
                <img class="matchup-champ-img" src="${{oppImg}}" alt="${{oppName}}" onerror="this.style.display='none';">
                <span class="matchup-champ-name">${{oppName}}</span>
              </div>
              <span class="${{badgeClass}}">${{escapeHtml(winrateText)}}</span>
            </div>
            <div class="matchup-reason" style="${{reasonStyle}}">${{escapeHtml(reasonText)}}</div>
          </div>
        `;
      }}

      let favHtml = "";
      if (curMatchups.favorable && curMatchups.favorable.length > 0) {{
        favHtml = curMatchups.favorable.map(m => renderMatchupCard(m, true)).join("");
      }} else {{
        favHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }}

      let unfavHtml = "";
      if (curMatchups.unfavorable && curMatchups.unfavorable.length > 0) {{
        unfavHtml = curMatchups.unfavorable.map(m => renderMatchupCard(m, false)).join("");
      }} else {{
        unfavHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }}

      // ルーン
      const r = roleSpecificData.runes || c.runes || {{}};
      const priChoices = (r.primary?.choices || []).join(" / ");
      const secChoices = (r.secondary?.choices || []).join(" / ");
      const shards = (r.shards || []).join(" / ");

      // スキル一覧
      let skillsHtml = "";
      if (c.abilities && c.abilities.length > 0) {{
        c.abilities.forEach(a => {{
          const pImg = a.image ? `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/passive/${{a.image}}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${{pImg}}" alt="${{a.name}}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">P</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${{a.name}}</div>
                <div class="skill-desc">${{a.description || ""}}</div>
              </div>
            </div>
          `;
        }});
      }}
      if (c.spells && c.spells.length > 0) {{
        c.spells.forEach(s => {{
          const spImg = s.image ? `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/spell/${{s.image}}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${{spImg}}" alt="${{s.name}}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">${{s.slot}}</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${{s.name}}</div>
                <div class="skill-meta">CD: ${{s.cooldown || "なし"}} | コスト: ${{s.cost || "0"}}</div>
                <div class="skill-desc">${{s.description || ""}}</div>
              </div>
            </div>
          `;
        }});
      }}

      modalBodyEl.innerHTML = `
        ${{roleTabsHtml}}

        <!-- 通常攻撃 (AA) 射程タイプ -->
        ${{attackTypeHeaderHtml}}

        <!-- ダメージ属性 ＆ 防具対策ガイド -->
        ${{damageBadgeHtml}}
        ${{dualBuildAlertHtml}}

        <!-- ハイライトバッジ群 -->
        <div class="champ-highlight-badges">
          ${{sustainBadgeHtml}}
          ${{skillOrderBadgeHtml}}
        </div>
        ${{sustainReasonHtml}}

        <!-- チャンピオン概要 (特徴・強み・弱み) -->
        <div class="detail-section">
          <div class="detail-heading">📖 チャンピオン概要（特徴・強み・弱み）</div>
          <div class="overview-text">${{ov.summary || ""}}</div>
          <div class="pros-cons-grid">
            <div class="pros-box">
              <div class="pros-cons-title pros-title">💪 強み (Strengths)</div>
              <ul class="pros-cons-ul">${{strengthsHtml}}</ul>
            </div>
            <div class="cons-box">
              <div class="pros-cons-title cons-title">⚠️ 弱み (Weaknesses)</div>
              <ul class="pros-cons-ul">${{weaknessesHtml}}</ul>
            </div>
          </div>
        </div>

        <!-- 立ち回りメモ & スキル吐きどころ -->
        <div class="detail-section">
          <div class="detail-heading">📝 立ち回り概要メモ & スキルの吐きどころ</div>
          ${{roleNoteHtml}}
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【序盤・レーン戦】</strong> ${{laningNote}}</div>
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【中終盤・集団戦】</strong> ${{tfNote}}</div>
          ${{tipNote ? `<div style="font-size:12px; color:#f59e0b; line-height:1.5;"><strong>【極意】</strong> ${{tipNote}}</div>` : ""}}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">📖 wikiの考察・対策</div>
          ${{Object.entries(c.wiki_info?.sections || {{}}).map(([heading, text]) => `<div style="font-size:12px; margin-bottom:8px;">${{escapeHtml(heading)}}：${{escapeHtml(text)}}</div>`).join("")}}
          <div style="font-size:11px; color:var(--text-muted);">取得日：${{escapeHtml((c.wiki_info?.fetched_at || "").slice(0, 10))}}・パッチ対応未検証</div>
          ${{c.wiki_info?.source_url?.startsWith("https://www.loljp-wiki.jp/") ? `<a href="${{escapeHtml(c.wiki_info.source_url)}}" target="_blank" rel="noopener noreferrer">出典：LoLJPWiki</a>` : ""}}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">🥊 実戦コンボ・スキル回し（Flash併用含む）</div>
          <div class="combo-grid">${{combosHtml}}</div>
        </div>

        <!-- 推奨スペル -->
        <div class="detail-section">
          <div class="detail-heading">⚔️ 推奨サモナースペル（${{currentSelectedRole}}運用・採用率上位）</div>
          ${{spellsHtml}}
        </div>

        <!-- 推奨ビルド (複数パターン切り替え) -->
        <div class="detail-section">
          <div class="detail-heading">🛡️ 推奨ビルド構成（複数パターン対応）</div>
          ${{buildTabsHtml}}
          ${{buildContentHtml}}
        </div>

        <!-- 対面相性 -->
        <div class="detail-section">
          <div class="detail-heading">⚖️ 対面相性（OP.GG 統計勝率）</div>
          <div class="matchups-container">
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--favorable); margin-bottom:6px;">📈 有利な対面（おすすめ）</div>
              ${{favHtml}}
            </div>
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--unfavorable); margin-bottom:6px;">📉 不利な対面（警戒）</div>
              ${{unfavHtml}}
            </div>
          </div>
        </div>

        <!-- ルーン構成 -->
        <div class="detail-section">
          <div class="detail-heading">🔮 推奨ルーン構成</div>
          <div class="rune-row"><span class="rune-title">メインパス [${{r.primary?.path || "精密"}}]:</span><strong>${{r.primary?.keystone_name || "征服者"}}</strong> (${{priChoices}})</div>
          <div class="rune-row"><span class="rune-title">サブパス [${{r.secondary?.path || "不撓"}}]:</span>${{secChoices}}</div>
          <div class="rune-row"><span class="rune-title">シャード:</span>${{shards}}</div>
        </div>

        <!-- 全スキル詳細 -->
        <div class="detail-section">
          <div class="detail-heading">⚡ スキル詳細 & スキル取得順マトリクス</div>
          <div style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:8px;">📊 レベル別取得テーブル (Lv 1〜18)</div>
          ${{skillMatrixHtml}}
          <div style="font-size:12px; font-weight:700; color:var(--text-muted); margin:16px 0 8px 0;">🎯 各スキル性能解説</div>
          ${{skillsHtml}}
        </div>
      `;

      // ロールサブタブのイベント登録
      modalBodyEl.querySelectorAll(".modal-role-btn").forEach(btn => {{
        btn.onclick = (e) => {{
          e.stopPropagation();
          const targetRole = btn.getAttribute("data-modal-role");
          openDetail(champId, targetRole);
        }};
      }});

      // ビルドパターン切り替えタブのイベント登録
      modalBodyEl.querySelectorAll(".build-pat-btn").forEach(btn => {{
        btn.onclick = (e) => {{
          e.stopPropagation();
          modalBodyEl.querySelectorAll(".build-pat-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const idx = parseInt(btn.getAttribute("data-build-idx"), 10);
          const bp = buildPatterns[idx];
          const contentBox = document.getElementById("buildPatternContent");
          if (contentBox && bp) {{
            contentBox.innerHTML = renderBuildPatternInner(bp);
            bindClickableItems(contentBox);
          }}
        }};
      }});

      // アイテムクリックイベントの登録関数
      function bindClickableItems(parentEl) {{
        parentEl.querySelectorAll(".clickable-item").forEach(el => {{
          el.onclick = (e) => {{
            e.stopPropagation();
            const itemId = el.getAttribute("data-item-id");
            if (itemId && ITEMS[itemId]) {{
              openItemDetail(itemId);
            }}
          }};
        }});
      }}
      bindClickableItems(modalBodyEl);

      modalEl.classList.add("open");

      // スクロール位置を必ず一番上（最上部）にリセット
      const mContent = modalEl.querySelector(".modal-content");
      if (mContent) mContent.scrollTop = 0;
      modalBodyEl.scrollTop = 0;

      // スマホの戻るスワイプ対応: History APIにモーダル状態を追加
      if (!history.state || history.state.modal !== 'champion_detail') {{
        history.pushState({{ modal: 'champion_detail', champId: champId }}, '');
      }}
    }}

    function closeDetailModal() {{
      modalEl.classList.remove("open");
    }}

    modalCloseBtn.onclick = () => {{
      if (history.state && history.state.modal === 'champion_detail') {{
        history.back();
      }} else {{
        closeDetailModal();
      }}
    }};

    modalEl.onclick = (e) => {{
      if (e.target === modalEl) {{
        if (history.state && history.state.modal === 'champion_detail') {{
          history.back();
        }} else {{
          closeDetailModal();
        }}
      }}
    }};

    // リリースノート（アプデ履歴）モーダル制御
    const changelogModalEl = document.getElementById("changelogModal");
    const changelogCloseBtn = document.getElementById("changelogCloseBtn");
    const patchBadgeEl = document.getElementById("patchBadge");

    function openChangelogModal() {{
      changelogModalEl.classList.add("open");
      const cContent = changelogModalEl.querySelector(".modal-content");
      if (cContent) cContent.scrollTop = 0;
      if (!history.state || history.state.modal !== 'changelog') {{
        history.pushState({{ modal: 'changelog' }}, '');
      }}
    }}

    function closeChangelogModal() {{
      changelogModalEl.classList.remove("open");
    }}

    if (patchBadgeEl) {{
      patchBadgeEl.onclick = () => openChangelogModal();
    }}

    if (changelogCloseBtn) {{
      changelogCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'changelog') {{
          history.back();
        }} else {{
          closeChangelogModal();
        }}
      }};
    }}

    if (changelogModalEl) {{
      changelogModalEl.onclick = (e) => {{
        if (e.target === changelogModalEl) {{
          if (history.state && history.state.modal === 'changelog') {{
            history.back();
          }} else {{
            closeChangelogModal();
          }}
        }}
      }};
    }}

    // ==========================================
    // アイテム詳細モーダル制御 (Phase 2)
    // ==========================================
    const itemDetailModalEl = document.getElementById("itemDetailModal");
    const itemDetailCloseBtn = document.getElementById("itemDetailCloseBtn");
    const itemDetailIcon = document.getElementById("itemDetailIcon");
    const itemDetailName = document.getElementById("itemDetailName");
    const itemDetailPrices = document.getElementById("itemDetailPrices");
    const itemDetailStatsSec = document.getElementById("itemDetailStatsSec");
    const itemDetailStatsText = document.getElementById("itemDetailStatsText");
    const itemDetailDescSec = document.getElementById("itemDetailDescSec");
    const itemDetailDescText = document.getElementById("itemDetailDescText");
    const itemDetailRecipeSec = document.getElementById("itemDetailRecipeSec");
    const itemRecipeFromBox = document.getElementById("itemRecipeFromBox");
    const itemRecipeFromList = document.getElementById("itemRecipeFromList");
    const itemRecipeIntoBox = document.getElementById("itemRecipeIntoBox");
    const itemRecipeIntoList = document.getElementById("itemRecipeIntoList");

    function openItemDetail(itemId) {{
      const item = ITEMS[itemId];
      if (!item) return;

      const patch = DEFAULT_PATCH;
      itemDetailIcon.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{item.id}}.png`;
      itemDetailIcon.style.display = "block";
      itemDetailName.textContent = item.name;

      // 価格
      const totalGold = item.gold?.total || 0;
      const sellGold = item.gold?.sell || 0;
      itemDetailPrices.innerHTML = `
        <span class="item-card-price">💰 価格: ${{totalGold}} G</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">(売却: ${{sellGold}} G)</span>
      `;

      // ステータス整形 (絵文字・アイコンなしのクリーン表示)
      const statsList = item.stats_list || [];
      if (statsList.length > 0) {{
        itemDetailStatsSec.style.display = "block";
        itemDetailStatsText.innerHTML = statsList.map(st => `<span class="stat-badge">${{st}}</span>`).join("");
      }} else {{
        const statsObj = item.stats || {{}};
        const statEntries = Object.entries(statsObj);
        if (statEntries.length > 0) {{
          itemDetailStatsSec.style.display = "block";
          const statsHtml = statEntries.map(([k, v]) => {{
            let label = k;
            let val = v;
            if (k === "FlatPhysicalDamageMod") label = "攻撃力(AD)";
            else if (k === "FlatMagicDamageMod") label = "魔力(AP)";
            else if (k === "FlatHPPoolMod") label = "体力(HP)";
            else if (k === "FlatArmorMod") label = "物理防御(AR)";
            else if (k === "FlatSpellBlockMod") label = "魔法防御(MR)";
            else if (k === "PercentAttackSpeedMod") {{ label = "攻撃速度"; val = `+${{Math.round(val * 100)}}%`; }}
            else if (k === "FlatMovementSpeedMod") label = "移動速度";
            else if (k === "PercentMovementSpeedMod") {{ label = "移動速度%"; val = `+${{Math.round(val * 100)}}%`; }}
            else if (k === "FlatCritChanceMod") {{ label = "クリティカル率"; val = `+${{Math.round(val * 100)}}%`; }}
            else if (k === "FlatMPPoolMod") label = "マナ";
            else if (k === "PercentLifeStealMod") {{ label = "ライフスティール"; val = `+${{Math.round(val * 100)}}%`; }}
            else if (k === "PercentOmnivampMod") {{ label = "オムニヴァンプ"; val = `+${{Math.round(val * 100)}}%`; }}
            else if (k === "PercentTenacityMod") {{ label = "行動妨害耐性"; val = `+${{Math.round(val * 100)}}%`; }}

            if (typeof val === "number" && !val.toString().startsWith("+") && val > 0) {{
              val = `+${{val}}`;
            }}
            return `<span class="stat-badge">${{label}}: ${{val}}</span>`;
          }}).join("");
          itemDetailStatsText.innerHTML = statsHtml;
        }} else {{
          itemDetailStatsSec.style.display = "none";
        }}
      }}

      // 説明文整形
      let cleanDesc = item.description || item.plaintext || "効果情報なし";
      cleanDesc = cleanDesc.replace(/<br\\s*\\/?>/gi, "\\n")
                           .replace(/<\\/p>/gi, "\\n")
                           .replace(/<li>/gi, "• ")
                           .replace(/<\\/li>/gi, "\\n")
                           .replace(/<[^>]+>/g, "")
                           .trim();
      itemDetailDescText.textContent = cleanDesc;

      // 素材ツリー (Builds from)
      const fromIds = item.from || [];
      if (fromIds.length > 0) {{
        itemRecipeFromBox.style.display = "block";
        itemRecipeFromList.innerHTML = fromIds.map(fid => {{
          const fItem = ITEMS[fid];
          const fName = fItem ? fItem.name : `ID:${{fid}}`;
          const fPrice = fItem ? `${{fItem.gold?.total || 0}} G` : "無料";
          const fImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{fid}}.png`;
          const fStats = fItem?.stats_summary ? `<span style="font-size:10px; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${{fItem.stats_summary}}</span>` : "";
          return `
            <div class="recipe-item-card" data-recipe-id="${{fid}}" title="${{fName}} の詳細を表示">
              <img src="${{fImg}}" alt="${{fName}}" onerror="this.src='icon.png';">
              <div class="recipe-item-info">
                <span class="recipe-item-name">${{fName}}</span>
                <span class="recipe-item-price">💰 ${{fPrice}}</span>
                ${{fStats}}
              </div>
            </div>
          `;
        }}).join("");
      }} else {{
        itemRecipeFromBox.style.display = "none";
      }}

      // 派生先ツリー (Builds into)
      const intoIds = item.into || [];
      if (intoIds.length > 0) {{
        itemRecipeIntoBox.style.display = "block";
        itemRecipeIntoList.innerHTML = intoIds.map(iid => {{
          const iItem = ITEMS[iid];
          const iName = iItem ? iItem.name : `ID:${{iid}}`;
          const iPrice = iItem ? `${{iItem.gold?.total || 0}} G` : "無料";
          const iImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{iid}}.png`;
          const iStats = iItem?.stats_summary ? `<span style="font-size:10px; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${{iItem.stats_summary}}</span>` : "";
          return `
            <div class="recipe-item-card" data-recipe-id="${{iid}}" title="${{iName}} の詳細を表示">
              <img src="${{iImg}}" alt="${{iName}}" onerror="this.src='icon.png';">
              <div class="recipe-item-info">
                <span class="recipe-item-name">${{iName}}</span>
                <span class="recipe-item-price">💰 ${{iPrice}}</span>
                ${{iStats}}
              </div>
            </div>
          `;
        }}).join("");
      }} else {{
        itemRecipeIntoBox.style.display = "none";
      }}

      if (fromIds.length === 0 && intoIds.length === 0) {{
        itemDetailRecipeSec.style.display = "none";
      }} else {{
        itemDetailRecipeSec.style.display = "block";
      }}

      // レシピアイテムのクリックイベント（素材・派生先アイテム詳細へジャンプ）
      itemDetailModalEl.querySelectorAll(".recipe-item-card, .recipe-item-pill").forEach(pill => {{
        pill.onclick = (e) => {{
          e.stopPropagation();
          const nextId = pill.getAttribute("data-recipe-id");
          if (nextId) openItemDetail(nextId);
        }};
      }});

      itemDetailModalEl.classList.add("open");
      const iContent = itemDetailModalEl.querySelector(".modal-content");
      if (iContent) iContent.scrollTop = 0;
      const iBody = itemDetailModalEl.querySelector(".modal-body");
      if (iBody) iBody.scrollTop = 0;

      // History API
      if (!history.state || history.state.modal !== 'item_detail') {{
        history.pushState({{ modal: 'item_detail', itemId: itemId }}, '');
      }}
    }}

    function closeItemDetailModal() {{
      itemDetailModalEl.classList.remove("open");
    }}

    if (itemDetailCloseBtn) {{
      itemDetailCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'item_detail') {{
          history.back();
        }} else {{
          closeItemDetailModal();
        }}
      }};
    }}

    if (itemDetailModalEl) {{
      itemDetailModalEl.onclick = (e) => {{
        if (e.target === itemDetailModalEl) {{
          if (history.state && history.state.modal === 'item_detail') {{
            history.back();
          }} else {{
            closeItemDetailModal();
          }}
        }}
      }};
    }}

    // ==========================================
    // アイテム図鑑の制御・検索・ソート (Phase 2)
    // ==========================================
    const itemsGridEl = document.getElementById("itemsGrid");
    const itemCountStatusEl = document.getElementById("itemCountStatus");
    const itemSearchInput = document.getElementById("itemSearchInput");
    const itemSortSelect = document.getElementById("itemSortSelect");
    let currentItemCat = "ALL";
    let itemSearchKeyword = "";
    let currentItemSort = "price_desc";

    function renderItemsList() {{
      if (!itemsGridEl) return;
      itemsGridEl.innerHTML = "";
      const query = itemSearchKeyword.trim();

      let itemsList = Object.values(ITEMS);

      // 1. カテゴリフィルター
      if (currentItemCat !== "ALL") {{
        itemsList = itemsList.filter(item => {{
          if (Array.isArray(item.categories)) {{
            return item.categories.includes(currentItemCat);
          }}
          if (typeof item.category === "string") {{
            return item.category === currentItemCat;
          }}
          return false;
        }});
      }}

      // 2. ステータスチェックボックスフィルター (複数選択 AND条件)
      const checkedBoxes = document.querySelectorAll(".stat-filter-chk:checked");
      const selectedStats = Array.from(checkedBoxes).map(cb => cb.value);

      const activeStatBadge = document.getElementById("activeStatBadge");
      if (activeStatBadge) {{
        if (selectedStats.length > 0) {{
          activeStatBadge.textContent = selectedStats.length;
          activeStatBadge.style.display = "inline-flex";
        }} else {{
          activeStatBadge.style.display = "none";
        }}
      }}

      if (selectedStats.length > 0) {{
        itemsList = itemsList.filter(item => {{
          const itemTags = item.stat_tags || [];
          return selectedStats.every(tag => itemTags.includes(tag));
        }});
      }}

      // 3. 検索フィルター (ひらがな・カタカナ・通称・部分一致対応)
      if (query) {{
        itemsList = itemsList.filter(item => {{
          return matchSearch(item.name, query) ||
                 matchSearch(item.colloq, query) ||
                 matchSearch(item.plaintext, query) ||
                 matchSearch(item.stats_summary, query) ||
                 matchSearch(item.description, query);
        }});
      }}

      // 4. ソート
      itemsList.sort((a, b) => {{
        if (currentItemSort === "price_desc") {{
          return (b.gold?.total || 0) - (a.gold?.total || 0);
        }} else if (currentItemSort === "price_asc") {{
          return (a.gold?.total || 0) - (b.gold?.total || 0);
        }} else if (currentItemSort === "name_asc") {{
          return (a.name || "").localeCompare(b.name || "", "ja");
        }}
        return 0;
      }});

      itemsList.forEach(item => {{
        const card = document.createElement("div");
        card.className = "item-grid-card";
        card.onclick = () => openItemDetail(item.id);

        const patch = DEFAULT_PATCH;
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{item.id}}.png`;
        const price = item.gold?.total ? `${{item.gold.total}} G` : "無料";
        const statsSummary = item.stats_summary ? `<div class="item-card-stats" title="${{item.stats_summary}}">${{item.stats_summary}}</div>` : "";

        card.innerHTML = `
          <img class="item-card-icon" src="${{imgUrl}}" alt="${{item.name}}" loading="lazy" onerror="this.src='icon.png';">
          <div class="item-card-name" title="${{item.name}}">${{item.name}}</div>
          <div class="item-card-price">💰 ${{price}}</div>
          ${{statsSummary}}
        `;
        itemsGridEl.appendChild(card);
      }});

      if (itemCountStatusEl) {{
        itemCountStatusEl.textContent = `表示中: ${{itemsList.length}} 個 / 全 ${{Object.keys(ITEMS).length}} 個`;
      }}
    }}

    if (itemSearchInput) {{
      itemSearchInput.addEventListener("input", (e) => {{
        itemSearchKeyword = e.target.value;
        renderItemsList();
      }});
    }}

    if (itemSortSelect) {{
      itemSortSelect.addEventListener("change", (e) => {{
        currentItemSort = e.target.value;
        renderItemsList();
      }});
    }}

    document.querySelectorAll(".item-cat-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".item-cat-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentItemCat = btn.getAttribute("data-cat");
        renderItemsList();
      }});
    }});

    // ステータスフィルターのチェックボックス＆全解除ボタンのイベント登録
    document.querySelectorAll(".stat-filter-chk").forEach(chk => {{
      chk.addEventListener("change", () => {{
        renderItemsList();
      }});
    }});

    const clearStatFiltersBtn = document.getElementById("clearStatFiltersBtn");
    if (clearStatFiltersBtn) {{
      clearStatFiltersBtn.onclick = () => {{
        document.querySelectorAll(".stat-filter-chk").forEach(chk => chk.checked = false);
        renderItemsList();
      }};
    }}

    // ==========================================
    // 対面対策シミュレーター制御 (Phase 4)
    // ==========================================
    let simMyChampId = null;
    let simOppChampId = null;
    let simCurrentPickingTarget = null; // 'me' or 'opp'
    let simPickerRole = "ALL";
    let simPickerAttack = "ALL";
    let simPickerDamage = "ALL";
    let simPickerSearch = "";

    const simCardMe = document.getElementById("simCardMe");
    const simCardOpp = document.getElementById("simCardOpp");
    const simImgMe = document.getElementById("simImgMe");
    const simImgOpp = document.getElementById("simImgOpp");
    const simNameMe = document.getElementById("simNameMe");
    const simNameOpp = document.getElementById("simNameOpp");
    const simRoleMe = document.getElementById("simRoleMe");
    const simRoleOpp = document.getElementById("simRoleOpp");

    const simEmptyPrompt = document.getElementById("simEmptyPrompt");
    const simResultArea = document.getElementById("simResultArea");
    const simAdvantageBadge = document.getElementById("simAdvantageBadge");
    const simAdvantageDesc = document.getElementById("simAdvantageDesc");
    const simSustainWarning = document.getElementById("simSustainWarning");
    const simLaningTips = document.getElementById("simLaningTips");
    const simItemList = document.getElementById("simItemList");
    const simCombosArea = document.getElementById("simCombosArea");

    const simPickerModal = document.getElementById("simPickerModal");
    const simPickerCloseBtn = document.getElementById("simPickerCloseBtn");
    const simPickerTitle = document.getElementById("simPickerTitle");
    const simSearchInput = document.getElementById("simSearchInput");
    const simPickerGrid = document.getElementById("simPickerGrid");

    function openSimPicker(target) {{
      simCurrentPickingTarget = target;
      if (simPickerTitle) {{
        simPickerTitle.textContent = target === 'me' ? '👑 あなたのチャンピオンを選択' : '👿 対面の相手チャンピオンを選択';
      }}
      if (simSearchInput) simSearchInput.value = "";
      simPickerSearch = "";
      if (simPickerModal) simPickerModal.classList.add("open");
      renderSimPickerGrid();
      if (!history.state || history.state.modal !== 'sim_picker') {{
        history.pushState({{ modal: 'sim_picker' }}, '');
      }}
    }}

    function closeSimPicker() {{
      if (simPickerModal) simPickerModal.classList.remove("open");
    }}

    if (simPickerCloseBtn) {{
      simPickerCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'sim_picker') history.back();
        else closeSimPicker();
      }};
    }}

    if (simPickerModal) {{
      simPickerModal.onclick = (e) => {{
        if (e.target === simPickerModal) {{
          if (history.state && history.state.modal === 'sim_picker') history.back();
          else closeSimPicker();
        }}
      }};
    }}

    function renderSimPickerGrid() {{
      if (!simPickerGrid) return;
      simPickerGrid.innerHTML = "";
      const q = simPickerSearch.trim();

      // 日本語五十音順（あいうえお順）にソート (濱田くんの重要指定！)
      let sortedChamps = Object.values(CHAMPIONS).slice().sort((a, b) => {{
        return (a.name || "").localeCompare(b.name || "", "ja");
      }});

      sortedChamps.forEach(champ => {{
        // 1. ロール絞り込み
        if (simPickerRole !== "ALL") {{
          if (!champ.roles || !champ.roles.includes(simPickerRole)) return;
        }}

        // 2. AA攻撃タイプ絞り込み (近接 / 遠隔)
        if (simPickerAttack !== "ALL") {{
          const attType = champ.attack_type?.type || (champ.stats?.attackrange <= 250 ? "MELEE" : "RANGED");
          if (simPickerAttack === "MELEE") {{
            if (attType !== "MELEE" && attType !== "HYBRID") return;
          }} else if (simPickerAttack === "RANGED") {{
            if (attType !== "RANGED" && attType !== "HYBRID") return;
          }}
        }}

        // 3. ダメージ属性絞り込み (AD / AP / TANK)
        if (simPickerDamage !== "ALL") {{
          const pType = champ.damage_profile?.primary_type || "AD";
          if (simPickerDamage === "AD") {{
            if (pType !== "AD" && pType !== "HYBRID") return;
          }} else if (simPickerDamage === "AP") {{
            if (pType !== "AP" && pType !== "HYBRID") return;
          }} else if (simPickerDamage === "TANK") {{
            if (pType !== "TANK") return;
          }}
        }}

        // 4. 検索クエリ (ひらがな・カタカナ・英字部分一致対応)
        if (q) {{
          const isHit = matchSearch(champ.name, q) || matchSearch(champ.id, q);
          if (!isHit) return;
        }}

        const item = document.createElement("div");
        item.className = "sim-picker-item";
        const patch = champ.patch || DEFAULT_PATCH;
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{champ.id}}.png`;

        // AAタイプ＆属性ミニアイコン
        const att = champ.attack_type || {{}};
        const attRange = champ.stats?.attackrange || 175;
        let attIcon = "🗡️";
        if (att.type === "RANGED" || (!att.type && attRange > 250)) {{
          attIcon = "🏹";
        }} else if (att.type === "HYBRID") {{
          attIcon = "🔄";
        }}

        const dp = champ.damage_profile || {{}};
        const dpText = dp.badge_text || "";

        item.innerHTML = `
          <div style="position:relative; width:48px; height:48px; margin:0 auto 4px;">
            <img class="sim-picker-img" src="${{imgUrl}}" alt="${{champ.name}}" loading="lazy" onerror="this.src='icon.png';" style="margin:0;">
            <span class="sim-picker-mini-badge" title="${{escapeHtml(att.label || '')}}">${{attIcon}}</span>
          </div>
          <div class="sim-picker-name">${{champ.name}}</div>
          ${{dpText ? `<div style="font-size:9px; color:var(--text-muted); line-height:1;">[${{dpText}}]</div>` : ""}}
        `;
        item.onclick = () => selectSimChamp(champ.id);
        simPickerGrid.appendChild(item);
      }});
    }}

    function selectSimChamp(champId) {{
      const c = CHAMPIONS[champId];
      if (!c) return;
      const patch = c.patch || DEFAULT_PATCH;
      const dp = c.damage_profile || {{}};

      if (simCurrentPickingTarget === 'me') {{
        simMyChampId = champId;
        if (simCardMe) {{
          simCardMe.classList.remove("empty");
          simCardMe.classList.add("selected");
          const plusEl = simCardMe.querySelector(".sim-slot-plus");
          if (plusEl) plusEl.style.display = "none";
        }}
        if (simImgMe) {{
          simImgMe.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{c.id}}.png`;
          simImgMe.style.display = "block";
        }}
        if (simNameMe) simNameMe.textContent = c.name;
        if (simRoleMe) simRoleMe.textContent = c.roles ? c.roles.join(" / ") : "";

        const dmgBadgeMe = document.getElementById("simDamageBadgeMe");
        const detailBtnMe = document.getElementById("simDetailBtnMe");
        if (dmgBadgeMe && dp.badge_text) {{
          dmgBadgeMe.textContent = dp.badge_text;
          dmgBadgeMe.className = `damage-badge ${{dp.badge_class || "badge-ad"}}`;
          dmgBadgeMe.style.display = "inline-flex";
        }}
        if (detailBtnMe) detailBtnMe.style.display = "inline-flex";
      }} else {{
        simOppChampId = champId;
        if (simCardOpp) {{
          simCardOpp.classList.remove("empty");
          simCardOpp.classList.add("selected");
          const plusEl = simCardOpp.querySelector(".sim-slot-plus");
          if (plusEl) plusEl.style.display = "none";
        }}
        if (simImgOpp) {{
          simImgOpp.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{c.id}}.png`;
          simImgOpp.style.display = "block";
        }}
        if (simNameOpp) simNameOpp.textContent = c.name;
        if (simRoleOpp) simRoleOpp.textContent = c.roles ? c.roles.join(" / ") : "";

        const dmgBadgeOpp = document.getElementById("simDamageBadgeOpp");
        const detailBtnOpp = document.getElementById("simDetailBtnOpp");
        if (dmgBadgeOpp && dp.badge_text) {{
          dmgBadgeOpp.textContent = dp.badge_text;
          dmgBadgeOpp.className = `damage-badge ${{dp.badge_class || "badge-ad"}}`;
          dmgBadgeOpp.style.display = "inline-flex";
        }}
        if (detailBtnOpp) detailBtnOpp.style.display = "inline-flex";
      }}

      if (history.state && history.state.modal === 'sim_picker') history.back();
      else closeSimPicker();

      updateSimAnalysis();
    }}

    // 対面シミュレーターから選んだチャンプの詳細ページへ飛ぶ関数 (濱田くんの重要指定！)
    function viewSimChampDetail(e, who) {{
      if (e) e.stopPropagation();
      const cid = (who === 'me') ? simMyChampId : simOppChampId;
      if (cid && CHAMPIONS[cid]) {{
        openDetail(cid);
      }}
    }}

    if (simSearchInput) {{
      simSearchInput.addEventListener("input", (e) => {{
        simPickerSearch = e.target.value;
        renderSimPickerGrid();
      }});
    }}

    document.querySelectorAll(".sim-role-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".sim-role-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        simPickerRole = btn.getAttribute("data-sim-role");
        renderSimPickerGrid();
      }});
    }});

    // ピッカー用AAタイプ＆属性絞り込みボタンイベント
    document.querySelectorAll(".sim-chip-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const filterType = btn.getAttribute("data-sim-filter");
        const val = btn.getAttribute("data-val");
        const parentGroup = btn.closest(".filter-group");
        if (parentGroup) {{
          parentGroup.querySelectorAll(".sim-chip-btn").forEach(b => b.classList.remove("active"));
        }}
        btn.classList.add("active");

        if (filterType === "attack") {{
          simPickerAttack = val;
        }} else if (filterType === "damage") {{
          simPickerDamage = val;
        }}
        renderSimPickerGrid();
      }});
    }});

    let simSelectedLane = "AUTO";
    document.querySelectorAll(".sim-lane-tab").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".sim-lane-tab").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        simSelectedLane = btn.getAttribute("data-lane") || "AUTO";
        updateSimAnalysis();
      }});
    }});

    function updateSimAnalysis() {{
      if (!simMyChampId || !simOppChampId) {{
        if (simEmptyPrompt) simEmptyPrompt.style.display = "block";
        if (simResultArea) simResultArea.style.display = "none";
        return;
      }}

      if (simEmptyPrompt) simEmptyPrompt.style.display = "none";
      if (simResultArea) simResultArea.style.display = "block";

      const me = CHAMPIONS[simMyChampId];
      const opp = CHAMPIONS[simOppChampId];

      // 対象レーンの決定: AUTO時は自分と相手の共通ロール優先、なければ自分の第1ロール
      let targetLane = simSelectedLane;
      if (targetLane === "AUTO") {{
        const meRoles = me.roles || ["TOP"];
        const oppRoles = opp.roles || [];
        const commonRole = meRoles.find(r => oppRoles.includes(r));
        targetLane = commonRole || meRoles[0] || "TOP";
      }}

      // (自分, 相手, レーン, パッチ) に一致する実測データのみを検索（別レーン統計は混同しない）
      let measuredData = null;
      if (me.matchup_matrix_by_role && me.matchup_matrix_by_role[targetLane] && me.matchup_matrix_by_role[targetLane][opp.id]) {{
        const candidate = me.matchup_matrix_by_role[targetLane][opp.id];
        if (candidate.is_estimated === false && candidate.role === targetLane) {{
          measuredData = candidate;
        }}
      }}
      if (!measuredData && me.role_data && me.role_data[targetLane] && me.role_data[targetLane].matchups) {{
        const rm = me.role_data[targetLane].matchups;
        const favHit = (rm.favorable || []).find(m => (m.champion_id === opp.id || m.name === opp.name) && (!m.role || m.role === targetLane));
        const unfavHit = (rm.unfavorable || []).find(m => (m.champion_id === opp.id || m.name === opp.name) && (!m.role || m.role === targetLane));
        if (favHit) measuredData = Object.assign({{ advantage: "fav", is_estimated: false, role: targetLane }}, favHit);
        else if (unfavHit) measuredData = Object.assign({{ advantage: "unfav", is_estimated: false, role: targetLane }}, unfavHit);
      }}

      const evalData = measuredData || computeHeuristicMatchup(me, opp, targetLane);
      const isEst = evalData.is_estimated !== false;

      let advClass = "sim-adv-even";
      const advCode = (evalData.advantage || "").toLowerCase();
      if (advCode === "fav" || advCode === "favorable") advClass = "sim-adv-fav";
      else if (advCode === "unfav" || advCode === "unfavorable") advClass = "sim-adv-unfav";

      const advText = evalData.advantage_label || (isEst ? "特性推定" : "実測統計");
      let advReason = evalData.reason || `${{me.name}} と ${{opp.name}} のマッチアップ。`;
      if (advReason.includes(" | ")) {{
        advReason = advReason.split(" | ").slice(1).join(" | ");
      }}

      const simMatchupSourceTag = document.getElementById("simMatchupSourceTag");
      const simAdvantageMeta = document.getElementById("simAdvantageMeta");

      if (simMatchupSourceTag) {{
        if (evalData.source === "mirror") {{
          simMatchupSourceTag.textContent = `📊 判定区分: ミラーマッチ (${{targetLane}})`;
        }} else if (!isEst) {{
          simMatchupSourceTag.textContent = `📊 判定区分: 実測統計データ (${{targetLane}}レーン専用)`;
        }} else {{
          simMatchupSourceTag.textContent = `🔍 判定区分: ヒューリスティック特性推定 (${{targetLane}}レーン実測統計なし)`;
        }}
      }}

      if (simAdvantageBadge) {{
        simAdvantageBadge.className = `sim-adv-badge ${{advClass}}`;
        simAdvantageBadge.textContent = advText;
      }}
      if (simAdvantageDesc) simAdvantageDesc.textContent = advReason;

      if (simAdvantageMeta) {{
        if (evalData.source === "mirror") {{
          simAdvantageMeta.textContent = `対象レーン: ${{targetLane}} | パッチ: ${{evalData.patch || DEFAULT_PATCH}}`;
        }} else if (!isEst) {{
          simAdvantageMeta.textContent =
            `【実測データ情報】参照元: ${{evalData.source || "opgg_stats"}} | レーン: ${{evalData.role || targetLane}} | ` +
            `地域: ${{evalData.region || "Global"}} | ランク帯: ${{evalData.tier || "Emerald+"}} | ` +
            `パッチ: ${{evalData.patch || DEFAULT_PATCH}} | 取得時期: ${{evalData.fetched_at || "2026-10"}} | ` +
            `区分: ${{evalData.sample_note || "OP.GG ロール別カウンター統計"}}`;
        }} else {{
          const factorsStr = (evalData.estimation_factors || []).join(" / ") || "基礎ステータス均衡";
          simAdvantageMeta.textContent =
            `【推定の要因】${{factorsStr}} ｜ 【推定の限界】${{evalData.estimation_limitation || "基礎特性からの推定であり実戦統計勝率ではありません。"}}`;
        }}
      }}

      // 2. 相手のサステイン警告 (escapeHtml による安全なレンダリング)
      if (simSustainWarning) {{
        if (opp.sustain_info && opp.sustain_info.has_sustain) {{
          simSustainWarning.style.display = "block";
          simSustainWarning.innerHTML = `🩸 <strong>【相手は高回復・サステイン持ち！】</strong> ${{escapeHtml(opp.name)}} は強力な回復能力を誇ります。${{escapeHtml(opp.sustain_info.reason || "")}} 早期リコール時に必ず「重傷アイテム（回復阻害）」を購入してください。`;
        }} else {{
          simSustainWarning.style.display = "none";
        }}
      }}

      // レーン戦注意点 ＆ ダメージ属性対策 (escapeHtml 徹底)
      if (simLaningTips) {{
        const oppWeaknesses = escapeHtml((opp.overview?.weaknesses || []).join("、") || "主要スキルのクールダウン中が最大の仕掛けどころです。");
        const oppDp = opp.damage_profile || {{}};
        let dualNote = "";
        if (oppDp.has_dual_build) {{
          dualNote = `<div style="margin-top:6px; padding:6px 10px; background:rgba(245, 158, 11, 0.12); border-left:3px solid #f59e0b; border-radius:4px; color:#fde68a;">⚠️ <strong>【対面注意・AD/AP両型あり】</strong> ${{escapeHtml(oppDp.dual_build_desc || "")}}</div>`;
        }}
        const roleLaning = me.role_data?.[targetLane]?.gameplay_notes?.laning || me.gameplay_notes?.laning || "相手のスキルを躱してからトレードに入りましょう。";
        simLaningTips.innerHTML = `
          <div style="margin-bottom: 6px;"><strong>【相手の属性 ＆ 対策】</strong> 主ダメージ: <span class="damage-badge ${{escapeHtml(oppDp.badge_class || 'badge-ad')}}">${{escapeHtml(oppDp.badge_text || 'AD')}} (${{escapeHtml(oppDp.label || '')}})</span> ➔ <strong>${{escapeHtml(oppDp.counter_defense || '防御アイテムを選択')}}</strong></div>
          ${{dualNote}}
          <div style="margin-bottom: 6px; margin-top: 6px;"><strong>【相手の弱み・突くべき隙】</strong> ${{oppWeaknesses}}</div>
          <div><strong>【あなたの立ち回り指針 (${{escapeHtml(targetLane)}})】</strong> ${{escapeHtml(roleLaning)}}</div>
        `;
      }}

      // 3. 積むべき対策 ＆ おすすめアイテムの選定 (複数アイテム)
      if (simItemList) {{
        const recommendedItems = [];
        const seenIds = new Set();

        function findItemId(name) {{
          if (!name) return null;
          for (const [id, it] of Object.entries(ITEMS)) {{
            if (it.name === name) return id;
          }}
          return null;
        }}

        function addItem(id, name, tag, reason) {{
          if (!id && name) {{
            id = findItemId(name);
          }}
          if (id && !seenIds.has(id)) {{
            seenIds.add(id);
            recommendedItems.push({{ id, name: ITEMS[id]?.name || name, tag, reason }});
          }}
        }}

        const oppRoles = opp.roles || [];
        const oppClasses = opp.classes || opp.tags || [];
        const oppResource = opp.resource || "";
        const myRoles = me.roles || [];
        const myClasses = me.classes || me.tags || [];
        const oppDp = opp.damage_profile || {{}};
        const isOppAP = oppDp.primary_type === "AP" || (oppDp.primary_type === "TANK" && !["DrMundo", "KSante", "Poppy", "Sion", "Skarner"].includes(opp.id));
        const isOppDual = oppDp.has_dual_build;

        // ① 対面属性・サステイン対策特化
        if (opp.sustain_info?.has_sustain) {{
          if (myClasses.includes("Mage") || (me.resource && me.resource.includes("マナ") && !myClasses.includes("Marksman"))) {{
            addItem("3916", "忘却のオーブ", "対面重傷", "回復阻害(AP)");
          }} else if (myClasses.includes("Tank")) {{
            addItem("3076", "ブランブル ベスト", "対面重傷", "回復阻害(AR)");
          }} else {{
            addItem("3123", "エクスキューショナー コーリング", "対面重傷", "回復阻害(AD)");
          }}
        }}

        // 対面ダメージ属性対策（靴＋防具）
        if (isOppDual) {{
          // 両型持ちの場合: 相手の型に合わせたAR/MR両方の選択肢を提示
          addItem("3047", "プレート スチールキャップ", "対AD型", "相手がADビルド時の通常攻撃低減");
          addItem("3111", "マーキュリー ブーツ", "対AP型", "相手がAPビルド時の魔法耐性&CC低減");
          if (myClasses.includes("Tank") || myClasses.includes("Fighter")) {{
            addItem("2504", "ケイニック ルーケルン", "対AP防具", "相手がAPビルド時の魔法シールド");
          }}
        }} else if (isOppAP) {{
          addItem("3111", "マーキュリー ブーツ", "対AP靴", "魔法耐性 ＆ 行動妨害低減");
          if (myClasses.includes("Tank") || myClasses.includes("Fighter")) {{
            addItem("2504", "ケイニック ルーケルン", "対AP防具", "魔法シールド ＆ 高MR");
          }} else if (myClasses.includes("Assassin") || myClasses.includes("Marksman")) {{
            addItem("3156", "マルモティウスの胃袋", "対AP火力", "魔法シールド ＆ 攻撃力");
          }}
        }} else {{
          addItem("3047", "プレート スチールキャップ", "対AD靴", "通常攻撃被ダメ12%低減");
          if (myClasses.includes("Tank")) {{
            addItem("3143", "ランデュイン オーメン", "対AD防具", "クリティカル＆通常攻撃耐性");
          }} else if (myClasses.includes("Fighter")) {{
            addItem("6333", "デス ダンス", "対AD耐久", "被ダメ遅延 ＆ キル時回復");
          }}
        }}

        // 相手が硬いタンクの場合の貫通アイテム
        if (oppClasses.includes("Tank") || ["Sion", "Malphite", "ChoGath", "Ornn", "DrMundo", "Shen", "Rammus", "TahmKench"].includes(opp.id)) {{
          if (myClasses.includes("Mage")) {{
            addItem("3135", "ヴォイド スタッフ", "対タンク貫通", "40% 魔法防御貫通");
          }} else {{
            addItem("3071", "ブラック クリーバー", "対タンク破甲", "物理防御破壊 ＆ 加速");
          }}
        }}

        // ② あなたの主戦力・中核コアアイテム (採用率・勝率重視)
        const myCoreBuild = me.core_build || (me.build_patterns && me.build_patterns[0]?.core) || [];
        myCoreBuild.forEach(itemName => {{
          if (recommendedItems.length < 5) {{
            addItem(null, itemName, "主戦力コア", "対面戦を制する中核コア");
          }}
        }});

        // ③ 後半・交戦の保険・生存アイテム
        if (recommendedItems.length < 6) {{
          if (myClasses.includes("Fighter") || myClasses.includes("Tank")) {{
            addItem("3053", "ステラックの篭手", "交戦生存", "瀕死時巨大シールド＆耐性");
          }} else if (myClasses.includes("Mage")) {{
            addItem("3157", "ゾーニャの砂時計", "緊急無敵", "2.5秒無敵でバースト回避");
          }} else if (myClasses.includes("Marksman") || myClasses.includes("Assassin")) {{
            addItem("3026", "ガーディアン エンジェル", "復活保険", "死亡時HP50%で復活");
          }}
        }}

        simItemList.innerHTML = recommendedItems.slice(0, 6).map(it => {{
          const itemImg = `https://ddragon.leagueoflegends.com/cdn/${{DEFAULT_PATCH}}/img/item/${{escapeHtml(it.id)}}.png`;
          return `
            <div class="sim-item-card clickable-item" data-item-id="${{escapeHtml(it.id)}}" title="タップして性能詳細を表示">
              <img class="sim-item-img" src="${{itemImg}}" alt="${{escapeHtml(it.name)}}" onerror="this.src='icon.png';">
              <div class="sim-item-info">
                <div class="sim-item-top">
                  <span class="sim-item-tag">${{escapeHtml(it.tag)}}</span>
                  <span class="sim-item-name">${{escapeHtml(it.name)}}</span>
                </div>
                <div class="sim-item-reason">${{escapeHtml(it.reason)}}</div>
              </div>
            </div>
          `;
        }}).join("");

        simItemList.querySelectorAll(".clickable-item").forEach(el => {{
          el.onclick = (e) => {{
            e.stopPropagation();
            const iid = el.getAttribute("data-item-id");
            if (iid && ITEMS[iid]) openItemDetail(iid);
          }};
        }});
      }}

      // 4. 狙い目コンボ
      if (simCombosArea) {{
        const combos = me.combos || [];
        simCombosArea.innerHTML = combos.map(cb => `
          <div class="combo-card">
            <div class="combo-name">🥊 ${{escapeHtml(cb.name)}}</div>
            <div class="combo-recipe">${{escapeHtml(cb.recipe)}}</div>
            <div class="combo-desc">${{escapeHtml(cb.desc)}}</div>
          </div>
        `).join("");
      }}
    }}

    // スマホのジェスチャースワイプ「戻る」イベント対応（アプリ終了防止・モーダル多重スタック制御）
    window.addEventListener("popstate", (e) => {{
      if (simPickerModal && simPickerModal.classList.contains("open")) {{
        closeSimPicker();
        return;
      }}
      if (itemDetailModalEl && itemDetailModalEl.classList.contains("open")) {{
        closeItemDetailModal();
        return;
      }}
      if (modalEl && modalEl.classList.contains("open")) {{
        closeDetailModal();
        return;
      }}
      if (changelogModalEl && changelogModalEl.classList.contains("open")) {{
        closeChangelogModal();
        return;
      }}
    }});

    // ESCキー対応（モーダル多重スタック制御）
    window.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") {{
        if (simPickerModal && simPickerModal.classList.contains("open")) {{
          if (history.state && history.state.modal === 'sim_picker') history.back();
          else closeSimPicker();
          return;
        }}
        if (itemDetailModalEl && itemDetailModalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'item_detail') history.back();
          else closeItemDetailModal();
          return;
        }}
        if (modalEl && modalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'champion_detail') history.back();
          else closeDetailModal();
          return;
        }}
        if (changelogModalEl && changelogModalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'changelog') history.back();
          else closeChangelogModal();
          return;
        }}
      }}
    }});

    // メインナビゲーションタブ切り替え
    const champControlsEl = document.getElementById("champControls");
    const viewChampsEl = document.getElementById("viewChampions");
    const viewItemsEl = document.getElementById("viewItems");
    const viewSimEl = document.getElementById("viewSimulator");
    const viewPicksEl = document.getElementById("viewPicks");

    // ユーザー提供のガレン対面表と、暫定の補足候補。勝率統計ではない。
    const pickRows = [
      ["アカリ","ガレン","耐えて短期トレード"],["アトロックス","ガレン","Qの外側を避ける"],["アンベッサ","ガレン","ダッシュ後を狙う"],["イラオイ","ガレン","Eを避けて短期戦"],["ウラジミール","ガレン","序盤に圧力"],["オラフ","ガレン","R中の長期戦を避ける"],["カシオペア","ガレン","接近が難しいので慎重に"],["ガリオ","ガレン","AP耐久型に物理ダメージ"],["ガングプランク","ガレン","樽の処理が重要"],["クレッド","ガレン","乗馬中の長期戦を避ける"],["グウェン","ガレン","Q中央を回避"],["グラガス","ガレン","回復と妨害に注意"],["ケイル","ガレン","序盤に主導権"],["ケネン","ガレン","無理な接近を避ける"],["コグ＝マウ","ガレン","珍しいTOP、序盤に圧力"],["ザーヘン","ガレン","長期戦を避ける"],["シンジド","ガレン","追いかけすぎない"],["スウェイン","ガレン","長期戦を避ける"],["ダリウス","ガレン","不利ならBANを検討"],["トランドル","ガレン","長い殴り合いを避ける"],["ニーコ","ガレン","分身とEに注意"],["ヘイマーディンガー","ガレン","タレットに無理に突っ込まない"],["ボリベア","ガレン","2回目のWを受けない"],["ランブル","ガレン","長い炎上トレードを避ける"],["リヴェン","ガレン","短期トレードで対応"],["リサンドラ","ガレン","無理なダイブをしない"],["リリア","ガレン","移動速度と継続ダメージに注意"],["ワーウィック","ガレン","低HP時の回復に注意"],
      ["マルファイト","モルデカイザー","対タンク枠。孤立Qを狙う"],["オーン","モルデカイザー","タンク対策。鍛冶神の呼び声に注意"],["サイオン","モルデカイザー","継続魔法ダメージ。Qの範囲から出る"],["チョ＝ガス","モルデカイザー","タンク対策。QとRに注意"],["タム・ケンチ","モルデカイザー","長期戦と割合ダメージを意識"],
      ["ウディア","モルデカイザー","継続戦闘を意識"],["カ・サンテ","モルデカイザー","AP継続ダメージを活用"],["ガレン","モルデカイザー","長期戦で優位を狙う"],["シェン","モルデカイザー","Rで相手のRによる離脱を妨害"],["セト","モルデカイザー","W中央を回避"],["ティーモ","モルデカイザー","Qのブラインドを受けてもスキルで戦える"],["ドクター・ムンド","モルデカイザー","パッシブによる行動妨害への耐性に注意"],["ナサス","モルデカイザー","序盤にスタックを妨害"],["ポッピー","モルデカイザー","AP継続ダメージを活用"],["ヨリック","モルデカイザー","メイデンとグールの処理に注意"],
      ["トリンダメア","マルファイト","通常攻撃対策。R中の殴り合いを避ける"],["ヤスオ","マルファイト","対AD通常攻撃。Eの攻撃速度低下を活用"],["ヨネ","マルファイト","通常攻撃主体への候補。魔法ダメージとEの戻り位置に注意"],["クイン","マルファイト","対ADレンジ。R習得後に反撃"],["ヴェイン","マルファイト","対ADレンジ。Wの確定ダメージに注意"],["ジェイス","マルファイト","対ADレンジ。遠隔攻撃を受けすぎない"],
      ["アーゴット","マルファイト","Eで攻撃速度を下げる"],["アッシュ","マルファイト","対ADレンジ"],["ジャックス","マルファイト","Eの攻撃速度低下を活用。魔法ダメージに注意"],["イレリア","マルファイト","攻撃速度低下を活用"],["ウーコン","マルファイト","物理ダメージ対策"],["カミール","マルファイト","対ADだが確定ダメージに注意"],["ジャーヴァンIV","マルファイト","対AD。防御低下に注意"],["ナー","マルファイト","対ADレンジ。メガナーに注意"],["ノクターン","マルファイト","対AD。スペルシールドに注意"],["パンテオン","マルファイト","対AD。序盤は慎重に"],["フィオラ","マルファイト","Wと確定ダメージに注意"],["ブライアー","マルファイト","通常攻撃主体。回復に注意"],["レネクトン","マルファイト","序盤のバーストを耐える"],["レク＝サイ","マルファイト","対AD。確定ダメージに注意"],
      ["モルデカイザー","オラフ","習得後の候補。RでモルデカイザーのRを防げるが、長期戦は体力と装備を確認"]
    ];
    let pickFilter = "すべて";
    function renderPickGuide() {{
      const query = document.getElementById("pickSearch").value.trim().toLocaleLowerCase();
      const normalizedQuery = query === "アックス" ? "ジャックス" : query;
      const rows = pickRows.filter(row => (pickFilter === "すべて" || row[1] === pickFilter) && row[0].toLocaleLowerCase().includes(normalizedQuery)).sort((a,b) => a[0].localeCompare(b[0], "ja"));
      document.getElementById("pickCount").textContent = rows.length + "対面を表示";
      const list = document.getElementById("pickList");
      list.replaceChildren();
      if (!rows.length) {{ list.textContent = "該当する対面はありません。未掲載の対面はガレンを基準に検討してください。"; return; }}
      rows.forEach(row => {{
        const card = document.createElement("div"); card.className = "pick-row";
        const title = document.createElement("strong"); title.textContent = row[0] + " → ";
        const choice = document.createElement("span");
        const choiceClasses = {{ "ガレン": "garen", "モルデカイザー": "mordekaiser", "マルファイト": "malphite", "オラフ": "olaf" }};
        choice.className = "pick-choice-" + choiceClasses[row[1]]; choice.textContent = row[1];
        title.append(choice);
        const reason = document.createElement("p"); reason.textContent = row[2];
        card.append(title, reason); list.append(card);
      }});
    }}
    document.getElementById("pickSearch").addEventListener("input", renderPickGuide);
    document.querySelectorAll("[data-pick]").forEach(button => button.addEventListener("click", () => {{
      pickFilter = button.dataset.pick;
      document.querySelectorAll("[data-pick]").forEach(b => {{ b.classList.toggle("active", b === button); b.setAttribute("aria-pressed", String(b === button)); }});
      renderPickGuide();
    }}));
    renderPickGuide();

    document.querySelectorAll(".nav-tab").forEach(tab => {{
      tab.addEventListener("click", () => {{
        document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const target = tab.getAttribute("data-tab");
        viewPicksEl.style.display = target === "picks" ? "block" : "none";

        if (target === "champions") {{
          viewChampsEl.style.display = "block";
          viewItemsEl.style.display = "none";
          viewSimEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "flex";
        }} else if (target === "items") {{
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "block";
          viewSimEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "none";
          renderItemsList();
        }} else if (target === "simulator" || target === "picks") {{
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "none";
          viewSimEl.style.display = target === "simulator" ? "block" : "none";
          if (champControlsEl) champControlsEl.style.display = "none";
        }}
      }});
    }});

    // 検索入力イベント
    searchInput.addEventListener("input", (e) => {{
      searchKeyword = e.target.value;
      renderList();
    }});

    // ロールタブ切り替え
    document.querySelectorAll(".role-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".role-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentRole = btn.getAttribute("data-role");
        renderList();
      }});
    }});

    // 複合フィルターチップス (AAタイプ / ダメージ属性 / 特性)
    document.querySelectorAll("#champFilterBar .chip-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const filterType = btn.getAttribute("data-filter");
        const val = btn.getAttribute("data-val");

        if (btn.classList.contains("toggle-chip")) {{
          // トグルボタン (複数選択可能)
          if (btn.classList.contains("active")) {{
            btn.classList.remove("active");
            currentTraitFilters.delete(val);
          }} else {{
            btn.classList.add("active");
            currentTraitFilters.add(val);
          }}
        }} else {{
          // 単一選択ボタングループ
          const parentGroup = btn.closest(".filter-group");
          if (parentGroup) {{
            parentGroup.querySelectorAll(".chip-btn").forEach(b => b.classList.remove("active"));
          }}
          btn.classList.add("active");

          if (filterType === "attack") {{
            currentAttackFilter = val;
          }} else if (filterType === "damage") {{
            currentDamageFilter = val;
          }}
        }}
        renderList();
      }});
    }});

    // フィルターリセットボタン
    const chipResetBtn = document.getElementById("chipResetBtn");
    if (chipResetBtn) {{
      chipResetBtn.addEventListener("click", () => {{
        currentAttackFilter = "ALL";
        currentDamageFilter = "ALL";
        currentTraitFilters.clear();
        document.querySelectorAll("#champFilterBar .chip-btn").forEach(btn => {{
          if (btn.getAttribute("data-val") === "ALL") {{
            btn.classList.add("active");
          }} else {{
            btn.classList.remove("active");
          }}
        }});
        renderList();
      }});
    }}

    // 初期レンダリング
    renderList();
    renderItemsList();

    // チャンピオン画像バックグラウンド・プリフェッチ（完全オフライン化）
    function prewarmChampionImages() {{
      if (!('serviceWorker' in navigator) || !navigator.onLine) return;
      const champList = Object.values(CHAMPIONS);
      let idx = 0;
      function fetchNextBatch() {{
        if (idx >= champList.length) return;
        const end = Math.min(idx + 10, champList.length);
        for (let i = idx; i < end; i++) {{
          const c = champList[i];
          const patch = c.patch || DEFAULT_PATCH;
          const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{c.id}}.png`;
          const img = new Image();
          img.src = imgUrl;
        }}
        idx = end;
        setTimeout(fetchNextBatch, 250);
      }}
      setTimeout(fetchNextBatch, 1200);
    }}
    prewarmChampionImages();

    // Service Worker 登録（更新チェック付き）
    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', () => {{
        navigator.serviceWorker.register('sw.js')
          .then(reg => {{
            console.log('ServiceWorker registered:', reg.scope);
            reg.update();
          }})
          .catch(err => console.log('ServiceWorker registration failed:', err));
      }});
    }}
  </script>
</body>
</html>"""

    index_path = dist_dir / "index.html"
    root_index_path = base_dir / "index.html"
    print(f"単一HTML {index_path} および {root_index_path} を出力中...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(root_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Service Worker (sw.js) の生成 (バージョン＆HTMLハッシュ連動でキャッシュ名を自動更新)
    html_short_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()[:8]
    dynamic_core_cache = f"loldb-core-{latest_version}-{html_short_hash}"
    sw_content = """// LoLDB Service Worker - Dual Cache Architecture __VER_HASH__ (Scoped Cache Cleanup)
const CACHE_PREFIX = 'loldb-';
const CORE_CACHE = '__DYNAMIC_CORE_CACHE__';
const IMAGE_CACHE = 'loldb-images-v1'; // チャンピオン・アイテム・スペル画像オンデマンド＆段階プリフェッチキャッシュ

const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CORE_CACHE).then((cache) => {
      console.log('[SW] Pre-caching core offline assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        // 同一オリジン上の別アプリのキャッシュを消さないよう、'loldb-' で始まるキャッシュのみを管理・削除する
        if (key.startsWith(CACHE_PREFIX) && key !== CORE_CACHE && key !== IMAGE_CACHE) {
          console.log('[SW] Removing old LoLDB cache:', key);
          return caches.delete(key);
        }
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. メインHTML（ナビゲーション）は Network-First（オンライン時は最新、オフライン時はキャッシュ）
  if (event.request.mode === 'navigate' || url.pathname.endsWith('index.html') || url.pathname === '/' || url.pathname.endsWith('/')) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CORE_CACHE).then((cache) => cache.put(event.request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match('./index.html').then(response => response || caches.match('./')).then(response => response || caches.match('index.html'));
        })
    );
    return;
  }

  // 2. 画像リクエスト（Data Dragon CDN および ローカル画像）は Cache-First (永続画像キャッシュ)
  const isImage = event.request.destination === 'image' ||
                  url.pathname.match(/\\.(png|jpg|jpeg|svg|webp|ico)$/i) ||
                  url.hostname.includes('ddragon.leagueoflegends.com');

  if (isImage) {
    event.respondWith(
      caches.open(IMAGE_CACHE).then((imageCache) => {
        return imageCache.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(event.request).then((networkResponse) => {
            // クロスオリジン（no-cors）画像レスポンスは status が 0 (type: 'opaque') になるため、
            // status === 200 に加えて type === 'opaque' も確実にキャッシュに保存する！
            if (networkResponse && (networkResponse.status === 200 || networkResponse.type === 'opaque')) {
              imageCache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => {
            // オフライン時のローカルアイコンフォールバック
            return caches.match('./icon.png');
          });
        });
      })
    );
    return;
  }

  // 3. その他の静的アセットは CORE_CACHE による Cache-First
  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) {
        return response;
      }
      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
          const responseToCache = networkResponse.clone();
          caches.open(CORE_CACHE).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      });
    })
  );
});
"""
    sw_content = sw_content.replace("__VER_HASH__", f"{latest_version}-{html_short_hash}").replace("__DYNAMIC_CORE_CACHE__", dynamic_core_cache)
    sw_path = dist_dir / "sw.js"
    root_sw_path = base_dir / "sw.js"
    print(f"Service Worker {sw_path} を出力中...")
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)
    with open(root_sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)

    # PWA Manifest (manifest.json) の生成
    manifest_content = """{
  "name": "LoLDB",
  "short_name": "LoLDB",
  "start_url": "./index.html",
  "display": "standalone",
  "background_color": "#0b0f19",
  "theme_color": "#0f172a",
  "orientation": "any",
  "icons": [
    {
      "src": "./icon.png",
      "sizes": "120x120",
      "type": "image/png"
    },
    {
      "src": "./icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
"""
    manifest_path = dist_dir / "manifest.json"
    root_manifest_path = base_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)
    with open(root_manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    # GitHub Pages用 .nojekyll の配置
    (dist_dir / ".nojekyll").touch(exist_ok=True)
    (base_dir / ".nojekyll").touch(exist_ok=True)

    # プロジェクト直下の配布用ZIP (LoLDB_dist.zip) も自動同期更新
    zip_path = base_dir / "LoLDB_dist.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                full_p = Path(root) / file
                zf.write(full_p, full_p.relative_to(dist_dir))

    html_size_kb = os.path.getsize(index_path) / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    build()
