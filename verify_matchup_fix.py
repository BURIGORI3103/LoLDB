import json
import hashlib
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def verify_all():
    errors = []
    print("=== 1. merged_data/all_champions.json の検証 ===")
    with open(BASE_DIR / "merged_data" / "all_champions.json", "r", encoding="utf-8") as f:
        champs = json.load(f)

    # Aatrox, Garen, Yasuo, Ahri 等をチェック
    for cid in ["Aatrox", "Garen", "Yasuo", "Ahri"]:
        c = champs[cid]
        top_fav = c.get("matchups", {}).get("favorable", [])
        if not top_fav:
            errors.append(f"{cid}: top matchups favorable is empty")
        for item in top_fav:
            if not item.get("winrate"):
                errors.append(f"{cid}: top favorable missing winrate: {item}")
            if not item.get("reason"):
                errors.append(f"{cid}: top favorable missing tactical reason: {item}")
            if "統計的に有利" in (item.get("reason") or ""):
                errors.append(f"{cid}: top favorable reason contains stats boilerplate: {item}")

        # role_data check
        for rname, rinfo in c.get("role_data", {}).items():
            rm = rinfo.get("matchups", {})
            for item in rm.get("favorable", []) + rm.get("unfavorable", []):
                r = item.get("reason") or ""
                if "統計的に有利" in r or "統計的に不利" in r:
                    errors.append(f"{cid} role {rname}: reason contains boilerplate: {item}")

    # ハッシュ勝率の不在チェック
    hash_detected = False
    for cid, c in champs.items():
        mat = c.get("matchup_matrix", {})
        for opp_id, mentry in mat.items():
            if mentry.get("is_estimated") and mentry.get("winrate") is not None:
                errors.append(f"{cid} vs {opp_id}: estimated matchup has pseudo winrate: {mentry}")
                hash_detected = True
                break
        if hash_detected:
            break

    print(f"Champs verified: {len(champs)}")

    print("\n=== 2. 生成物 (index.html / dist/index.html) の検証 ===")
    root_html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    dist_html = (BASE_DIR / "dist" / "index.html").read_text(encoding="utf-8")

    if root_html != dist_html:
        errors.append("index.html and dist/index.html are NOT identical!")
    else:
        print("[OK] index.html and dist/index.html are completely identical.")

    # HTML内のJSロジックチェック
    if "escapeHtml" not in root_html:
        errors.append("escapeHtml is not found in generated HTML")
    else:
        print("[OK] escapeHtml is present in generated HTML.")

    if "renderMatchupCard" not in root_html:
        errors.append("renderMatchupCard is not found in generated HTML")
    else:
        print("[OK] renderMatchupCard is present in generated HTML.")

    if "理由データなし" not in root_html:
        errors.append("'理由データなし' is not found in generated HTML")
    else:
        print("[OK] '理由データなし' explicit fallback is present in generated HTML.")

    # Service Worker
    sw_file = (BASE_DIR / "dist" / "sw.js").read_text(encoding="utf-8")
    from build_pwa import _parse_markdown_update_block
    version = _parse_markdown_update_block((BASE_DIR / "UPDATE.md").read_text(encoding="utf-8"))["version"]
    expected_cache = f"loldb-core-{version}-{hashlib.sha256(root_html.encode('utf-8')).hexdigest()[:8]}"
    if expected_cache not in sw_file:
        errors.append(f"Service Workerのキャッシュ名が生成HTMLと不一致: {expected_cache}")
    else:
        print(f"[OK] キャッシュ名と生成HTMLが一致: {expected_cache}")

    if errors:
        print(f"\n[FAIL] Found {len(errors)} errors:")
        for err in errors[:10]:
            print(f"  - {err}")
        return False
    else:
        print("\n[SUCCESS] すべての検証項目をパスしました！")
        return True

if __name__ == "__main__":
    success = verify_all()
    exit(0 if success else 1)
