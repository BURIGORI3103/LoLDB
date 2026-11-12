"""
merge_data.py - champions_data と strategy_data を統合しマスターJSONを生成
========================================================================
champions_data（公式基礎値）と strategy_data（攻略統計値）をチャンピオンIDをキーにして突合し、
実運用レーン情報（roles）の上書きやサモナースペルの追加を行って、
merged_data/all_champions.json を出力します。
"""

import argparse
import json
import copy
import math
import os
import tempfile
from pathlib import Path
from tqdm import tqdm
from audit_normalization import normalize_with_evidence, pattern_from_build

def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=os.path.dirname(path), delete=False
        ) as temp:
            temp_path = Path(temp.name)
            json.dump(data, temp, ensure_ascii=False, indent=2)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

# Data DragonのチャンピオンIDとOP.GGスラッグの表記揺れエイリアス辞書
CHAMPION_SLUG_ALIASES = {
    "monkeyking": "monkeyking",
    "renata": "renata",
    "nunu": "nunu",
}


def choose_matchups(previous, measured, patch, role):
    """同一パッチ・ロールの新しい対面専用取得結果を再統合で巻き戻さない。"""
    old = previous.get("matchups", {})
    new = measured.get("matchups", {})
    entries = [entry for group in old.values() for entry in group]
    incoming = [entry for group in new.values() for entry in group]
    if entries and all(entry.get("patch") == patch and entry.get("role") == role
                       and entry.get("source") == "opgg_stats" and entry.get("games") is not None for entry in entries):
        if max(entry.get("fetched_at", "") for entry in entries) >= max((entry.get("fetched_at", "") for entry in incoming), default=""):
            return copy.deepcopy(old)
    return copy.deepcopy(new)


def merge_record(base, strategy, previous):
    """手動補完を保ちつつ統計を現在パッチ・現在ロールの取得結果へ置換する。"""
    patch = base["patch"]
    short_patch = ".".join(patch.split(".")[:2])
    strategy_source = strategy.get("opgg_source", {}) if strategy else {}
    if (not strategy or strategy.get("patch") != patch
            or strategy_source.get("patch") != short_patch
            or strategy_source.get("patch_verified") is not True):
        raise ValueError(f"最新パッチの検証済み攻略データがありません: {base['id']}")
    merged = copy.deepcopy(previous)
    merged.update(base)
    merged["classes"] = base.get("roles", [])
    for key in ("roles", "summoner_spells", "matchups", "build", "runes", "wiki_info", "opgg_source"):
        merged[key] = copy.deepcopy(strategy.get(key, {} if key not in ("roles", "summoner_spells") else []))
    merged["matchups"] = choose_matchups(previous, strategy, base["patch"], merged["roles"][0])
    for key in ("build_source", "runes_source"):
        if key in strategy:
            merged[key] = copy.deepcopy(strategy[key])
    for entries in merged["matchups"].values():
        for entry in entries:
            entry["reason"] = "理由データなし"
    old_roles = previous.get("role_data", {})
    roles = {}
    for role in merged["roles"]:
        measured = strategy.get("role_data", {}).get(role)
        source = measured.get("opgg_source", {}) if measured else {}
        if (not measured or measured.get("patch") != patch or source.get("role") != role
                or source.get("patch") != short_patch or source.get("patch_verified") is not True):
            raise ValueError(f"ロール別統計がありません: {base['id']} {role}")
        rd = copy.deepcopy(old_roles.get(role, {}))
        rd.update({key: copy.deepcopy(measured[key]) for key in ("build", "runes", "matchups", "opgg_source")})
        rd["matchups"] = choose_matchups(old_roles.get(role, {}), measured, base["patch"], role)
        for key in ("build_source", "runes_source"):
            if key in measured:
                rd[key] = copy.deepcopy(measured[key])
        for entries in rd["matchups"].values():
            for entry in entries:
                entry["reason"] = "理由データなし"
        rd["role"] = role
        rd["spells"] = measured["summoner_spells"]
        rd["build_patterns"] = [pattern_from_build(measured["build"], base["patch"], role)]
        rd["spell_sets"] = [{"name": "OP.GG 推奨", "spells": measured["summoner_spells"]}]
        roles[role] = rd
    merged["role_data"] = roles
    primary = merged["roles"][0]
    merged["build_patterns"] = copy.deepcopy(roles[primary]["build_patterns"])
    merged["gameplay_notes"] = copy.deepcopy(previous.get("gameplay_notes", {}))
    for key in ("matchup_matrix", "matchup_matrix_by_role"):
        merged.pop(key, None)
    from apply_matchup_reasons import apply_reasons, load_evidence
    return normalize_with_evidence(apply_reasons(merged, load_evidence()), Path(__file__).resolve().parent)

def find_strategy_file(strategy_dir, champ_id):
    lower_id = champ_id.lower()
    candidate_slugs = [
        lower_id,
        CHAMPION_SLUG_ALIASES.get(lower_id, ""),
        lower_id.replace(" ", "").replace("'", "").replace(".", "")
    ]
    for slug in candidate_slugs:
        if not slug:
            continue
        p = os.path.join(strategy_dir, f"{slug}.json")
        if os.path.exists(p):
            return p
    return None

OFFICIAL_STAT_FIELDS = frozenset("""
    hp hpperlevel mp mpperlevel movespeed armor armorperlevel spellblock spellblockperlevel
    attackrange hpregen hpregenperlevel mpregen mpregenperlevel crit critperlevel
    attackdamage attackdamageperlevel attackspeedperlevel attackspeed
""".split())


def _has_skill_fields(skill):
    return (
        isinstance(skill, dict)
        and all(isinstance(skill.get(field), str) for field in ("slot", "name", "description", "image"))
        and bool(skill["name"] and skill["image"])
    )


def validate_official_record(base, path):
    """公式スナップショットが正本の能力値・スキルを空にするのを防ぐ。"""
    if (not isinstance(base, dict) or base.get("id") != path.stem
            or not isinstance(base.get("patch"), str) or not base["patch"]):
        raise ValueError(f"公式チャンピオンデータが不正です: {path}")

    stats = base.get("stats")
    if (not isinstance(stats, dict) or not OFFICIAL_STAT_FIELDS <= stats.keys()
            or any(type(stats[field]) not in (int, float) or not math.isfinite(stats[field])
                   for field in OFFICIAL_STAT_FIELDS)):
        raise ValueError(f"公式チャンピオンの能力値が不正です: {path}")

    spells = base.get("spells")
    abilities = base.get("abilities")
    if (not isinstance(spells, list) or not all(_has_skill_fields(skill) for skill in spells)
            or [skill["slot"] for skill in spells[:4]] != ["Q", "W", "E", "R"]
            or not isinstance(abilities, list) or not all(_has_skill_fields(skill) for skill in abilities)
            or not any(skill["slot"] == "Passive" for skill in abilities)):
        raise ValueError(f"公式チャンピオンのスキルが不正です: {path}")


def merge_champion_data(*, check_only=False):
    base_dir = "champions_data"
    strategy_dir = "strategy_data"
    output_dir = "merged_data"
    combined_file = os.path.join(output_dir, "all_champions.json")
    previous = load_json(combined_file)
    if previous is None and not os.path.exists(combined_file):
        previous = {}
    if not isinstance(previous, dict):
        raise ValueError("既存マスターが不正です。データを確認してから再実行してください。")

    base_paths = sorted(Path(base_dir).glob("*.json"))
    if not base_paths:
        raise ValueError("公式チャンピオンデータがありません。")
    missing_ids = previous.keys() - {path.stem for path in base_paths}
    if missing_ids:
        raise ValueError(f"既存チャンピオンの公式データが欠落しています: {', '.join(sorted(missing_ids))}")

    print("データの結合処理を開始します...")
    all_champions_dict = {}
    patch = None
    for base_path in tqdm(base_paths, desc="データ統合中", unit="champ"):
        champ_id = base_path.stem
        base = load_json(base_path)
        validate_official_record(base, base_path)
        if patch is not None and base["patch"] != patch:
            raise ValueError(f"公式データに複数パッチが混在しています: {base_path}")
        patch = base["patch"]
        strategy_path = find_strategy_file(strategy_dir, champ_id)
        strategy = load_json(strategy_path) if strategy_path else None
        all_champions_dict[champ_id] = merge_record(base, strategy, previous.get(champ_id, {}))

    if check_only:
        print(f"書き込みなしで検証済み: {len(all_champions_dict)} 体 / パッチ {patch}")
        return

    # 全件の検証を通過するまで既存のマスター・個別JSONへ書き込まない。
    for cid, merged in tqdm(all_champions_dict.items(), desc="検証済みJSON保存"):
        save_json(merged, os.path.join(output_dir, f"{cid}.json"))
    save_json(all_champions_dict, combined_file)

    file_size_kb = os.path.getsize(combined_file) / 1024 if os.path.exists(combined_file) else 0

    print("結合処理が完了しました。")
    print(f"全チャンピオン数: {len(all_champions_dict)} 体")
    print(f"マスターファイル容量: {file_size_kb:.2f} KB")
    print(f"出力先フォルダ: {output_dir}")
    print(f"統合データファイル: {combined_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="公式データと取得済み統計の統合")
    parser.add_argument("--check", action="store_true", help="検証のみ行い、保存しない")
    merge_champion_data(check_only=parser.parse_args().check)
