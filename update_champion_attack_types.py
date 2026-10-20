"""
update_champion_attack_types.py
================================
全173体のチャンピオンデータ（merged_data/all_champions.json および個別JSON）に、
公式の stats.attackrange を参照して正確な attack_type（MELEE / RANGED / HYBRID）を付与する。
ハルシネーションや憶測を排除し、公式ステータスに基づき厳密に分類する。
"""

import json
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"
MERGED_DIR = BASE_DIR / "merged_data"

# 特殊なモード切替・進化持ち（フォームチェンジでAAレンジが変化する公式仕様）
HYBRID_SPECIAL_CHAMPIONS = {
    "Jayce": {
        "type": "HYBRID",
        "label": "近接/遠隔 (フォーム切替)",
        "badge": "両用",
        "base_range": 125,
        "alt_range": 500,
        "desc": "マーキュリーハンマー（近接 125）とマーキュリーキャノン（遠隔 500）を随時切り替えて戦闘可能。"
    },
    "Nidalee": {
        "type": "HYBRID",
        "label": "遠隔/近接 (フォーム切替)",
        "badge": "両用",
        "base_range": 525,
        "alt_range": 125,
        "desc": "人間形態（遠隔 525）とクーガー形態（近接 125）を随時切り替えて戦闘可能。"
    },
    "Elise": {
        "type": "HYBRID",
        "label": "遠隔/近接 (フォーム切替)",
        "badge": "両用",
        "base_range": 550,
        "alt_range": 125,
        "desc": "人間形態（遠隔 550）と蜘蛛形態（近接 125）を随時切り替えて戦闘可能。"
    },
    "Gnar": {
        "type": "HYBRID",
        "label": "遠隔/近接 (変身可変)",
        "badge": "両用",
        "base_range": 175,
        "alt_range": 175,
        "desc": "ミニナー形態（遠隔 175〜Lv比例400）とメガナー形態（近接 175）に変身。"
    },
    "Kayle": {
        "type": "HYBRID",
        "label": "近接 ➔ 遠隔 (Lv6~進化)",
        "badge": "可変",
        "base_range": 175,
        "alt_range": 525,
        "desc": "序盤（Lv1〜5）は近接（175）だが、Lv6以降は遠隔（525 / Lv16で625）に進化。"
    }
}

def determine_attack_type(cid, cdata):
    """
    stats.attackrange から AAタイプ を厳密に判定する。
    """
    stats = cdata.get("stats", {})
    attackrange = stats.get("attackrange", 175)

    if cid in HYBRID_SPECIAL_CHAMPIONS:
        info = dict(HYBRID_SPECIAL_CHAMPIONS[cid])
        info["range"] = attackrange
        return info

    if attackrange <= 250:
        return {
            "type": "MELEE",
            "label": f"近接 (メレー) [射程 {attackrange}]",
            "badge": "近接",
            "range": attackrange,
            "desc": f"通常攻撃射程 {attackrange} の近接攻撃チャンピオンです。"
        }
    else:
        return {
            "type": "RANGED",
            "label": f"遠隔 (レンジ) [射程 {attackrange}]",
            "badge": "遠隔",
            "range": attackrange,
            "desc": f"通常攻撃射程 {attackrange} の遠隔攻撃チャンピオンです。"
        }

def main():
    print("チャンピオンマスターデータ読み込み中...")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    melee_count = 0
    ranged_count = 0
    hybrid_count = 0

    print(f"全 {len(champions)} 体のチャンピオンにAAタイプ（メレー/レンジ）を付与中...")
    for cid, cdata in tqdm(champions.items(), desc="AAタイプ付与"):
        att_info = determine_attack_type(cid, cdata)
        cdata["attack_type"] = att_info

        # role_data 内の各ロールにも attack_type を同期
        for rname, rinfo in cdata.get("role_data", {}).items():
            rinfo["attack_type"] = att_info

        if att_info["type"] == "MELEE":
            melee_count += 1
        elif att_info["type"] == "RANGED":
            ranged_count += 1
        else:
            hybrid_count += 1

    # all_champions.json に書き出し
    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    # 個別JSONも同期更新
    for cid, cdata in tqdm(champions.items(), desc="個別JSON同期"):
        indiv_file = MERGED_DIR / f"{cid}.json"
        with open(indiv_file, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False, indent=2)

    print("\n[SUCCESS] AAタイプ付与が完了しました:")
    print(f"  - 近接 (MELEE): {melee_count} 体")
    print(f"  - 遠隔 (RANGED): {ranged_count} 体")
    print(f"  - 両用/可変 (HYBRID): {hybrid_count} 体")
    print(f"  - 合計: {len(champions)} 体")

if __name__ == "__main__":
    main()
