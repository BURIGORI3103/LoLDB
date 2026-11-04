"""指定パッチのビルド・ルーンだけを再取得し、監査指摘を補正する。"""
import argparse
import concurrent.futures
import copy
import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from tqdm import tqdm
from audit_normalization import normalize_champion, normalize_runes, plain_text, rune_parent_names, pattern_from_build, validate_build_references
from merge_data import find_strategy_file
from process_url_list import build_dictionaries, get_headers, parse_opgg_rsc, JST

BASE = Path(__file__).resolve().parent
ROLE_PATH = {"TOP": "top", "JUG": "jungle", "MID": "mid", "ADC": "adc", "SUP": "support"}
ROLE_TITLE = {"TOP": "Top", "JUG": "Jungle", "MID": "Middle", "ADC": "Bottom", "SUP": "Support"}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)




def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch", required=True, help="正本と一致するData Dragonパッチ")
    parser.add_argument("--fetch-only", action="store_true", help="検証済みHTMLキャッシュの取得のみ")
    parser.add_argument("--reuse-cache", action="store_true", help="同一パッチで取得したHTMLを明示的に再利用")
    args = parser.parse_args()
    master_path = BASE / "merged_data/all_champions.json"
    previous = json.loads(master_path.read_text(encoding="utf-8"))
    if {champ["patch"] for champ in previous.values()} != {args.patch}:
        raise ValueError("パッチが正本と一致しません")
    short = ".".join(args.patch.split(".")[:2])
    cache = BASE / "scratch/audit" / args.patch / "build_pages"
    cache.mkdir(parents=True, exist_ok=True)
    strategies = {cid: Path(find_strategy_file(str(BASE / "strategy_data"), cid)) for cid in previous}
    strategy_data = {cid: json.loads(path.read_text(encoding="utf-8")) for cid, path in strategies.items()}
    tasks = [(cid, role, strategy_data[cid]["slug"]) for cid, champ in previous.items() for role in champ["roles"]]

    def fetch(task):
        cid, role, slug = task
        url = f"https://op.gg/lol/champions/{slug}/build/{ROLE_PATH[role]}?patch={short}"
        target = cache / f"{cid}_{role}.html"
        for attempt in range(3):
            try:
                if args.reuse_cache and target.exists():
                    page = target.read_text(encoding="utf-8")
                else:
                    with urllib.request.urlopen(urllib.request.Request(url, headers=get_headers()), timeout=20) as response:
                        page = response.read().decode("utf-8")
                heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", page, re.S | re.I)
                text = re.sub(r"\s+", " ", plain_text(re.sub(r"<[^>]+>", " ", heading[1]))) if heading else ""
                if not re.search(r"Build for\s*" + ROLE_TITLE[role] + r",\s*Patch\s*" + re.escape(short) + r"\b", text):
                    raise ValueError(f"ロール・パッチの照合失敗: {cid} {role}")
                if f"/champion/{cid}.png" not in page:
                    raise ValueError(f"チャンピオンの照合失敗: {cid}")
                target.write_text(page, encoding="utf-8")
                return cid, role, page, url
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1)

    print("ステップ1/3: 全ロールの対象・パッチを照合して取得します (0%)", flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        pages = list(tqdm(pool.map(fetch, tasks), total=len(tasks), desc="ビルド取得・照合"))
    if args.fetch_only:
        print(f"検証済みページ {len(pages)} 件をキャッシュしました (100%)")
        return

    print("ステップ2/3: 全件をメモリ上で補正・検証します (50%)", flush=True)
    version, items, runes, paths, champs, _ = build_dictionaries(args.patch)
    trees_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/ja_JP/runesReforged.json"
    with urllib.request.urlopen(trees_url, timeout=20) as response:
        parents = rune_parent_names(json.load(response))
    item_data = json.loads((BASE / "merged_data/all_items.json").read_text(encoding="utf-8"))
    evidence_path = BASE / "data/role_guidance_evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else []
    updated = copy.deepcopy(previous)
    now = datetime.now(JST).isoformat(timespec="seconds")
    core_shortages = []
    for cid, role, page, url in tqdm(pages, desc="ビルド・ルーン補正"):
        parsed = parse_opgg_rsc(page, items, runes, paths, champs, version, champion_id=cid)
        parsed["runes"] = normalize_runes(parsed["runes"], parents)
        if not parsed["build"]["core"]:
            raise ValueError(f"完成品を取得できません: {cid} {role}")
        if len(parsed["build"]["core"]) < 3:
            core_shortages.append({"champion_id": cid, "role": role, "items": len(parsed["build"]["core"])})
        if cid == "Cassiopeia":
            parsed["build"]["boots"] = []
        source = {"url": url, "patch": short, "role": role, "patch_verified": True, "fetched_at": now}
        for rd in (updated[cid]["role_data"][role], strategy_data[cid]["role_data"][role]):
            for key in ("build", "runes"):
                rd[key] = copy.deepcopy(parsed[key])
                rd[key + "_source"] = source
            rd["build_patterns"] = [pattern_from_build(parsed["build"], version, role)]
    bases = {}
    for cid, champ in tqdm(updated.items(), desc="正規化と保持検証"):
        primary = champ["roles"][0]
        for data in (champ, strategy_data[cid]):
            for key in ("build", "runes", "build_source", "runes_source"):
                data[key] = copy.deepcopy(champ["role_data"][primary][key])
        wiki = champ.get("wiki_info", {})
        if not champ.get("overview") and wiki.get("status") == "success":
            summary = next(iter(wiki.get("sections", {}).values()), "")
            champ["overview"] = {"summary": plain_text(summary), "source_url": wiki.get("source_url", ""), "source_patch": "未検証"}
        updated[cid] = normalize_champion(champ, item_data, evidence)
        validate_build_references(updated[cid], item_data)
        for role, before in [(None, previous[cid]), *previous[cid]["role_data"].items()]:
            after = updated[cid] if role is None else updated[cid]["role_data"][role]
            if before.get("matchups") != after.get("matchups"):
                raise ValueError(f"対面統計が変更されています: {cid} {role}")
        base_path = BASE / "champions_data" / f"{cid}.json"
        base = json.loads(base_path.read_text(encoding="utf-8"))
        for key in ("abilities", "spells"):
            for skill in base.get(key, []):
                skill["description"] = plain_text(skill.get("description"))
        bases[cid] = base
    print("ステップ3/3: 全件の検証完了後に保存します (85%)", flush=True)
    for cid in tqdm(updated, desc="検証済みJSON保存"):
        write_json(BASE / "champions_data" / f"{cid}.json", bases[cid])
        write_json(BASE / "merged_data" / f"{cid}.json", updated[cid])
        write_json(strategies[cid], strategy_data[cid])
    write_json(master_path, updated)
    write_json(BASE / "data/rune_reference.json", {"patch": version, "parents": parents})
    write_json(BASE / "docs/audit_data_report.json", {"patch": version, "fetched_at": now, "champions": len(updated),
               "roles": len(pages), "core_shortages": core_shortages, "matchups_preserved": True})
    print(f"{len(updated)}体・{len(pages)}ロールを補正しました (100%)")


if __name__ == "__main__":
    run()
