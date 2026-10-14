import json
import re
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MERGED_DIR = BASE_DIR / "merged_data"
ALL_CHAMPS_FILE = MERGED_DIR / "all_champions.json"

def parse_matchup_entry(entry, default_role="TOP", default_patch="14.20.1"):
    """
    旧形式および混在形式のマッチアップエントリを正規スキーマに変換する。
    スキーマ:
    {
        "champion_id": str,
        "name": str,
        "winrate": str,          # e.g. "55.29%"
        "winrate_num": float,    # e.g. 55.29
        "winrate_display": str,  # e.g. "勝率 55.29%"
        "reason": str or None,   # 戦術的理由（スキル・立ち回り）。ない場合はNone
        "role": str,
        "patch": str,
        "source": str,
        "is_estimated": bool
    }
    """
    champ_id = entry.get("champion_id") or entry.get("id") or ""
    name = entry.get("name") or champ_id
    role = entry.get("role") or default_role
    patch = entry.get("patch") or default_patch
    source = entry.get("source") or "opgg_stats"
    is_estimated = entry.get("is_estimated", False)

    raw_reason = entry.get("reason") or ""
    existing_winrate = entry.get("winrate")

    winrate_val = None
    winrate_num = None
    winrate_display = None
    tactical_reason = None

    # 1. 既存のwinrateフィールドがある場合
    if existing_winrate:
        m_wr = re.search(r"(\d+(?:\.\d+)?)%", str(existing_winrate))
        if m_wr:
            winrate_num = float(m_wr.group(1))
            winrate_val = f"{winrate_num:.1f}%" if "." in m_wr.group(1) else f"{winrate_num}%"
            # 少数点第2位まであればそれを保持
            orig_str = m_wr.group(1)
            winrate_val = f"{orig_str}%"
            winrate_display = f"勝率 {winrate_val}"

    # 2. raw_reason の解析
    if " | " in raw_reason:
        parts = raw_reason.split(" | ", 1)
        wr_part = parts[0].strip()
        reason_part = parts[1].strip()

        m_wr = re.search(r"(\d+(?:\.\d+)?)%", wr_part)
        if m_wr:
            winrate_num = float(m_wr.group(1))
            winrate_val = f"{m_wr.group(1)}%"
            winrate_display = f"勝率 {winrate_val}"

        if reason_part and not is_generic_or_stats_only(reason_part):
            tactical_reason = reason_part
    elif raw_reason:
        # "勝率 XX%（統計的に有利）" または勝率のみのパターン
        m_wr = re.search(r"(\d+(?:\.\d+)?)%", raw_reason)
        if m_wr:
            if not winrate_val:
                winrate_num = float(m_wr.group(1))
                winrate_val = f"{m_wr.group(1)}%"
                winrate_display = f"勝率 {winrate_val}"
            # 勝率以外のテキスト部分を調べる
            cleaned = re.sub(r"勝率\s*\d+(?:\.\d+)?%", "", raw_reason)
            cleaned = re.sub(r"[（\(].*?[）\)]", "", cleaned).strip()
            if cleaned and not is_generic_or_stats_only(cleaned):
                tactical_reason = cleaned
            else:
                tactical_reason = None
        else:
            # 勝率が含まれない文章
            if not is_generic_or_stats_only(raw_reason):
                tactical_reason = raw_reason.strip()
            else:
                tactical_reason = None

    # 既存の entry に既にきれいな reason がある場合
    if entry.get("reason") and not raw_reason:
        pass

    return {
        "champion_id": champ_id,
        "name": name,
        "winrate": winrate_val,
        "winrate_num": winrate_num,
        "winrate_display": winrate_display,
        "reason": tactical_reason,
        "role": role,
        "patch": patch,
        "source": source,
        "is_estimated": is_estimated
    }

def is_generic_or_stats_only(text):
    if not text:
        return True
    t = text.strip()
    if t in ["統計的に有利", "統計的に不利", "統計データなし", "理由データなし", "有利", "不利", "互角", "五分"]:
        return True
    if re.fullmatch(r"勝率\s*\d+(?:\.\d+)?%\s*(?:（統計的に(?:有利|不利)）)?", t):
        return True
    return False

def migrate_champion_matchups(champ_data):
    """
    1体のチャンピオンの matchups (top-level) と role_data.*.matchups を正規化し同期する。
    """
    cid = champ_data.get("id", "")
    roles = champ_data.get("roles", ["TOP"])
    main_role = roles[0] if roles else "TOP"
    patch = champ_data.get("patch", "14.20.1")

    # 1. トップレベルの既存matchupsを正規化
    top_matchups = champ_data.get("matchups", {})
    norm_top_fav = []
    norm_top_unfav = []

    # メインロールの辞書として対面ID -> 詳細理由のマッピングを作る
    rich_reason_map = {}

    for item in top_matchups.get("favorable", []):
        norm = parse_matchup_entry(item, default_role=main_role, default_patch=patch)
        norm_top_fav.append(norm)
        if norm["reason"]:
            rich_reason_map[norm["champion_id"]] = norm["reason"]

    for item in top_matchups.get("unfavorable", []):
        norm = parse_matchup_entry(item, default_role=main_role, default_patch=patch)
        norm_top_unfav.append(norm)
        if norm["reason"]:
            rich_reason_map[norm["champion_id"]] = norm["reason"]

    # 2. role_data 内の各ロールの matchups を正規化＆同期
    role_data = champ_data.get("role_data", {})
    for rname, rinfo in role_data.items():
        rm = rinfo.get("matchups", {})
        norm_rfav = []
        norm_runfav = []

        for item in rm.get("favorable", []):
            norm = parse_matchup_entry(item, default_role=rname, default_patch=patch)
            # メインロールかつ理由が空で、トップレベルに詳細理由がある場合は同期
            if not norm["reason"] and rname == main_role and norm["champion_id"] in rich_reason_map:
                norm["reason"] = rich_reason_map[norm["champion_id"]]
            norm_rfav.append(norm)

        for item in rm.get("unfavorable", []):
            norm = parse_matchup_entry(item, default_role=rname, default_patch=patch)
            # メインロールかつ理由が空で、トップレベルに詳細理由がある場合は同期
            if not norm["reason"] and rname == main_role and norm["champion_id"] in rich_reason_map:
                norm["reason"] = rich_reason_map[norm["champion_id"]]
            norm_runfav.append(norm)

        rinfo["matchups"] = {
            "favorable": norm_rfav,
            "unfavorable": norm_runfav
        }

    # 3. トップレベル側もロール側で新しい理由が見つかった場合は逆補完
    for norm in norm_top_fav:
        if not norm["reason"]:
            # メインロールのデータから探す
            main_rm = role_data.get(main_role, {}).get("matchups", {}).get("favorable", [])
            for m in main_rm:
                if m.get("champion_id") == norm["champion_id"] and m.get("reason"):
                    norm["reason"] = m["reason"]
                    break

    for norm in norm_top_unfav:
        if not norm["reason"]:
            main_rm = role_data.get(main_role, {}).get("matchups", {}).get("unfavorable", [])
            for m in main_rm:
                if m.get("champion_id") == norm["champion_id"] and m.get("reason"):
                    norm["reason"] = m["reason"]
                    break

    champ_data["matchups"] = {
        "favorable": norm_top_fav,
        "unfavorable": norm_top_unfav
    }

    return champ_data

def main():
    print("データ移行を開始します...")
    with open(ALL_CHAMPS_FILE, "r", encoding="utf-8") as f:
        champions = json.load(f)

    migrated_count = 0
    total = len(champions)

    for cid, cdata in tqdm(champions.items(), desc="マッチアップ正規化・同期中"):
        migrate_champion_matchups(cdata)
        migrated_count += 1

    # all_champions.json に書き出し
    print("all_champions.json に書き込み中...")
    with open(ALL_CHAMPS_FILE, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    # 個別チャンピオンJSONの同期書き出し
    print("個別チャンピオンJSONファイルを同期更新中...")
    for cid, cdata in tqdm(champions.items(), desc="個別JSON同期中"):
        indiv_file = MERGED_DIR / f"{cid}.json"
        with open(indiv_file, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False, indent=2)

    print(f"[完了] 全 {migrated_count} 体のチャンピオンデータを正規スキーマへ移行・同期しました。")

if __name__ == "__main__":
    main()
