"""
process_url_list.py - URLリストからOP.GGと日本語wikiを解析し攻略データを保存 (v2.1 厳格検証対応版)
========================================================================================
docs/LoL_URL_list.md を参照し、未処理の対象に対してOP.GGの最新RSCストリームからビルド、ルーン、
レーン（roles: TOP, JUG, MID, ADC, SUP）、サモナースペル、対面勝率を抽出し、
日本語wikiから立ち回り概要を抽出し、strategy_dataフォルダへ保存します。
HTTP 200 だけでなく、必須項目・件数・対象チャンピオン識別子の妥当性検査 (validate_parsed_opgg_data) を
通過した場合のみ成功扱いとし、失敗時は再取得可能な状態（未チェック）を維持します。
"""

import json
import argparse
import os
import re
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tqdm import tqdm

JST = timezone(timedelta(hours=9))


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }


def fetch_json(url):
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=15) as resp:
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

    # チャンピオン辞書 (key -> id/name と id.lower() -> id/name の両方)
    champs_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/champion.json"
    champs_data = fetch_json(champs_url)["data"]
    champ_dict = {}
    for k, v in champs_data.items():
        champ_dict[v["key"]] = {"id": k, "name": v["name"]}
        champ_dict[k.lower()] = {"id": k, "name": v["name"]}

    # サモナースペル辞書
    spells_url = f"https://ddragon.leagueoflegends.com/cdn/{latest_version}/data/ja_JP/summoner.json"
    spells_data = fetch_json(spells_url)["data"]
    spell_dict = {v["key"]: v["name"] for k, v in spells_data.items()}

    return latest_version, item_dict, rune_dict, path_dict, champ_dict, spell_dict


SPELL_NAMES_MAP = {
    "SummonerFlash": "フラッシュ",
    "SummonerDot": "イグナイト",
    "SummonerTeleport": "テレポート",
    "SummonerSmite": "スマイト",
    "SummonerHeal": "ヒール",
    "SummonerBarrier": "バリア",
    "SummonerExhaust": "イグゾースト",
    "SummonerHaste": "ゴースト",
    "SummonerGhost": "ゴースト",
    "SummonerBoost": "クレンズ",
}


def parse_opgg_rsc(html, item_dict, rune_dict, path_dict, champ_dict, latest_version="16.20.1"):
    """OP.GGの最新Next.js App Router (RSC) ストリームから完全な攻略データをパースする"""
    matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:\\.|[^"\\])*)"\]\)', html, re.DOTALL)
    combined = ""
    for m in matches:
        try:
            unescaped = bytes(m, "utf-8").decode("unicode_escape")
        except Exception:
            unescaped = m.replace('\\"', '"').replace("\\\\", "\\")
        combined += unescaped

    fetched_date = datetime.now(JST).strftime("%Y-%m-%d")
    result = {
        "patch": latest_version,
        "fetched_at": fetched_date,
        "roles": [],
        "summoner_spells": [],
        "matchups": {"favorable": [], "unfavorable": []},
        "build": {"starter": [], "boots": [], "core": [], "situational": []},
        "runes": {
            "primary": {"path": "", "keystone": "", "keystone_name": "", "choices": []},
            "secondary": {"path": "", "choices": []},
            "shards": [],
        },
    }

    # 1. roles (positions)
    pos_match = re.search(r'"positions"\s*:\s*\[(.*?)\]', combined)
    if pos_match:
        pos_names = re.findall(r'"name":"([A-Za-z]+)"', pos_match.group(1))
        norm_map = {
            "TOP": "TOP",
            "JUNGLE": "JUG",
            "MID": "MID",
            "MIDDLE": "MID",
            "ADC": "ADC",
            "BOTTOM": "ADC",
            "SUPPORT": "SUP",
        }
        result["roles"] = list(dict.fromkeys([norm_map.get(p.upper(), p.upper()) for p in pos_names]))

    primary_role = result["roles"][0] if result["roles"] else "UNKNOWN"

    # 2. サモナースペル
    spells_found = re.findall(r"spell/(Summoner[A-Za-z0-9_]+)\.png", combined)
    if spells_found:
        unique_spells = list(dict.fromkeys(spells_found))[:2]
        result["summoner_spells"] = [SPELL_NAMES_MAP.get(s, s) for s in unique_spells]

    # 3. ルーン (rune_pages)
    rp_pos = combined.find('{"data":{"rune_pages"')
    if rp_pos != -1:
        depth = 0
        end = -1
        for i in range(rp_pos, len(combined)):
            c = combined[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            try:
                clean_json = re.sub(r":\s*\$undefined\b", ": null", combined[rp_pos:end])
                rp_data = json.loads(clean_json).get("data", {})
                pages = rp_data.get("rune_pages", [])
                if pages and pages[0].get("builds"):
                    top_build = pages[0]["builds"][0]
                    pri_style = top_build.get("primary_perk_style", {})
                    sec_style = top_build.get("secondary_perk_style", {})
                    result["runes"]["primary"]["path"] = path_dict.get(pri_style.get("id"), pri_style.get("name", ""))
                    result["runes"]["secondary"]["path"] = path_dict.get(sec_style.get("id"), sec_style.get("name", ""))

                    main_runes = top_build.get("main_runes", [])
                    choices = []
                    for idx, row in enumerate(main_runes):
                        active_rune = next((r for r in row if r.get("isActive")), None)
                        if active_rune:
                            r_id = active_rune.get("id")
                            r_name = rune_dict.get(r_id, active_rune.get("name", ""))
                            if idx == 0:
                                result["runes"]["primary"]["keystone"] = str(r_id)
                                result["runes"]["primary"]["keystone_name"] = r_name
                            else:
                                choices.append(r_name)
                    result["runes"]["primary"]["choices"] = choices

                    sub_runes = top_build.get("sub_runes", [])
                    sec_choices = []
                    for row in sub_runes:
                        active_rune = next((r for r in row if r.get("isActive")), None)
                        if active_rune:
                            r_id = active_rune.get("id")
                            sec_choices.append(rune_dict.get(r_id, active_rune.get("name", "")))
                    result["runes"]["secondary"]["choices"] = sec_choices

                    shards = top_build.get("shards", [])
                    shard_list = []
                    for row in shards:
                        active_shard = next((s for s in row if s.get("isActive")), None)
                        if active_shard:
                            shard_list.append(active_shard.get("name", str(active_shard.get("id", ""))))
                    result["runes"]["shards"] = shard_list
            except Exception:
                pass

    # 4. アイテム (starter, boots, core)
    s_block = re.search(r'"starter_items_0".*?(?=boots_|"core_items_|$)', combined)
    if s_block:
        starter_ids = re.findall(r'"metaId":(\d+)', s_block.group(0))
        for s_id in list(dict.fromkeys(starter_ids))[:2]:
            int_id = int(s_id)
            result["build"]["starter"].append({"item_id": s_id, "name": item_dict.get(int_id, f"アイテム_{s_id}")})

    b_matches = re.findall(r'"boots_\d+".*?"metaId":(\d+)', combined)
    for b_id in list(dict.fromkeys(b_matches))[:2]:
        int_id = int(b_id)
        result["build"]["boots"].append(
            {"item_id": b_id, "name": item_dict.get(int_id, f"靴_{b_id}"), "condition": "推奨靴"}
        )

    core_block = re.search(r'"core_items_0".*?(?=core_items_1|boots_|$)', combined)
    if core_block:
        core_ids = re.findall(r'"metaId":(\d+)', core_block.group(0))
        for step, c_id in enumerate(list(dict.fromkeys(core_ids))[:3], 1):
            int_id = int(c_id)
            result["build"]["core"].append(
                {
                    "step": step,
                    "item_id": c_id,
                    "name": item_dict.get(int_id, f"アイテム_{c_id}"),
                    "description": "推奨コア",
                }
            )

    # 5. カウンター (counters) - レーン・パッチ・取得日・参照元メタデータを付与
    counters = re.findall(r'"target_champion":"([a-z0-9]+)".*?"children":"(\d+\.\d+)%"', combined)
    unfav = []
    fav = []
    seen_opps = set()
    for champ_slug, wr_str in counters:
        if champ_slug in seen_opps:
            continue
        seen_opps.add(champ_slug)
        wr = float(wr_str)
        c_info = champ_dict.get(champ_slug, {"name": champ_slug.capitalize(), "id": champ_slug.capitalize()})
        entry = {
            "champion_id": c_info["id"],
            "name": c_info["name"],
            "winrate": f"{wr}%",
            "winrate_num": wr,
            "winrate_display": f"勝率 {wr}%",
            "role": primary_role,
            "patch": latest_version,
            "source": "opgg_stats",
            "region": "Global",
            "tier": "Emerald+",
            "fetched_at": fetched_date,
            "is_estimated": False,
            "reason": f"勝率 {wr}%",
        }
        if wr < 50.0:
            entry["reason"] += "（統計的に不利）"
            unfav.append(entry)
        else:
            entry["reason"] += "（統計的に有利）"
            fav.append(entry)

    result["matchups"]["unfavorable"] = unfav[:3]
    result["matchups"]["favorable"] = fav[:3]

    return result


def validate_parsed_opgg_data(parsed: dict, html: str, expected_slug: str) -> tuple[bool, str]:
    """
    HTTP 200 のみで成功と誤認しないよう、解析結果の必須項目・件数・対象チャンピオンを検証する。
    """
    if not html or len(html) < 500:
        return False, "HTMLレスポンスが空または極端に短いためブロック画面の可能性があります"

    # 対象チャンピオンのslugがHTMLまたはURL構造に含まれているか確認
    slug_norm = expected_slug.lower().replace("_", "").replace("-", "").replace("'", "")
    if slug_norm not in html.lower():
        return False, f"対象チャンピオン識別子 ({expected_slug}) がページ内に見つかりません"

    roles = parsed.get("roles", [])
    if not roles:
        return False, "担当ロール (positions) が1件も抽出できませんでした"

    core_items = parsed.get("build", {}).get("core", [])
    if len(core_items) == 0:
        return False, "推奨コアアイテム (core_items) が1件も抽出できませんでした"

    keystone = parsed.get("runes", {}).get("primary", {}).get("keystone", "")
    if not keystone:
        return False, "メインキーストーンルーンが抽出できませんでした"

    fav = parsed.get("matchups", {}).get("favorable", [])
    unfav = parsed.get("matchups", {}).get("unfavorable", [])
    if len(fav) + len(unfav) == 0:
        return False, "対面カウンター統計 (matchups) が1件も抽出できませんでした"

    return True, "OK"


def extract_wiki_notes_safe(wiki_url):
    """現行wikiの考察を取得する。取得失敗は空欄とし、汎用文を取得結果にしない。"""
    from refresh_wiki import fetch_wiki
    try:
        info = fetch_wiki(wiki_url)
        return {"laning": next(iter(info["sections"].values())), "teamfight": "", "wiki_info": info}
    except Exception as error:
        return {"laning": "", "teamfight": "", "wiki_info": {"status": "failed", "source_url": wiki_url, "error": str(error)}}


def generate_fallback_notes(name, roles):
    role_str = roles[0] if roles else "レーン"
    laning = f"序盤は相手のスキル使用後に有利なトレードを狙う。{role_str}でのCS管理とマップ警戒を徹底する。"
    teamfight = "集団戦では自身の役割（キャリー攻撃や味方の保護）を意識し、有利な位置取りからスキルを叩き込む。"
    return {"laning": laning, "teamfight": teamfight}


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="チェック済みも再取得")
    parser.add_argument("--reuse-wiki", action="store_true", help="取得済みのwiki情報を再利用")
    args = parser.parse_args()
    base_dir = Path(__file__).resolve().parent
    doc_paths = [
        base_dir / "docs" / "LoL_URL_list.md",
        Path("docs/LoL_URL_list.md"),
        Path("LoL_URL_list.md"),
        Path(r"c:\Project\LoLDB\docs\LoL_URL_list.md"),
    ]
    md_path = None
    for p in doc_paths:
        if p.exists():
            md_path = p
            break

    if not md_path:
        print("エラー: LoL_URL_list.md が見つかりません。")
        return

    print(f"URLリスト参照先: {md_path}")
    latest_version, item_dict, rune_dict, path_dict, champ_dict, spell_dict = build_dictionaries()
    output_dir = base_dir / "strategy_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entries = []
    current_entry = None

    for idx, line in enumerate(lines):
        match_header = re.match(r"^- \[( |x)\]\s*(.*?)\s*\((.*?)\)", line)
        if match_header:
            if current_entry:
                entries.append(current_entry)
            current_entry = {
                "line_idx": idx,
                "checked": match_header.group(1) == "x",
                "name": match_header.group(2).strip(),
                "slug": match_header.group(3).strip(),
                "opgg_url": "",
                "wiki_url": "",
            }
        elif current_entry:
            if "OP.GG:" in line:
                current_entry["opgg_url"] = line.split("OP.GG:", 1)[1].strip()
            elif "wiki:" in line:
                current_entry["wiki_url"] = line.split("wiki:", 1)[1].strip()

    if current_entry:
        entries.append(current_entry)

    total = len(entries)
    pending_entries = [e for e in entries if args.refresh or not e["checked"]]
    print(f"全 {total} 件中、未処理 {len(pending_entries)} 件を検出しました。")

    if not pending_entries:
        print("すべてのチャンピオンが処理済みです。")
        return

    success_count = 0
    fail_count = 0
    error_logs = []

    progress_bar = tqdm(pending_entries, desc="攻略データ収集中", unit="champ")
    for entry in progress_bar:
        champ_name = entry["name"]
        champ_slug = entry["slug"]
        progress_bar.set_postfix_str(f"{champ_name} ({champ_slug})")

        file_path = output_dir / f"{champ_slug}.json"
        strategy_json = {
            "name": champ_name,
            "slug": champ_slug,
            "patch": latest_version,
            "roles": [],
            "summoner_spells": [],
            "matchups": {"favorable": [], "unfavorable": []},
            "build": {"starter": [], "boots": [], "core": [], "situational": []},
            "runes": {
                "primary": {"path": "", "keystone": "", "keystone_name": "", "choices": []},
                "secondary": {"path": "", "choices": []},
                "shards": [],
            },
            "gameplay_notes": {"laning": "", "teamfight": ""},
        }

        opgg_success = False
        if entry["opgg_url"]:
            try:
                req = urllib.request.Request(entry["opgg_url"], headers=get_headers())
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8")

                parsed = parse_opgg_rsc(
                    html, item_dict, rune_dict, path_dict, champ_dict, latest_version=latest_version
                )
                is_valid, reason_msg = validate_parsed_opgg_data(parsed, html, champ_slug)
                short_patch = ".".join(latest_version.split(".")[:2])
                if not re.search(r'Patch\s+' + re.escape(short_patch) + r'\b', html, re.I):
                    is_valid, reason_msg = False, "ページの対象パッチを確認できません"
                if is_valid:
                    strategy_json.update(parsed)
                    strategy_json["opgg_source"] = {"url": entry["opgg_url"], "patch": short_patch, "patch_verified": True, "fetched_at": datetime.now(JST).isoformat(timespec="seconds")}
                    opgg_success = True
                else:
                    error_logs.append(f"{champ_name} ({champ_slug}) 検証失敗(再取得対象として維持): {reason_msg}")
            except Exception as e:
                err_msg = f"{champ_name} ({champ_slug}) OP.GG取得失敗: {e}"
                error_logs.append(err_msg)

        # 日本語wiki立ち回り抽出
        if args.reuse_wiki and file_path.exists() and (cached := json.loads(file_path.read_text(encoding="utf-8"))).get("wiki_info", {}).get("status") == "success":
            strategy_json["wiki_info"] = cached["wiki_info"]
            strategy_json["gameplay_notes"] = {"laning": next(iter(cached["wiki_info"]["sections"].values())), "teamfight": ""}
        elif entry["wiki_url"]:
            wiki_notes = extract_wiki_notes_safe(entry["wiki_url"])
            strategy_json["wiki_info"] = wiki_notes.pop("wiki_info")
            if wiki_notes.get("laning"):
                strategy_json["gameplay_notes"] = wiki_notes
            else:
                strategy_json["gameplay_notes"] = {"laning": "", "teamfight": ""}
        else:
            strategy_json["gameplay_notes"] = generate_fallback_notes(champ_name, strategy_json["roles"])

        # 検証通過時のみデータを上書き保存し、チェックボックスを [x] に進める
        if opgg_success:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(strategy_json, f, ensure_ascii=False, indent=2)
            success_count += 1
            target_line = lines[entry["line_idx"]]
            lines[entry["line_idx"]] = re.sub(r"^- \[ \]", "- [x]", target_line)
            with open(md_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        else:
            fail_count += 1
            lines[entry["line_idx"]] = re.sub(r"^- \[x\]", "- [ ]", lines[entry["line_idx"]])
            md_path.write_text("".join(lines), encoding="utf-8")

        time.sleep(0.15)

    print("すべての処理が完了しました。")
    print(f"成功(検証通過): {success_count} 件, 失敗/再取得対象: {fail_count} 件")
    if error_logs:
        print(f"エラーログ（計 {len(error_logs)} 件）:")
        for log in error_logs[:10]:
            print(f" - {log}")
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    run()
