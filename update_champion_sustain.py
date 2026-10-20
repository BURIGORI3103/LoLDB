"""
update_champion_sustain.py
==========================
全173体のチャンピオンデータ（merged_data/all_champions.json および個別JSON）に、
公式スキル説明（abilities & spells）から厳密に解析した sustain_info を付与・保存する。
ハルシネーションや憶測を排除し、公式ステータス・説明文に基づき正確に分類する。
"""

import json
import re
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"
MERGED_DIR = BASE_DIR / "merged_data"

def analyze_champion_sustain(cid, cdata):
    """
    公式の abilities (Passive) および spells (Q, W, E, R) の説明文から
    体力回復（吸血・リジェネ）およびシールド能力を厳密に抽出する。
    """
    all_skills = []
    for ab in cdata.get("abilities", []):
        all_skills.append(("Passive", ab.get("name", ""), ab.get("description", "")))
    for sp in cdata.get("spells", []):
        all_skills.append((sp.get("id", ""), sp.get("name", ""), sp.get("description", "")))

    heals = []
    shields = []

    for slot, name, raw_desc in all_skills:
        # HTMLタグ除去
        desc = re.sub(r"<[^>]+>", "", raw_desc)

        # 1. 体力回復・吸血・リジェネ判定
        # 阻害・重傷（低下する、減少する）は除外
        is_debuff = bool(re.search(r"(回復量|回復効果|自動回復).{0,10}(低下|減少|半減)", desc))
        is_passive_receiver = bool(re.search(r"味方から.{0,20}(回復|シールド).{0,10}(受ける|付与される)", desc))

        is_heal = False
        if not is_debuff and not is_passive_receiver:
            # ライフスティール・オムニヴァンプ・吸血
            if re.search(r"ライフスティール|オムニヴァンプ|吸血", desc):
                is_heal = True
            # 体力回復 / 自身を回復 / 味方を回復 / ヘルス回復 / HP回復
            elif re.search(r"(体力|自身|味方|ヘルス|HP|受領|ダメージの一部).{0,25}回復", desc):
                is_heal = True
            elif re.search(r"回復.{0,10}(体力|ヘルス|HP)", desc):
                is_heal = True

        if is_heal:
            # マナ・気力・勇気だけの回復は厳格に除外
            has_explicit_hp = bool(re.search(r"体力|自身|味方|ヘルス|HP|ダメージの一部|ライフスティール|オムニヴァンプ|吸血", desc))
            has_only_mana_ki = bool(re.search(r"(マナ|気|勇気)を回復する", desc) and not re.search(r"(体力|自身|味方|ヘルス)を?回復", desc))
            if has_explicit_hp and not has_only_mana_ki:
                heals.append({"slot": slot, "name": name, "desc": desc})

        # 2. シールド判定
        shield_pattern = r"シールドを(獲得|得る|付与|張る|展開|生成|纏|身にまとう|付加)|シールドが(付与|生成|展開)|シールドを身に"
        if re.search(shield_pattern, desc):
            if not is_passive_receiver and not is_debuff:
                shields.append({"slot": slot, "name": name, "desc": desc})

    heal_names = [h["name"] for h in heals]
    shield_names = [s["name"] for s in shields]

    has_heal = len(heals) > 0
    has_shield = len(shields) > 0
    has_sustain = has_heal or has_shield

    s_type = "NONE"
    badge_text = ""
    summary = "固有のサステイン・シールドスキルは持ちません。"

    if has_heal and has_shield:
        s_type = "BOTH"
        badge_text = "回復＆シールド"
        summary = f"スキル（{', '.join(heal_names)}）による体力回復と、（{', '.join(shield_names)}）によるシールドを併せ持つ高い耐久・維持能力を持ちます。"
    elif has_heal:
        s_type = "HEAL"
        badge_text = "自己回復"
        summary = f"スキル（{', '.join(heal_names)}）による体力回復・吸血・リジェネによる優れたレーン維持・サステイン能力を持ちます。"
    elif has_shield:
        s_type = "SHIELD"
        badge_text = "シールド"
        summary = f"スキル（{', '.join(shield_names)}）によるシールド展開で敵の攻撃を緩和し、トレードで優位を保ちます。"

    return {
        "has_sustain": has_sustain,
        "has_heal": has_heal,
        "has_shield": has_shield,
        "type": s_type,
        "badge_text": badge_text,
        "heal_skills": heal_names,
        "shield_skills": shield_names,
        "summary": summary
    }

def main():
    print("チャンピオンマスターデータ読み込み中...")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    sustain_count = 0
    heal_count = 0
    shield_count = 0

    print(f"全 {len(champions)} 体のチャンピオンにサステイン情報（sustain_info）を付与中...")
    for cid, cdata in tqdm(champions.items(), desc="サステイン解析・付与"):
        sustain_info = analyze_champion_sustain(cid, cdata)
        cdata["sustain_info"] = sustain_info

        if sustain_info["has_sustain"]:
            sustain_count += 1
        if sustain_info["has_heal"]:
            heal_count += 1
        if sustain_info["has_shield"]:
            shield_count += 1

        # 個別JSONファイルも同期更新
        indiv_path = MERGED_DIR / f"{cid}.json"
        if indiv_path.exists():
            with open(indiv_path, "r", encoding="utf-8") as f:
                indiv_data = json.load(f)
            indiv_data["sustain_info"] = sustain_info
            with open(indiv_path, "w", encoding="utf-8") as f:
                json.dump(indiv_data, f, ensure_ascii=False, indent=2)

    # all_champions.json を保存
    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print("\n[SUCCESS] サステイン情報の付与・同期が完了しました！")
    print(f"  サステイン保持（回復またはシールド）: {sustain_count} 体")
    print(f"  体力回復・吸血保持: {heal_count} 体")
    print(f"  シールド保持: {shield_count} 体")

if __name__ == "__main__":
    main()
