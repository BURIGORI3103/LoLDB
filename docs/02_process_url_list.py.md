---
tags:
  - LoLDB
---
URLリストからOP.GGと日本語wikiを順次解析し、サモナースペル、レーン、ビルド、ルーン、対面相性を strategy_data フォルダへ保存します。進捗チェックボックスも自動更新します。

import json
import os
import re
import time
import urllib.request
import urllib.parse

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

def fetch_json(url):
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def build_dictionaries():
    print("公式Data Dragonから日本語辞書データを取得中...")
    versions_url = "https://ddragon.leagueoflegends.com/api/versions.json"
    latest_version = fetch_json(versions_url)[0]

    # アイテム辞書
    items_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/item.json"
    items_data = fetch_json(items_url)["data"]
    item_dict = {int(k): v["name"] for k, v in items_data.items()}

    # ルーン辞書
    runes_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/runesReforged.json"
    runes_data = fetch_json(runes_url)
    rune_dict = {}
    path_dict = {}
    for tree in runes_data:
        path_dict[tree["id"]] = tree["name"]
        for slot in tree["slots"]:
            for rune in slot["runes"]:
                rune_dict[rune["id"]] = rune["name"]

    # チャンピオン辞書
    champs_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/champion.json"
    champs_data = fetch_json(champs_url)["data"]
    champ_dict = {v["key"]: {"id": k, "name": v["name"]} for k, v in champs_data.items()}

    # サモナースペル辞書
    spells_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/summoner.json"
    spells_data = fetch_json(spells_url)["data"]
    spell_dict = {v["key"]: v["name"] for k, v in spells_data.items()}

    return latest_version, item_dict, rune_dict, path_dict, champ_dict, spell_dict

def extract_next_data(html_content):
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content)
    if match:
        return json.loads(match.group(1))
    return None

def normalize_position(pos_str):
    pos_map = {
        "TOP": "TOP",
        "JUNGLE": "JUG",
        "MID": "MID",
        "MIDDLE": "MID",
        "ADC": "ADC",
        "BOTTOM": "ADC",
        "SUPPORT": "SUP"
    }
    return pos_map.get(pos_str.upper(), pos_str.upper())

def extract_wiki_notes(wiki_url):
    if not wiki_url:
        return {"laning": "", "teamfight": ""}
    try:
        req = urllib.request.Request(wiki_url, headers=get_headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        match = re.search(r'立ち回り.*?(?=おすすめ|長所|短所|$)', text)
        summary = match.group(0)[:150].strip() if match else ""
        return {
            "laning": summary,
            "teamfight": ""
        }
    except Exception:
        return {"laning": "", "teamfight": ""}

def run():
    # docsフォルダ内を優先して探索し、なければカレントディレクトリを参照する
    if os.path.exists(os.path.join("docs", "LoL_URL_list.md")):
        md_path = os.path.join("docs", "LoL_URL_list.md")
    elif os.path.exists("LoL_URL_list.md"):
        md_path = "LoL_URL_list.md"
    else:
        print("エラー: LoL_URL_list.md が docs/ 内にもカレントディレクトリにも見つかりません。")
        return

    latest_version, item_dict, rune_dict, path_dict, champ_dict, spell_dict = build_dictionaries()
    output_dir = "strategy_data"
    os.makedirs(output_dir, exist_ok=True)

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    current_entry = None

    for idx, line in enumerate(lines):
        match_header = re.match(r'^- \[( |x)\] (.*?) \((.*?)\)', line)
        if match_header:
            if current_entry:
                entries.append(current_entry)
            current_entry = {
                "line_idx": idx,
                "checked": match_header.group(1) == "x",
                "name": match_header.group(2).strip(),
                "slug": match_header.group(3).strip(),
                "opgg_url": "",
                "wiki_url": ""
            }
        elif current_entry:
            if "OP.GG:" in line:
                current_entry["opgg_url"] = line.split("OP.GG:", 1)[1].strip()
            elif "wiki:" in line:
                current_entry["wiki_url"] = line.split("wiki:", 1)[1].strip()

    if current_entry:
        entries.append(current_entry)

    total = len(entries)
    print(f"全 {total} 件の対象を検出しました。")

    for i, entry in enumerate(entries, 1):
        if entry["checked"]:
            continue

        champ_name = entry["name"]
        champ_slug = entry["slug"]
        print(f"[{i}/{total}] {champ_name} ({champ_slug}) を取得中...")

        file_path = os.path.join(output_dir, f"{champ_slug}.json")
        strategy_json = {
            "name": champ_name,
            "slug": champ_slug,
            "roles": [],
            "summoner_spells": [],
            "matchups": {"favorable": [], "unfavorable": []},
            "build": {"starter": [], "boots": [], "core": [], "situational": []},
            "runes": {
                "primary": {"path": "", "keystone": "", "keystone_name": "", "choices": []},
                "secondary": {"path": "", "choices": []},
                "shards": []
            },
            "gameplay_notes": {"laning": "", "teamfight": ""}
        }

        if entry["opgg_url"]:
            try:
                req = urllib.request.Request(entry["opgg_url"], headers=get_headers())
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8")
                next_data = extract_next_data(html)
                if next_data:
                    page_props = next_data.get("props", {}).get("pageProps", {})
                    page_data = page_props.get("data", {})

                    # レーン抽出
                    detected_roles = []
                    summary_positions = page_data.get("summary", {}).get("positions", [])
                    if summary_positions:
                        for p in summary_positions:
                            p_name = p.get("name")
                            if p_name:
                                norm = normalize_position(p_name)
                                if norm not in detected_roles:
                                    detected_roles.append(norm)

                    if not detected_roles:
                        single_pos = page_data.get("position") or page_props.get("position")
                        if single_pos:
                            detected_roles.append(normalize_position(single_pos))

                    strategy_json["roles"] = detected_roles

                    # サモナースペル抽出
                    summoner_data = page_data.get("summoner_spells", []) or page_data.get("spells", [])
                    if summoner_data:
                        top_spells = summoner_data[0].get("ids", [])
                        for s_id in top_spells:
                            s_name = spell_dict.get(str(s_id), f"スペル_{s_id}")
                            strategy_json["summoner_spells"].append(s_name)

                    # アイテム抽出
                    core_items = page_data.get("core_items", [])
                    if core_items:
                        for step_idx, item_id in enumerate(core_items[0].get("ids", []), 1):
                            strategy_json["build"]["core"].append({
                                "step": step_idx,
                                "item_id": str(item_id),
                                "name": item_dict.get(item_id, f"アイテム_{item_id}"),
                                "description": "推奨コア"
                            })

                    boots = page_data.get("boots", [])
                    if boots:
                        for b in boots[:2]:
                            b_id = b.get("ids", [0])[0]
                            strategy_json["build"]["boots"].append({
                                "item_id": str(b_id),
                                "name": item_dict.get(b_id, f"靴_{b_id}"),
                                "condition": "推奨靴"
                            })

                    starters = page_data.get("starter_items", [])
                    if starters:
                        for s_id in starters[0].get("ids", []):
                            strategy_json["build"]["starter"].append({
                                "item_id": str(s_id),
                                "name": item_dict.get(s_id, f"アイテム_{s_id}")
                            })

                    # ルーン抽出
                    runes = page_data.get("runes", [])
                    if runes:
                        top_rune = runes[0]
                        p_id = top_rune.get("primary_page_id")
                        s_id = top_rune.get("secondary_page_id")
                        p_runes = top_rune.get("primary_rune_ids", [])
                        s_runes = top_rune.get("secondary_rune_ids", [])

                        strategy_json["runes"]["primary"]["path"] = path_dict.get(p_id, "")
                        if p_runes:
                            k_id = p_runes[0]
                            strategy_json["runes"]["primary"]["keystone"] = str(k_id)
                            strategy_json["runes"]["primary"]["keystone_name"] = rune_dict.get(k_id, "")
                            strategy_json["runes"]["primary"]["choices"] = [rune_dict.get(r, "") for r in p_runes[1:]]

                        strategy_json["runes"]["secondary"]["path"] = path_dict.get(s_id, "")
                        strategy_json["runes"]["secondary"]["choices"] = [rune_dict.get(r, "") for r in s_runes]

                    # カウンター（相性）抽出
                    counters = page_data.get("counters", [])
                    if counters:
                        sorted_counters = sorted(counters, key=lambda x: x.get("win", 0))
                        for opp in sorted_counters[:3]:
                            opp_key = str(opp.get("champion_id", ""))
                            opp_info = champ_dict.get(opp_key, {"name": "不明"})
                            winrate = round(opp.get("win", 0) * 100, 1)
                            strategy_json["matchups"]["unfavorable"].append({
                                "champion_id": opp_key,
                                "name": opp_info["name"],
                                "reason": f"勝率 {winrate}%（不利）"
                            })
                        for opp in reversed(sorted_counters[-3:]):
                            opp_key = str(opp.get("champion_id", ""))
                            opp_info = champ_dict.get(opp_key, {"name": "不明"})
                            winrate = round(opp.get("win", 0) * 100, 1)
                            strategy_json["matchups"]["favorable"].append({
                                "champion_id": opp_key,
                                "name": opp_info["name"],
                                "reason": f"勝率 {winrate}%（有利）"
                            })
            except Exception as e:
                print(f"  OP.GG取得失敗: {e}")

        # 日本語wiki立ち回り抽出
        if entry["wiki_url"]:
            strategy_json["gameplay_notes"] = extract_wiki_notes(entry["wiki_url"])

        # 保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(strategy_json, f, ensure_ascii=False, indent=2)

        # チェックボックス更新
        target_line = lines[entry["line_idx"]]
        lines[entry["line_idx"]] = re.sub(r'^- \[ \]', '- [x]', target_line)
        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        time.sleep(1.5)

    print("すべての処理が完了しました。")

if __name__ == "__main__":
    run()
