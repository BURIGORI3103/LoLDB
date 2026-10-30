"""
merge_data.py - champions_data と strategy_data を統合しマスターJSONを生成
========================================================================
champions_data（公式基礎値）と strategy_data（攻略統計値）をチャンピオンIDをキーにして突合し、
実運用レーン情報（roles）の上書きやサモナースペルの追加を行って、
merged_data/all_champions.json を出力します。
"""

import json
import copy
import os
from pathlib import Path
from tqdm import tqdm

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Data DragonのチャンピオンIDとOP.GGスラッグの表記揺れエイリアス辞書
CHAMPION_SLUG_ALIASES = {
    "monkeyking": "monkeyking",
    "renata": "renata",
    "nunu": "nunu",
}


def merge_record(base, strategy, previous):
    """手動補完を保ちつつ統計を現在パッチ・現在ロールの取得結果へ置換する。"""
    if not strategy or strategy.get("patch") != base["patch"] or not strategy.get("opgg_source", {}).get("patch_verified"):
        raise ValueError(f"最新パッチの検証済み攻略データがありません: {base['id']}")
    merged = copy.deepcopy(previous)
    merged.update(base)
    merged["classes"] = base.get("roles", [])
    for key in ("roles", "summoner_spells", "matchups", "build", "runes", "wiki_info", "opgg_source"):
        merged[key] = copy.deepcopy(strategy.get(key, {} if key not in ("roles", "summoner_spells") else []))
    for entries in merged["matchups"].values():
        for entry in entries:
            entry["reason"] = "理由データなし"
    old_roles = previous.get("role_data", {})
    roles = {}
    for role in merged["roles"]:
        measured = strategy.get("role_data", {}).get(role)
        if not measured or measured.get("opgg_source", {}).get("role") != role:
            raise ValueError(f"ロール別統計がありません: {base['id']} {role}")
        rd = copy.deepcopy(old_roles.get(role, {}))
        rd.update({key: copy.deepcopy(measured[key]) for key in ("build", "runes", "matchups", "opgg_source")})
        for entries in rd["matchups"].values():
            for entry in entries:
                entry["reason"] = "理由データなし"
        rd["role"] = role
        rd["spells"] = measured["summoner_spells"]
        rd["build_patterns"] = [{"name": "OP.GG 推奨ビルド", "desc": f"パッチ{base['patch']}・{role}の取得済み統計", "core": [item["name"] for item in measured["build"]["core"]], "core_items": measured["build"]["core"], "starter": [item["name"] for item in measured["build"]["starter"]], "boots": next((item["name"] for item in measured["build"]["boots"]), "取得データなし"), "situational": [], "source": "opgg_stats", "patch": base["patch"]}]
        rd["spell_sets"] = [{"name": "OP.GG 推奨", "spells": measured["summoner_spells"]}]
        roles[role] = rd
    merged["role_data"] = roles
    primary = merged["roles"][0]
    merged["build_patterns"] = copy.deepcopy(roles[primary]["build_patterns"])
    merged["gameplay_notes"] = copy.deepcopy(previous.get("gameplay_notes", {}))
    for key in ("matchup_matrix", "matchup_matrix_by_role"):
        merged.pop(key, None)
    return merged

def find_strategy_file(strategy_dir, champ_id):
    lower_id = champ_id.lower()
    candidate_slugs = [
        lower_id,
        CHAMPION_SLUG_ALIASES.get(lower_id, ""),
        lower_id.replace(" ", "").replace("'", "").replace(".", "")
    ]
    for slug in candidate_slugs:
        if not slug:
            continue
        p = os.path.join(strategy_dir, f"{slug}.json")
        if os.path.exists(p):
            return p
    return None

def merge_champion_data():
    base_dir = "champions_data"
    strategy_dir = "strategy_data"
    output_dir = "merged_data"
    combined_file = os.path.join(output_dir, "all_champions.json")
    previous = load_json(combined_file) or {}

    if not os.path.exists(base_dir):
        print(f"エラー: 基本データフォルダ（{base_dir}）が見つかりません。")
        return

    os.makedirs(strategy_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    default_strategy = {
        "roles": [],
        "summoner_spells": [],
        "matchups": {
            "favorable": [],
            "unfavorable": []
        },
        "build": {
            "starter": [],
            "boots": [],
            "core": [],
            "situational": []
        },
        "runes": {
            "primary": {
                "path": "",
                "keystone": "",
                "keystone_name": "",
                "choices": []
            },
            "secondary": {
                "path": "",
                "choices": []
            },
            "shards": []
        },
        "gameplay_notes": {
            "laning": "",
            "teamfight": ""
        }
    }

    base_files = [f for f in os.listdir(base_dir) if f.endswith(".json")]
    all_champions_dict = {}
    merged_count = 0
    strategy_applied_count = 0

    print("データの結合処理を開始します...")

    for filename in tqdm(sorted(base_files), desc="データ統合中", unit="champ"):
        champ_id = os.path.splitext(filename)[0]
        base_path = os.path.join(base_dir, filename)
        strategy_path = find_strategy_file(strategy_dir, champ_id)

        base_data = load_json(base_path)
        if not base_data:
            continue

        strategy_data = load_json(strategy_path) if strategy_path else None
        merged = merge_record(base_data, strategy_data, previous.get(champ_id, {}))
        # 公式の基本クラス情報（Fighter, Mage, Tank 等）を classes として保持
        merged["classes"] = list(base_data.get("roles", []))

        if strategy_data:
            if strategy_data.get("roles"):
                merged["roles"] = strategy_data.get("roles")
            merged["summoner_spells"] = strategy_data.get("summoner_spells", [])
            merged["build"] = strategy_data.get("build", default_strategy["build"])
            merged["runes"] = strategy_data.get("runes", default_strategy["runes"])
            # wiki抜粋はwiki_infoへ保持し、レーン戦・集団戦の専用メモと混同しない。
            strategy_applied_count += 1
        else:
            merged["roles"] = default_strategy["roles"]
            merged["summoner_spells"] = default_strategy["summoner_spells"]
            merged["matchups"] = default_strategy["matchups"]
            merged["build"] = default_strategy["build"]
            merged["runes"] = default_strategy["runes"]
            merged["gameplay_notes"] = default_strategy["gameplay_notes"]

        all_champions_dict[champ_id] = merged
        merged_count += 1

    # 全件の検証を通過するまで既存のマスター・個別JSONへ書き込まない。
    for cid, merged in tqdm(all_champions_dict.items(), desc="検証済みJSON保存"):
        save_json(merged, os.path.join(output_dir, f"{cid}.json"))
    save_json(all_champions_dict, combined_file)

    file_size_kb = os.path.getsize(combined_file) / 1024 if os.path.exists(combined_file) else 0

    print("結合処理が完了しました。")
    print(f"全チャンピオン数: {merged_count} 体")
    print(f"攻略データ適用数: {strategy_applied_count} 体")
    print(f"マスターファイル容量: {file_size_kb:.2f} KB")
    print(f"出力先フォルダ: {output_dir}")
    print(f"統合データファイル: {combined_file}")

if __name__ == "__main__":
    merge_champion_data()
