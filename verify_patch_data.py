"""公式・統計・wiki・アプリ生成物のパッチ整合性を検証する。"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(*, write_report=True):
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    champions = read(BASE / "merged_data/all_champions.json")
    official = {p.stem: read(p) for p in (BASE / "champions_data").glob("*.json")}
    items = read(BASE / "merged_data/all_items.json")
    patches = {c["patch"] for c in champions.values()}
    require(len(patches) == 1, "マスターが空か複数パッチが混在")
    patch = next(iter(patches))
    short = ".".join(patch.split(".")[:2])
    require(champions.keys() == official.keys(), "公式一覧とマスターが不一致")
    roles = pairs = 0
    for cid, c in champions.items():
        require(c["patch"] == official[cid]["patch"], f"公式パッチと不一致: {cid}")
        require(c == read(BASE / "merged_data" / f"{cid}.json"), f"個別JSONと不一致: {cid}")
        require(c["wiki_info"]["status"] == "success", f"wiki未取得: {cid}")
        require(c["opgg_source"]["patch_verified"] is True and c["opgg_source"]["patch"] == short,
                f"OP.GGのパッチ未検証または不一致: {cid}")
        require(all(k in c for k in ("attack_type", "damage_profile", "sustain_info", "combos", "skill_matrix")),
                f"必須チャンピオン情報が不足: {cid}")
        require(bool(c["roles"]) and set(c["role_data"]) == set(c["roles"]), f"ロール構成が不正: {cid}")
        for role, data in c["role_data"].items():
            roles += 1
            source = data["opgg_source"]
            require(source["role"] == role and source["patch"] == short and source["patch_verified"] is True,
                    f"ロール別OP.GGのパッチ未検証または不一致: {cid} {role}")
            require(data["runes"]["primary"]["keystone"] and data["build"]["core"], f"ルーンかビルドが欠落: {cid} {role}")
            for item in data["build"]["core"]:
                require(item["item_id"] in items, f"アイテム辞書に未登録: {cid} {item}")
            for entry in c["matchup_matrix_by_role"][role].values():
                pairs += 1
                require(entry["patch"] == patch and entry["role"] == role, f"対面のパッチかロールが不一致: {cid} {role}")
                require(entry["source"] == "opgg_stats" and entry["is_estimated"] is False, f"対面が実測統計でない: {cid} {role}")
                require(entry["champion_id"] in champions, f"対面相手が未登録: {cid} {role}")
    md = (BASE / "docs/LoL_URL_list.md").read_text(encoding="utf-8")
    require(len(re.findall(r"^- \[x\]", md, re.M)) == len(champions) and "- [ ]" not in md,
            "URLの取得チェックが未完了")
    html = (BASE / "dist/index.html").read_text(encoding="utf-8")
    require(html == (BASE / "index.html").read_text(encoding="utf-8"), "ルートとdistのHTMLが不一致")
    require(f"Patch {short}" in html and "wikiの考察・対策" in html, "HTMLのパッチかwiki見出しが不一致")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
    for script in scripts:
        subprocess.run(["node", "--check"], input=script, text=True, encoding="utf-8", check=True, capture_output=True)
    report = {"verified_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"), "patch": patch,
              "champions": len(champions), "roles": roles, "items": len(items), "wiki_success": len(champions),
              "measured_matchup_pairs": pairs, "url_checks_complete": True, "individual_json_consistent": True,
              "javascript_syntax_valid": True}
    if write_report:
        (BASE / "docs/data_refresh_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="公式・統計・wiki・アプリ生成物のパッチ整合性検証")
    parser.add_argument("--check", action="store_true", help="検証レポートを書き込まない")
    run(write_report=not parser.parse_args().check)
