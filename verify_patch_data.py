"""公式・統計・wiki・アプリ生成物のパッチ整合性を検証する。"""
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).resolve().parent


def run():
    def read(path):
        return json.loads(path.read_text(encoding="utf-8"))
    champions = read(BASE / "merged_data/all_champions.json")
    official = {p.stem: read(p) for p in (BASE / "champions_data").glob("*.json")}
    items = read(BASE / "merged_data/all_items.json")
    patches = {c["patch"] for c in champions.values()}
    assert len(patches) == 1, "マスターに複数パッチが混在"
    patch = next(iter(patches))
    short = ".".join(patch.split(".")[:2])
    assert champions.keys() == official.keys(), "公式一覧とマスターが不一致"
    roles = pairs = 0
    for cid, c in champions.items():
        assert c["patch"] == official[cid]["patch"]
        assert c == read(BASE / "merged_data" / f"{cid}.json"), f"個別JSONと不一致: {cid}"
        assert c["wiki_info"]["status"] == "success"
        assert c["opgg_source"]["patch_verified"] and c["opgg_source"]["patch"] == short
        assert all(k in c for k in ("attack_type", "damage_profile", "sustain_info", "combos", "skill_matrix"))
        assert set(c["role_data"]) == set(c["roles"])
        for role, data in c["role_data"].items():
            roles += 1
            assert data["opgg_source"]["role"] == role and data["opgg_source"]["patch"] == short
            assert data["runes"]["primary"]["keystone"] and data["build"]["core"]
            for item in data["build"]["core"]:
                assert item["item_id"] in items, f"アイテム辞書に未登録: {cid} {item}"
            for entry in c["matchup_matrix_by_role"][role].values():
                pairs += 1
                assert entry["patch"] == patch and entry["role"] == role
                assert entry["source"] == "opgg_stats" and not entry["is_estimated"]
                assert entry["champion_id"] in champions
    md = (BASE / "docs/LoL_URL_list.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^- \[x\]", md, re.M)) == len(champions) and "- [ ]" not in md
    html = (BASE / "dist/index.html").read_text(encoding="utf-8")
    assert html == (BASE / "index.html").read_text(encoding="utf-8")
    assert f"Patch {short}" in html and "wikiの考察・対策" in html
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S)
    for script in scripts:
        subprocess.run(["node", "--check"], input=script, text=True, encoding="utf-8", check=True, capture_output=True)
    report = {"verified_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"), "patch": patch,
              "champions": len(champions), "roles": roles, "items": len(items), "wiki_success": len(champions),
              "measured_matchup_pairs": pairs, "url_checks_complete": True, "individual_json_consistent": True,
              "javascript_syntax_valid": True}
    (BASE / "docs/data_refresh_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    run()
