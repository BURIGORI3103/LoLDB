"""既存パッチのOP.GG対面一覧を検証し、有利・不利を各最大7体保存する。"""
import concurrent.futures
import argparse
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

from merge_data import find_strategy_file
from process_url_list import get_headers, JST
from refresh_role_stats import ROLE_PATH, ROLE_TITLE

BASE = Path(__file__).resolve().parent
LIMIT = 7


def parse_counter_page(html, champion_id, role, patch, champions, url):
    """対象名・ロール・パッチと、対面行の画像ID・勝率・試合数を検証する。"""
    soup = BeautifulSoup(html, "html.parser")
    short_patch = ".".join(patch.split(".")[:2])
    heading = soup.find("h1")
    if not heading or not re.search(
        r"Counters for\s+" + ROLE_TITLE[role] + r",\s*Patch\s+" + re.escape(short_patch) + r"\b",
        heading.get_text(" ", strip=True), re.I
    ):
        raise ValueError("対面ページのロールまたはパッチが一致しません")
    if not heading.find("img", src=re.compile(r"/champion/" + re.escape(champion_id) + r"\.png")):
        # 見出しの画像が外にあるページではタイトルの英語名と照合する。
        name = champions[champion_id]["name_en"]
        if not heading.get_text(" ", strip=True).startswith(name + " Counters for"):
            raise ValueError("対面ページの対象チャンピオンが一致しません")
    rows = {}
    for row in soup.select("li"):
        img = row.find("img", src=re.compile(r"/champion/[^/]+\.png"))
        rate = row.find("strong", string=re.compile(r"^\d+(?:\.\d+)?%$"))
        if not img or not rate:
            continue
        cid = re.search(r"/champion/([^/]+)\.png", img["src"]).group(1)
        if cid not in champions or cid == champion_id:
            raise ValueError("対面一覧に不明なチャンピオンがあります")
        games_text = row.find_all("div", recursive=False)[-1].get_text(strip=True)
        if not re.fullmatch(r"[\d,]+", games_text):
            raise ValueError("対面一覧の試合数を抽出できません")
        games = int(games_text.replace(",", ""))
        wr = float(rate.get_text().rstrip("%"))
        if not 0 <= wr <= 100 or games <= 0 or cid in rows:
            raise ValueError("対面一覧の勝率・試合数・重複が不正です")
        rows[cid] = {
            "champion_id": cid, "name": champions[cid]["name"],
            "winrate": f"{wr}%", "winrate_num": wr, "winrate_display": f"勝率 {wr}%",
            "role": role, "patch": patch, "source": "opgg_stats", "source_url": url,
            "region": "Global", "tier": "Emerald+", "games": games,
            "fetched_at": datetime.now(JST).isoformat(timespec="seconds"),
            "is_estimated": False, "reason": "",
        }
    if not rows:
        if "Sample size is not large enough." in soup.get_text(" ", strip=True):
            return {"favorable": [], "unfavorable": []}, 0
        raise ValueError("対面一覧を1件も抽出できません")
    entries = list(rows.values())
    return {
        "favorable": sorted((m for m in entries if m["winrate_num"] >= 50),
                             key=lambda m: (-m["winrate_num"], -m["games"], m["champion_id"]))[:LIMIT],
        "unfavorable": sorted((m for m in entries if m["winrate_num"] < 50),
                               key=lambda m: (m["winrate_num"], -m["games"], m["champion_id"]))[:LIMIT],
    }, len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-cache", action="store_true", help="今回取得済みのHTMLで保存前検証を再開する")
    args = parser.parse_args()
    master_path = BASE / "merged_data/all_champions.json"
    master = json.loads(master_path.read_text(encoding="utf-8"))
    champions = {}
    strategies = {}
    tasks = []
    for cid, champ in master.items():
        # 基礎JSONの英語名はIDと異なるため、OP.GGの画像altを同じパッチの英語辞書で照合する。
        champions[cid] = {"name": champ["name"], "name_en": cid}
        strategy_path = Path(find_strategy_file(str(BASE / "strategy_data"), cid))
        strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
        strategies[cid] = (strategy_path, strategy)
        for role in champ["roles"]:
            tasks.append((cid, role, strategy["slug"], champ["patch"]))
    for patch in {task[3] for task in tasks}:
        url = f"https://ddragon.leagueoflegends.com/cdn/{patch}/data/en_US/champion.json"
        with urllib.request.urlopen(urllib.request.Request(url, headers=get_headers()), timeout=30) as response:
            english = json.load(response)["data"]
        for cid in champions:
            champions[cid]["name_en"] = english[cid]["name"]

    cache = BASE / "scratch/counter_pages"
    cache.mkdir(parents=True, exist_ok=True)

    def fetch(task):
        cid, role, slug, patch = task
        short = ".".join(patch.split(".")[:2])
        url = f"https://www.op.gg/champions/{slug}/counters/{ROLE_PATH[role]}?region=global&tier=emerald_plus&type=ranked&patch={short}"
        page = cache / f"{cid}_{role}_{patch}.html"
        for attempt in range(3):
            try:
                if args.reuse_cache and page.exists():
                    html = page.read_text(encoding="utf-8")
                else:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=get_headers()), timeout=30) as response:
                        html = response.read().decode("utf-8")
                matchups, available = parse_counter_page(html, cid, role, patch, champions, url)
                page.write_text(html, encoding="utf-8")
                return cid, role, matchups, available, url
            except Exception as exc:
                if attempt == 2:
                    raise ValueError(f"{cid}/{role}: {exc}") from exc
                time.sleep(1)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result in tqdm(pool.map(fetch, tasks), total=len(tasks), desc="対面一覧取得・検証"):
            results.append(result)
    # 全ページの検証後に対面データだけを更新し、ビルドや手動補完を保持する。
    report = []
    for cid, role, matchups, available, url in results:
        strategy = strategies[cid][1]
        strategy["role_data"][role]["matchups"] = matchups
        master[cid]["role_data"][role]["matchups"] = matchups
        if role == master[cid]["roles"][0]:
            strategy["matchups"] = matchups
            master[cid]["matchups"] = matchups
        report.append({"champion_id": cid, "role": role, "available": available,
                       "status": "ok" if available else "insufficient_sample",
                       "favorable": len(matchups["favorable"]), "unfavorable": len(matchups["unfavorable"]), "url": url})
    def save(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for cid, (path, strategy) in tqdm(strategies.items(), desc="対面データ保存"):
        save(path, strategy)
        save(BASE / "merged_data" / f"{cid}.json", master[cid])
    save(master_path, master)
    save(BASE / "docs/matchup_refresh_report.json", report)
    print(f"{len(master)}体・{len(results)}ロールの有利不利を最大{LIMIT}体へ更新しました。")


if __name__ == "__main__":
    main()
