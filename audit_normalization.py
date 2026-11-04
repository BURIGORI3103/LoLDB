"""収集・統合・監査補正で共有する、推測を含まない正規化。"""
import copy
import html
import json
import re
from html.parser import HTMLParser

SHARDS = {
    5008: "アダプティブフォース", 5005: "攻撃速度", 5007: "スキルヘイスト",
    5010: "移動速度", 5001: "スケーリング体力", 5011: "体力", 5013: "行動妨害耐性",
}
SHARD_NAMES = dict(zip(
    ["Adaptive Force", "Attack Speed", "Ability Haste", "Move Speed", "Health Scaling", "Health", "Tenacity and Slow Resist"],
    SHARDS.values(),
))
SHARD_NAMES.update({"Movement Speed": "移動速度", "Tenacity": "行動妨害耐性"})


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif not self.hidden and tag in ("br", "p", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in ("p", "li"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value):
    parser = _Text()
    parser.feed(str(value or ""))
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines()).strip()


def canonical_item_ids(raw, referenced=()):
    referenced = {str(i) for i in referenced}
    return {str(i) for i, item in raw.items()
            if str(i).isdigit() and len(str(i)) <= 4 and str(i) not in {"1105", "1106", "1107"}
            and item.get("maps", {}).get("11", False)
            and (item.get("inStore", True) or item.get("specialRecipe")
                 or item.get("requiredChampion") or item.get("requiredAlly") or str(i) in referenced)}


def referenced_item_ids(champions):
    ids = set()
    for champ in champions.values():
        for data in [champ, *champ.get("role_data", {}).values()]:
            groups = list(data.get("build", {}).values())
            for pattern in data.get("build_patterns", []):
                groups.extend(pattern.get(key, []) for key in ("core_items", "starter_items", "boots_items", "situational_items", "items"))
            for group in groups:
                if isinstance(group, list):
                    for item in group:
                        if isinstance(item, dict) and (iid := item.get("item_id", item.get("id"))):
                            ids.add(str(iid))
    return ids


def validate_build_references(champ, items):
    for role, data in [("primary", champ), *champ.get("role_data", {}).items()]:
        for group in data.get("build", {}).values():
            for item in group:
                if str(item.get("item_id")) not in items:
                    raise ValueError(f"未登録アイテム: {champ['id']} {role} {item.get('item_id')}")


def is_finished_item(iid, raw, allowed=None):
    iid = str(iid)
    allowed = canonical_item_ids(raw) if allowed is None else allowed
    item = raw.get(iid, {})
    if iid not in allowed or not item or set(item.get("tags", [])) & {"Boots", "Consumable", "Trinket", "Jungle", "Lane"}:
        return False
    successors = [raw[x] for x in item.get("into", []) if x in allowed
                  and not raw[x].get("specialRecipe") and not raw[x].get("requiredAlly")
                  and not raw[x].get("requiredChampion")]
    return not successors and bool(item.get("from") or item.get("specialRecipe") or item.get("requiredAlly"))


def decode_rsc(page):
    matches = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:\\.|[^"\\])*)"\]\)', page, re.S)
    return "".join(json.loads('"' + part + '"') for part in matches)


def rsc_records(stream):
    decoder = json.JSONDecoder()
    records = {}
    for match in re.finditer(r"(?:^|\n)([a-f0-9]+):", stream):
        try:
            records[match[1]] = decoder.raw_decode(stream, match.end())[0]
        except ValueError:
            continue
    return records


def walk_rsc(value, records=None, seen=frozenset()):
    records = records or {}
    if isinstance(value, str) and (match := re.fullmatch(r"\$L?([a-f0-9]+)", value)):
        key = match[1]
        if key in records and key not in seen:
            yield from walk_rsc(records[key], records, seen | {key})
    elif isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_rsc(child, records, seen)
    elif isinstance(value, list):
        for child in value:
            yield from walk_rsc(child, records, seen)


def rsc_item_groups(stream, group):
    """React行または辞書配列の終端内だけを読み、遅延参照も解決する。"""
    decoder = json.JSONDecoder()
    records = rsc_records(stream)
    groups = {}
    row_pattern = r'\["\$",\s*"tr",\s*"(' + re.escape(group) + r'_\d+)"'
    for match in re.finditer(row_pattern, stream):
        row = decoder.raw_decode(stream, match.start())[0]
        groups[match[1]] = list(dict.fromkeys(str(node["metaId"]) for node in walk_rsc(row, records)
                                            if "metaId" in node and node.get("metaType", "item") == "item"))
    for match in re.finditer(r'"(' + re.escape(group) + r'_\d+)"\s*:\s*', stream):
        value = decoder.raw_decode(stream, match.end())[0]
        groups[match[1]] = list(dict.fromkeys(str(node["metaId"]) for node in walk_rsc(value, records)
                                            if "metaId" in node and node.get("metaType", "item") == "item"))
    return [groups[key] for key in sorted(groups, key=lambda key: int(key.rsplit("_", 1)[1]))]


def rune_parent_names(trees):
    return {rune["name"]: tree["name"] for tree in trees for slot in tree["slots"] for rune in slot["runes"]}


def pattern_from_build(build, patch, role):
    return {"name": "OP.GG 推奨ビルド", "desc": f"パッチ{patch}・{role}の取得済み統計",
            "source": "opgg_stats", "patch": patch,
            "core": [item["name"] for item in build.get("core", [])], "core_items": copy.deepcopy(build.get("core", [])),
            "starter": [item["name"] for item in build.get("starter", [])],
            "boots": next((item["name"] for item in build.get("boots", [])), ""),
            "situational": [item["name"] for item in build.get("situational", [])],
            "starter_items": copy.deepcopy(build.get("starter", [])), "boots_items": copy.deepcopy(build.get("boots", [])),
            "situational_items": copy.deepcopy(build.get("situational", []))}


def normalize_with_evidence(champ, base):
    item_path = base / "merged_data/all_items.json"
    evidence_path = base / "data/role_guidance_evidence.json"
    items = json.loads(item_path.read_text(encoding="utf-8")) if item_path.exists() else {}
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else []
    return normalize_champion(champ, items, evidence)


def normalize_runes(runes, parent_names):
    result = copy.deepcopy(runes)
    for kind in ("primary", "secondary"):
        part = result.setdefault(kind, {})
        names = ([part.get("keystone_name")] if kind == "primary" else []) + part.get("choices", [])
        parents = {parent_names[name] for name in names if name in parent_names}
        if len(parents) != 1:
            raise ValueError(f"ルーン所属を一意に確認できません: {kind} {names}")
        part["path"] = parents.pop()
    result["shards"] = [SHARD_NAMES.get(name, name) for name in result.get("shards", [])]
    if any(re.search(r"[A-Za-z]", name) for name in result["shards"]):
        raise ValueError(f"未確認のシャード名: {result['shards']}")
    return result


def normalize_champion(champ, items, evidence=()):
    """統計値には触れず、テキストとビルド参照と確認済み補完を同期する。"""
    result = copy.deepcopy(champ)
    for key in ("abilities", "spells"):
        for spell in result.get(key, []):
            spell["description"] = plain_text(spell.get("description"))
    names = {item["name"]: iid for iid, item in items.items()}
    for role, rd in [(None, result), *result.get("role_data", {}).items()]:
        if result["id"] == "Cassiopeia":
            rd.setdefault("build", {})["boots"] = []
        rd["gameplay_notes"] = {key: re.sub(r"^\s*(?:【[^】]+】\s*)+", "", text)
                                for key, text in rd.get("gameplay_notes", {}).items()}
        for bp in rd.get("build_patterns", []):
            for field, old in (("starter_items", "starter"), ("boots_items", "boots"), ("situational_items", "situational")):
                values = bp.get(field)
                if values is None:
                    old_values = bp.get(old, [])
                    if isinstance(old_values, str):
                        old_values = [old_values] if old_values else []
                    values = [{"item_id": names.get(name), "name": name} for name in old_values]
                bp[field] = [{"item_id": str(it.get("item_id", it.get("id", ""))), "name": items[str(it.get("item_id", it.get("id", "")))]["name"]}
                             for it in values if str(it.get("item_id", it.get("id", ""))) in items]
            if result["id"] == "Cassiopeia":
                bp["boots_items"] = []
                bp["boots"] = ""
            prefix = result.get("damage_profile", {}).get("primary_type", "")
            if prefix in {"AD", "AP", "TANK", "HYBRID"}:
                bp["name"] = re.sub(r"^(?:\[(?:AD|AP|TANK|HYBRID)\]\s*)+", "", bp.get("name", ""))
                bp["name"] = f"[{prefix}] {bp['name']}"
        for entry in evidence:
            if entry.get("verified") and entry["champion_id"] == result["id"] and entry["role"] == role:
                if entry.get("source_patch") not in (None, "未検証", result.get("patch")):
                    continue
                rd[entry["field"]] = copy.deepcopy(entry["value"])
                rd.setdefault("guidance_sources", {})[entry["field"]] = {k: entry[k] for k in ("source_url", "source_patch", "checked_at")}
    primary = result.get("roles", [None])[0]
    if primary in result.get("role_data", {}):
        result["build_patterns"] = copy.deepcopy(result["role_data"][primary].get("build_patterns", []))
    return result


def project_for_display(champions):
    """正本を変更せず、同一情報を一度だけHTMLへ埋め込む。"""
    projected = copy.deepcopy(champions)
    for champ in projected.values():
        for key in ("matchup_matrix", "matchup_matrix_by_role", "build_source", "runes_source", "opgg_source"):
            champ.pop(key, None)
        roles = list(champ.get("role_data", {}).values())
        if not roles:
            continue
        for key in ("build", "build_patterns", "runes", "matchups", "summoner_spells", "spell_sets"):
            champ.pop(key, None)
        shared = {}
        for key in ("attack_type", "combos", "skill_order", "skill_matrix", "gameplay_notes", "role_note", "spell_sets"):
            if key in roles[0] and all(rd.get(key) == roles[0][key] for rd in roles):
                shared[key] = roles[0][key]
                for rd in roles:
                    rd.pop(key, None)
        champ["common_role_data"] = shared
        for rd in roles:
            for key in ("opgg_source", "build_source", "runes_source"):
                rd.pop(key, None)
    return projected
