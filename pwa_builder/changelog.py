"""更新履歴を統合し、配布用の履歴一覧へ整形する。"""

import html
import json
import re
from pathlib import Path
from typing import NotRequired, TypedDict


XO_HISTORY_PATH = Path(r"C:\Project\XObsidian\Topics\LoLDB\Update_History.md")


class _ChangelogEntry(TypedDict):
    """保存済み履歴と Markdown から統合する一件分の記録。"""

    version: str
    date: NotRequired[str]
    title: NotRequired[str]
    items: NotRequired[list[str]]


# 過去バージョンの詳細箇条書き定義（Update_History.md側が1段落要約のみの古いエントリをリッチ表示するための補完辞書）
CURATED_CHANGELOG_ITEMS: dict[str, list[str]] = {
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

VERSION_ICONS: dict[str, str] = {
    "v1.7.1": "🛡️",
    "v1.6.0": "⚡",
    "v1.5.0": "🛡️",
    "v1.4.0": "🚀",
    "v1.3.0": "🛡️",
    "v1.1.0": "🎨",
    "v1.0.0": "✨",
}


def _parse_version_tuple(ver_str: str) -> tuple[int, ...]:
    """バージョンから並べ替え用の数字を最大三つ取り出し、欠けた桁はゼロで補う。"""
    nums = [int(x) for x in re.findall(r"\d+", ver_str)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def _parse_markdown_update_block(block_text: str) -> _ChangelogEntry | None:
    """Markdown の履歴一件からバージョン、日付、見出し、更新内容を抽出する。"""
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
    """保存済み履歴と Markdown を統合し、最新バージョンと履歴 HTML を返す。"""
    entries_by_ver: dict[str, _ChangelogEntry] = {}

    # 1. ローカル保存済み changelog_history.json があれば読み込む（単体環境用バックアップ）
    history_json_path = base_dir / "data" / "changelog_history.json"
    invalid_cache = f"更新履歴ファイルの形式が不正です: {history_json_path}"
    try:
        cached_list = json.loads(history_json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        cached_list = []
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(invalid_cache) from error
    if not isinstance(cached_list, list):
        raise ValueError(invalid_cache)
    for entry in cached_list:
        if not isinstance(entry, dict):
            raise ValueError(invalid_cache)
        version = entry.get("version", "")
        items = entry.get("items", [])
        if (
            not isinstance(version, str)
            or not isinstance(entry.get("date", ""), str)
            or not isinstance(items, list)
            or any(not isinstance(item, str) for item in items)
        ):
            raise ValueError(invalid_cache)
        if version:
            entries_by_ver[version] = entry

    # 2. Obsidian (XO) の全履歴マスター Update_History.md をパース
    if XO_HISTORY_PATH.exists():
        xo_text = XO_HISTORY_PATH.read_text(encoding="utf-8")
        chunks = re.split(r"(?=### 📅 \d{4}-\d{2}-\d{2}\s*\|\s*📢 アップデート)", xo_text)
        for chunk in chunks[1:]:
            parsed = _parse_markdown_update_block(chunk)
            if parsed and parsed["version"] != "v0.1.0":
                v = parsed["version"]
                if v in CURATED_CHANGELOG_ITEMS and (len(parsed["items"]) <= 1 or v in ("v2.5.0", "v2.5.2")):
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
