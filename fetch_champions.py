"""
fetch_champions.py - 公式Data Dragonから全チャンピオンの基礎データを取得
========================================================================
Riot公式Data Dragonから全チャンピオンの基礎ステータス、パッシブ、QWERスキル、画像名を取得し、
champions_dataフォルダへ保存します。
"""

import json
import os
import urllib.request
from tqdm import tqdm

NETWORK_TIMEOUT_SECONDS = 15
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LoLDB/2.6"}


def fetch_lol_data():
    versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    print("🔧 ステップ 1/3: 最新バージョンを確認中... (33%)")
    ver_req = urllib.request.Request(versions_url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(ver_req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
        versions = json.loads(response.read().decode("utf-8"))
        latest_version = versions[0]
    print(f"最新バージョン: {latest_version}")

    data_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/championFull.json"
    print("🔧 ステップ 2/3: 全チャンピオンの詳細データをダウンロード中... (66%)")
    req = urllib.request.Request(data_url, headers=DEFAULT_HEADERS)
    with urllib.request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
        full_data = json.loads(response.read().decode("utf-8"))

    champions = full_data["data"]
    output_dir = "champions_data"
    os.makedirs(output_dir, exist_ok=True)

    print(f"🔧 ステップ 3/3: 個別JSONファイルを {output_dir} フォルダに保存中... (100%)")
    for champ_id, champ_info in tqdm(champions.items(), desc="チャンピオン基礎データ保存中"):
        formatted_data = {
            "id": champ_info["id"],
            "key": champ_info["key"],
            "name": champ_info["name"],
            "title": champ_info["title"],
            "patch": latest_version,
            "roles": champ_info["tags"],
            "resource": champ_info["partype"],
            "stats": champ_info["stats"],
            "abilities": [
                {
                    "slot": "Passive",
                    "name": champ_info["passive"]["name"],
                    "description": champ_info["passive"]["description"],
                    "image": champ_info["passive"]["image"]["full"],
                }
            ],
            "spells": [],
        }

        slots = ["Q", "W", "E", "R"]
        for idx, spell in enumerate(champ_info["spells"]):
            slot_name = slots[idx] if idx < len(slots) else f"Skill_{idx+1}"
            formatted_data["spells"].append(
                {
                    "slot": slot_name,
                    "name": spell["name"],
                    "description": spell["description"],
                    "cooldown": spell["cooldownBurn"],
                    "cost": spell["costBurn"],
                    "image": spell["image"]["full"],
                }
            )

        file_path = os.path.join(output_dir, f"{champ_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)

    print(f"完了しました。合計 {len(champions)} 体の基礎データを保存しました。")


if __name__ == "__main__":
    fetch_lol_data()
