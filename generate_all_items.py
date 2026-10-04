"""
generate_all_items.py - Data Dragonから全サモナーズリフト用アイテムを抽出し、
完全な基礎ステータス、効果テキスト、複数カテゴリ分類を付与した merged_data/all_items.json を生成する。
"""

import json
import os
import re
import urllib.request
from tqdm import tqdm

def format_stat_line(line):
    line = re.sub(r'<[^>]+>', ' ', line).strip()
    line = re.sub(r'\s+', ' ', line)
    if not line:
        return ""
    # "攻撃力 75" -> "攻撃力 +75" or "+75 攻撃力"
    # match (Label) (Value)
    match = re.match(r'^([^0-9\+\-]+?)\s*([0-9\+\-]+(?:\.[0-9]+)?%?)$', line)
    if match:
        label = match.group(1).strip()
        val = match.group(2).strip()
        if not val.startswith('+') and not val.startswith('-'):
            val = f"+{val}"
        return f"{label} {val}"
    return line

def clean_description(raw_desc):
    if not raw_desc:
        return ""
    # Remove stats section
    desc = re.sub(r'<stats>.*?</stats>', '', raw_desc, flags=re.DOTALL | re.IGNORECASE)
    # Convert passive / active tags
    desc = re.sub(r'<passive>(.*?)</passive>', r'【自動効果: \1】\n', desc, flags=re.IGNORECASE)
    desc = re.sub(r'<active>(.*?)</active>', r'【発動効果: \1】\n', desc, flags=re.IGNORECASE)
    desc = re.sub(r'<br\s*/?>', '\n', desc, flags=re.IGNORECASE)
    desc = re.sub(r'</p>', '\n', desc, flags=re.IGNORECASE)
    desc = re.sub(r'<li>', '• ', desc, flags=re.IGNORECASE)
    desc = re.sub(r'<[^>]+>', '', desc)
    lines = [l.strip() for l in desc.split('\n') if l.strip()]
    return '\n'.join(lines)

def determine_categories(item_name, desc_text, stats_list, tags, stats):
    full_text = f"{item_name} {desc_text} {' '.join(stats_list)}".lower()
    clean_stats_str = " ".join(stats_list)
    categories = set()

    # 1. BOOTS
    if 'Boots' in tags or any(k in item_name for k in ['ブーツ', '靴', 'スチールキャップ', 'アイオニア']):
        categories.add('BOOTS')

    # 2. CONSUMABLE
    if any(t in tags for t in ['Consumable', 'Trinket', 'Vision']) or any(k in item_name for k in ['ポーション', 'ワード', 'エリクサー', '詰め替え', 'ビスケット', 'トリンケット']):
        categories.add('CONSUMABLE')

    # 3. AD (物理・通常攻撃系)
    has_ad_stat = (
        stats.get('FlatPhysicalDamageMod', 0) > 0 or
        any(k in clean_stats_str for k in ['攻撃力', '脅威', '物理防御貫通', 'クリティカル', '攻撃速度', 'ライフスティール'])
    )
    has_ad_tag = any(t in tags for t in ['Damage', 'AttackSpeed', 'CriticalStrike', 'LifeSteal', 'ArmorPenetration', 'OnHit'])
    if has_ad_stat or has_ad_tag:
        categories.add('AD')

    # 4. AP (魔力・魔法系)
    has_ap_stat = (
        stats.get('FlatMagicDamageMod', 0) > 0 or
        any(k in clean_stats_str for k in ['魔力', '魔法防御貫通'])
    )
    has_ap_tag = any(t in tags for t in ['SpellDamage', 'MagicPenetration', 'SpellVamp'])
    if has_ap_stat or has_ap_tag:
        categories.add('AP')

    # 5. TANK (防具・耐久系)
    has_tank_stat = (
        stats.get('FlatArmorMod', 0) > 0 or
        stats.get('FlatSpellBlockMod', 0) > 0 or
        stats.get('FlatHPPoolMod', 0) > 0 or
        any(k in clean_stats_str for k in ['物理防御', '魔法防御', '体力', '行動妨害耐性', '基本体力自動回復'])
    )
    has_tank_tag = any(t in tags for t in ['Armor', 'SpellBlock', 'Health', 'HealthRegen', 'Tenacity'])
    if has_tank_stat or has_tank_tag:
        categories.add('TANK')

    # 6. SUPPORT
    has_sup_tag = any(t in tags for t in ['Support', 'GoldPer'])
    has_sup_item = any(k in item_name for k in [
        'ワールドアトラス', 'ルーンコンパス', '天の異形', 'ソラリ', '騎士の誓い', 
        'ミカエル', 'ドリームメーカー', 'ザックザック', 'ソングレス', '血の熱狂',
        '帝国の指令', 'シュレリア', '流水の杖', 'アーデント', 'ドーンコア', 'レディアント'
    ])
    has_sup_stat = any(k in clean_stats_str for k in ['回復およびシールド', '基本マナ自動回復'])
    if has_sup_tag or has_sup_item or has_sup_stat:
        categories.add('SUPPORT')

    if not categories:
        categories.add('OTHER')

    return sorted(list(categories))

def main():
    print("最新Data Dragonバージョンを取得中...")
    with urllib.request.urlopen("https://ddragon.leagueoflegends.com/api/versions.json") as res:
        versions = json.loads(res.read().decode("utf-8"))
        latest_version = versions[0]
    print(f"最新バージョン: {latest_version}")

    item_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/item.json"
    print(f"Data Dragon item.json ダウンロード中: {item_url}")
    req = urllib.request.Request(item_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as res:
        raw_data = json.loads(res.read().decode("utf-8"))["data"]

    # チャンピオンデータから使われているアイテムIDも確認
    champs_path = "merged_data/all_champions.json"
    used_item_ids = set()
    if os.path.exists(champs_path):
        with open(champs_path, "r", encoding="utf-8") as f:
            champs = json.load(f)
            for c in champs.values():
                b = c.get("build", {})
                for k in ["starter", "boots", "core", "situational"]:
                    for it in b.get(k, []):
                        if it.get("item_id"):
                            used_item_ids.add(str(it["item_id"]))
                for rdata in c.get("role_data", {}).values():
                    for bp in rdata.get("build_patterns", []):
                        for it in bp.get("items", []):
                            if it.get("id"):
                                used_item_ids.add(str(it["id"]))

    processed_items = {}
    print("アイテムデータ解析およびステータス・カテゴリ生成中...")
    for iid, raw_item in tqdm(raw_data.items(), desc="アイテム処理中"):
        maps = raw_item.get("maps", {})
        is_sr = maps.get("11", False)
        gold = raw_item.get("gold", {})
        purchasable = gold.get("purchasable", True)
        total_gold = gold.get("total", 0)
        req_champ = raw_item.get("requiredChampion", None)

        # サモナーズリフト用、またはチャンピオン推奨ビルドで参照されているアイテム
        if not is_sr and str(iid) not in used_item_ids:
            continue
        if req_champ and str(iid) not in used_item_ids:
            continue
        if not purchasable and total_gold <= 0 and str(iid) not in used_item_ids:
            continue

        raw_desc = raw_item.get("description", "")
        tags = raw_item.get("tags", [])
        stats = raw_item.get("stats", {})
        item_name = raw_item.get("name", "")

        # <stats> タグからステータスリスト抽出
        stats_match = re.search(r'<stats>(.*?)</stats>', raw_desc, re.DOTALL | re.IGNORECASE)
        stats_list = []
        if stats_match:
            parts = stats_match.group(1).split('<br>')
            for p in parts:
                formatted = format_stat_line(p)
                if formatted:
                    stats_list.append(formatted)

        # もし <stats> に情報がなく stats 辞書がある場合 (フォールバック)
        if not stats_list and stats:
            for k, v in stats.items():
                lbl = k
                val = f"+{v}" if v > 0 else str(v)
                if k == "FlatPhysicalDamageMod": lbl = "攻撃力"
                elif k == "FlatMagicDamageMod": lbl = "魔力"
                elif k == "FlatHPPoolMod": lbl = "体力"
                elif k == "FlatArmorMod": lbl = "物理防御"
                elif k == "FlatSpellBlockMod": lbl = "魔法防御"
                elif k == "FlatMovementSpeedMod": lbl = "移動速度"
                elif k == "PercentAttackSpeedMod": lbl = "攻撃速度"; val = f"+{round(v*100)}%"
                elif k == "FlatCritChanceMod": lbl = "クリティカル率"; val = f"+{round(v*100)}%"
                stats_list.append(f"{lbl} {val}")

        stats_summary = " | ".join(stats_list[:3]) if stats_list else (raw_item.get("plaintext") or "")
        clean_desc = clean_description(raw_desc)
        categories = determine_categories(item_name, clean_desc, stats_list, tags, stats)

        processed_items[iid] = {
            "id": str(iid),
            "name": item_name,
            "colloq": raw_item.get("colloq", ""),
            "plaintext": raw_item.get("plaintext", ""),
            "image": raw_item.get("image", {}).get("full", f"{iid}.png"),
            "category": categories[0] if categories else "OTHER",
            "categories": categories,
            "gold": gold,
            "tags": tags,
            "stats": stats,
            "stats_list": stats_list,
            "stats_summary": stats_summary,
            "description": clean_desc,
            "from": raw_item.get("from", []),
            "into": raw_item.get("into", [])
        }

    out_file = "merged_data/all_items.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(processed_items, f, ensure_ascii=False, indent=2)

    print(f"合計 {len(processed_items)} 個のアイテムを {out_file} に保存しました。")

if __name__ == "__main__":
    main()
