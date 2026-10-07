import json
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
ITEMS_JSON = BASE_DIR / "merged_data" / "all_items.json"

STARTUP_IDS = {
    "1055", "1056", "1054", "1082", "3070", "1083",  # ドラン系, ダークシール, 涙, カル
    "1101", "1102", "1103",                            # スコーチクロウ, ガストウォーカー, モスストンパー
    "3865", "3866", "3867", "3869", "3870", "3871", "3876", "3877", # ワールドアトラス系列
    "2003", "2031", "2033", "2055", "3340", "3364", "3363" # ポーション, ワード, レンズ
}

def analyze_stat_tags(item):
    """アイテムのstatsとdescriptionから上昇ステータスタグを抽出"""
    stats = item.get("stats", {}) or {}
    summary = item.get("stats_summary", "") or ""
    desc = item.get("description", "") or ""
    text = f"{summary} {desc}".lower()

    tags = set()

    # AD (攻撃力)
    if stats.get("FlatPhysicalDamageMod", 0) > 0 or "攻撃力" in summary or "attack damage" in text:
        tags.add("AD")

    # AP (魔力)
    if stats.get("FlatMagicDamageMod", 0) > 0 or "魔力" in summary or "ability power" in text:
        tags.add("AP")

    # AS (攻撃速度)
    if stats.get("PercentAttackSpeedMod", 0) > 0 or "攻撃速度" in summary or "attack speed" in text:
        tags.add("AS")

    # AR (物理防御)
    if stats.get("FlatArmorMod", 0) > 0 or "物理防御" in summary or "armor" in text:
        tags.add("AR")

    # MR (魔法耐性)
    if stats.get("FlatSpellBlockMod", 0) > 0 or "魔法耐性" in summary or "magic resist" in text:
        tags.add("MR")

    # HP (体力)
    if stats.get("FlatHPPoolMod", 0) > 0 or "体力 +" in summary or "体力+" in summary or "最大体力" in summary:
        tags.add("HP")

    # AH (スキルヘイスト)
    if "スキルヘイスト" in text or "ability haste" in text or "クールダウン" in text:
        tags.add("AH")

    # CRIT (クリティカル)
    if stats.get("FlatCritChanceMod", 0) > 0 or "クリティカル" in text or "critical strike" in text:
        tags.add("CRIT")

    # MS (移動速度)
    if stats.get("FlatMovementSpeedMod", 0) > 0 or stats.get("PercentMovementSpeedMod", 0) > 0 or "移動速度" in text:
        tags.add("MS")

    # LETHALITY (脅威 / 物理貫通)
    if "脅威" in text or "物理防御貫通" in text or "lethality" in text or "armor penetration" in text:
        tags.add("LETHALITY")

    # MAGICPEN (魔法防御貫通)
    if "魔法防御貫通" in text or "magic penetration" in text:
        tags.add("MAGICPEN")

    # VAMP (ライフスティール / オムニヴァンプ)
    if "ライフスティール" in text or "オムニヴァンプ" in text or "吸血" in text or "life steal" in text:
        tags.add("VAMP")

    # MANA (マナ / マナ回復)
    if stats.get("FlatMPPoolMod", 0) > 0 or "マナ" in summary or "基本マナ回復" in text:
        tags.add("MANA")

    # HPREGEN (体力回復)
    if stats.get("FlatHPRegenMod", 0) > 0 or "基本体力回復" in text or "体力自動回復" in text:
        tags.add("HPREGEN")

    return sorted(list(tags))

def main():
    print("アイテムデータ読み込み中...")
    with open(ITEMS_JSON, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"全 {len(items)} アイテムのカテゴリとステータスタグを精査・拡張中...")
    for iid, it in tqdm(items.items(), desc="アイテム拡張"):
        cats = it.get("categories", [])
        if not isinstance(cats, list):
            cats = [cats] if cats else []

        # スタートアップ判定
        if iid in STARTUP_IDS or "初期" in it.get("plaintext", "") or "ドラン" in it.get("name", ""):
            if "STARTUP" not in cats:
                cats.append("STARTUP")

        it["categories"] = cats

        # ステータスタグ解析
        it["stat_tags"] = analyze_stat_tags(it)

    with open(ITEMS_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] アイテムデータを拡張しました: {ITEMS_JSON}")

if __name__ == "__main__":
    main()
