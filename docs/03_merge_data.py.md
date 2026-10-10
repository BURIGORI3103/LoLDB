---
tags:
  - LoLDB
---
champions_data と strategy_data を結合し、rolesの上書きとサモナースペル情報の統合を行ってマスターデータ（all_champions.json）を出力します。

import json
import os

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge_champion_data():
    base_dir = "champions_data"
    strategy_dir = "strategy_data"
    output_dir = "merged_data"
    combined_file = os.path.join(output_dir, "all_champions.json")

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

    for filename in sorted(base_files):
        champ_id = os.path.splitext(filename)[0]
        base_path = os.path.join(base_dir, filename)
        strategy_path = os.path.join(strategy_dir, f"{champ_id.lower()}.json")

        base_data = load_json(base_path)
        if not base_data:
            continue

        strategy_data = load_json(strategy_path)
        merged = dict(base_data)

        if strategy_data:
            if strategy_data.get("roles"):
                merged["roles"] = strategy_data.get("roles")
            merged["summoner_spells"] = strategy_data.get("summoner_spells", [])
            merged["matchups"] = strategy_data.get("matchups", default_strategy["matchups"])
            merged["build"] = strategy_data.get("build", default_strategy["build"])
            merged["runes"] = strategy_data.get("runes", default_strategy["runes"])
            merged["gameplay_notes"] = strategy_data.get("gameplay_notes", default_strategy["gameplay_notes"])
            strategy_applied_count += 1
        else:
            merged["roles"] = default_strategy["roles"]
            merged["summoner_spells"] = default_strategy["summoner_spells"]
            merged["matchups"] = default_strategy["matchups"]
            merged["build"] = default_strategy["build"]
            merged["runes"] = default_strategy["runes"]
            merged["gameplay_notes"] = default_strategy["gameplay_notes"]

        output_path = os.path.join(output_dir, filename)
        save_json(merged, output_path)

        all_champions_dict[champ_id] = merged
        merged_count += 1

    save_json(all_champions_dict, combined_file)

    print("結合処理が完了しました。")
    print(f"全チャンピオン数: {merged_count} 体")
    print(f"攻略データ適用数: {strategy_applied_count} 体")
    print(f"出力先フォルダ: {output_dir}")
    print(f"統合データファイル: {combined_file}")

if __name__ == "__main__":
    merge_champion_data()
