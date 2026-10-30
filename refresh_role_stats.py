"""OP.GGのロール別統計を検証して攻略JSONへ保存する。"""
import concurrent.futures
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from process_url_list import (build_dictionaries, parse_opgg_rsc,
                              validate_parsed_opgg_data, get_headers, JST, tqdm)
from merge_data import find_strategy_file

BASE = Path(__file__).resolve().parent
ROLE_PATH = {"TOP": "top", "JUG": "jungle", "MID": "mid", "ADC": "adc", "SUP": "support"}
ROLE_TITLE = {"TOP": "Top", "JUG": "Jungle", "MID": "Middle", "ADC": "Bottom", "SUP": "Support"}


def run():
    version, items, runes, paths, champs, spells = build_dictionaries()
    short = ".".join(version.split(".")[:2])
    datasets = {}
    tasks = []
    for base in sorted((BASE / "champions_data").glob("*.json")):
        target = Path(find_strategy_file(str(BASE / "strategy_data"), base.stem))
        data = json.loads(target.read_text(encoding="utf-8"))
        if data.get("patch") != version or not data.get("opgg_source", {}).get("patch_verified"):
            raise ValueError(f"最新統計の取得が未完了: {base.stem}")
        datasets[base.stem] = (target, data)
        data["role_data"] = {}
        for role in data["roles"]:
            tasks.append((base.stem, role, data["slug"]))

    def fetch(task):
        cid, role, slug = task
        url = f"https://www.op.gg/champions/{slug}/build/{ROLE_PATH[role]}"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=get_headers()), timeout=15) as response:
                    html = response.read().decode("utf-8")
                if not re.search(r'Build for\s+' + ROLE_TITLE[role] + r',\s*Patch\s+' + re.escape(short) + r'\b', html, re.I):
                    raise ValueError("ページのロールまたはパッチが一致しません")
                parsed = parse_opgg_rsc(html, items, runes, paths, champs, version)
                valid, reason = validate_parsed_opgg_data(parsed, html, slug)
                if not valid:
                    raise ValueError(reason)
                for entries in parsed["matchups"].values():
                    for entry in entries:
                        entry["role"] = role
                parsed["opgg_source"] = {"url": url, "patch": short, "patch_verified": True,
                                         "role": role, "fetched_at": datetime.now(JST).isoformat(timespec="seconds")}
                return cid, role, parsed
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for cid, role, parsed in tqdm(pool.map(fetch, tasks), total=len(tasks), desc="ロール別統計取得"):
            datasets[cid][1]["role_data"][role] = parsed
    for target, data in datasets.values():
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"全{len(datasets)}体・{len(tasks)}ロールのパッチ{short}統計を保存しました。")


if __name__ == "__main__":
    run()
