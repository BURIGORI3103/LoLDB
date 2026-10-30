"""対面・ロール・方向の一致した文献確認済み解説だけを付与する。"""
import copy
import json
from pathlib import Path
from tqdm import tqdm

BASE = Path(__file__).resolve().parent


def apply_reasons(champion, evidence):
    cid = champion["id"]
    roles = champion.get("roles", [])
    def apply(entry, role, side):
        entry["reason"] = ""
        entry.pop("reason_evidence", None)
        found = next((r for r in evidence if r.get("confirmation") == "source_confirmed"
                      and r.get("champion_id") == cid and r.get("opponent_id") == entry.get("champion_id")
                      and r.get("role") == role and r.get("advantage") == side
                      and r.get("source_url", "").startswith("https://") and r.get("reason")), None)
        if found:
            entry["reason"] = found["reason"]
            entry["reason_evidence"] = copy.deepcopy(found)
    for side, entries in champion.get("matchups", {}).items():
        for entry in entries:
            apply(entry, entry.get("role") or (roles[0] if roles else None), side)
    for role, rd in champion.get("role_data", {}).items():
        for side, entries in rd.get("matchups", {}).items():
            for entry in entries:
                apply(entry, role, side)
    for role, matrix in champion.get("matchup_matrix_by_role", {}).items():
        for entry in matrix.values():
            apply(entry, role, "favorable" if entry.get("advantage") == "fav" else "unfavorable")
    if roles and "matchup_matrix_by_role" in champion:
        champion["matchup_matrix"] = copy.deepcopy(champion["matchup_matrix_by_role"].get(roles[0], {}))
    return champion


def load_evidence():
    return json.loads((BASE / "data/matchup_reason_evidence.json").read_text(encoding="utf-8"))


def main():
    path = BASE / "merged_data/all_champions.json"
    champions = json.loads(path.read_text(encoding="utf-8"))
    evidence = load_evidence()
    count = 0
    for cid, c in tqdm(champions.items(), desc="出典確認済み理由を反映"):
        apply_reasons(c, evidence)
        count += sum(bool(e.get("reason_evidence")) for rd in c.get("role_data", {}).values() for es in rd.get("matchups", {}).values() for e in es)
        (BASE / "merged_data" / f"{cid}.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    path.write_text(json.dumps(champions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"文献確認済み解説: {count}件")


if __name__ == "__main__":
    main()
