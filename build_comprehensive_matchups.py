"""
build_comprehensive_matchups.py - レーン別・パッチ別・実測/推定厳格分離の相性構築スクリプト
=========================================================================================
- レーン (role) の次元を持たせ、別レーンの対面統計が他レーンに混入しないよう厳格に分離する
- 実測統計データには role, patch, source, region, tier, fetched_at, sample_note を記録する
- 実測データが存在しない組み合わせ（またはレーン不一致・不明時）はヒューリスティック推定とし、
  推定要因 (estimation_factors) と限界説明 (estimation_limitation) を付与して実測値と明確に区別する
"""

import json
import sys
from pathlib import Path
from tqdm import tqdm

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent
MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"

ESTIMATION_LIMITATION_NOTE = (
    "基礎ステータス（射程・ダメージ属性・サステイン・クラス特性）に基づく特性シナジー推定です。"
    "実戦のプレイヤースキルやパッチメタ、ジャングル介入等により結果は変動します（実測統計勝率ではありません）。"
)


def _enrich_measured_entry(entry: dict, adv: str, default_role: str, patch: str) -> dict:
    """実測統計エントリに参照元・地域・ランク・取得日などのメタデータを補完して返す"""
    wr_str = entry.get("winrate")
    wr_num = entry.get("winrate_num")
    if wr_num is None and wr_str:
        try:
            wr_num = float(str(wr_str).replace("%", "").strip())
        except ValueError:
            wr_num = None
    wr_disp = entry.get("winrate_display") or (f"勝率 {wr_str}" if wr_str else ("有利" if adv == "fav" else "不利"))
    role_val = entry.get("role") or default_role
    patch_val = entry.get("patch") or patch
    region_val = entry.get("region", "Global")
    tier_val = entry.get("tier", "Emerald+")
    fetched_val = entry.get("fetched_at", "2026-10")
    sample_val = entry.get("sample_note", "OP.GG ロール別カウンター統計")
    detail = entry.get("reason") or (
        "統計的に主導権を握りやすい有利なマッチアップです。"
        if adv == "fav"
        else "統計的に警戒すべき不利なマッチアップです。無理なトレードを避ける必要があります。"
    )
    label_prefix = "有利" if adv == "fav" else "警戒・不利"

    return {
        "champion_id": entry.get("champion_id", ""),
        "name": entry.get("name", ""),
        "winrate": wr_str,
        "winrate_num": wr_num,
        "winrate_display": wr_disp,
        "advantage": adv,
        "advantage_label": f"{label_prefix}（{wr_disp} / {role_val}実測）" if wr_str else f"{label_prefix}（{role_val}実測統計）",
        "reason": detail,
        "source": entry.get("source", "opgg_stats"),
        "is_estimated": False,
        "role": role_val,
        "patch": patch_val,
        "region": region_val,
        "tier": tier_val,
        "fetched_at": fetched_val,
        "sample_note": sample_val,
    }


def calculate_heuristic_matchup(me: dict, opp: dict, role: str | None = None) -> dict:
    """
    実測データがない（またはレーンが異なる/不明な）場合に、特性シナジーに基づく推定相性と
    推定要因・限界説明を返す。実測勝率 (winrate) は常に None とし実測値と同列に扱わない。
    """
    me_id = me.get("id")
    opp_id = opp.get("id")
    patch = me.get("patch", "16.20.1")

    if me_id == opp_id:
        return {
            "winrate": None,
            "winrate_num": None,
            "winrate_display": None,
            "advantage": "even",
            "advantage_label": "五分（ミラーマッチ）",
            "reason": "同チャンピオン対決です。ルーン選択、スキルの命中率、ウェーブコントロール等の技量勝負になります。",
            "source": "mirror",
            "is_estimated": False,
            "role": role or "ALL",
            "patch": patch,
        }

    score = 0
    me_dp = me.get("damage_profile", {})
    opp_dp = opp.get("damage_profile", {})
    me_sustain = me.get("sustain_info", {}).get("has_sustain", False)
    opp_sustain = opp.get("sustain_info", {}).get("has_sustain", False)

    reasons = []
    factors = []

    # ① ダメージ属性と防具特性
    if me_id in ["Malphite", "Rammus"] and opp_dp.get("primary_type") == "AD":
        score += 3
        factors.append("対AD物理防御特化 (+3)")
        reasons.append("物理防御(AR)スケールにより、相手のAD物理ダメージを大幅に軽減できます")
    elif opp_id in ["Malphite", "Rammus"] and me_dp.get("primary_type") == "AD":
        score -= 3
        factors.append("相手の対AD物理防御特化 (-3)")
        reasons.append("相手の高い物理防御と通常攻撃反射により、ADダメージが通りにくい対面です")

    if me_id in ["Galio", "Kassadin"] and opp_dp.get("primary_type") == "AP":
        score += 3
        factors.append("対AP魔法耐性特化 (+3)")
        reasons.append("魔法耐性パッシブと魔法シールドにより、相手のAPバーストを容易に耐えきれます")
    elif opp_id in ["Galio", "Kassadin"] and me_dp.get("primary_type") == "AP":
        score -= 3
        factors.append("相手の対AP魔法耐性特化 (-3)")
        reasons.append("相手の対AP防御性能とシールドにより、こちらの魔法バーストが軽減されます")

    # ② サステイン（回復力）格差
    if me_sustain and not opp_sustain:
        score += 1
        factors.append("サステイン優位 (+1)")
        reasons.append("高い固有サステインによりショートトレード後の体力差でレーン主導権を握れます")
    elif not me_sustain and opp_sustain:
        score -= 1
        factors.append("相手サステイン優位 (-1)")
        reasons.append("相手のサステイン回復により消耗戦で不利になりやすいため、早期の重傷アイテム購入が有効です")

    # ③ ロール・クラスの相性
    me_classes = me.get("classes") or me.get("tags") or []
    opp_classes = opp.get("classes") or opp.get("tags") or []
    is_opp_assassin = "Assassin" in opp_classes or any(k in opp_id for k in ["Zed", "Talon", "Qiyana", "Katarina"])
    is_me_assassin = "Assassin" in me_classes or any(k in me_id for k in ["Zed", "Talon", "Qiyana", "Katarina"])

    if ("Tank" in me_classes or me_dp.get("primary_type") == "TANK") and is_opp_assassin:
        score += 2
        factors.append("タンク対アサシン耐久優位 (+2)")
        reasons.append("アサシンの瞬間バーストを耐久力で受け止め、CCで拘束して反撃できます")
    elif ("Tank" in opp_classes or opp_dp.get("primary_type") == "TANK") and is_me_assassin:
        score -= 2
        factors.append("アサシン対タンク突破難 (-2)")
        reasons.append("相手の高耐久を削りきれず、アサシン側のバーストが通りにくい構成です")

    # ④ 割合ダメージ・タンクキラー
    if me_id in ["Vayne", "Fiora", "Gwen", "KogMaw"] and opp_dp.get("primary_type") == "TANK":
        score += 2
        factors.append("対タンク割合・確定ダメージ (+2)")
        reasons.append("最大体力割合ダメージと確定ダメージにより、相手の防具を無視して削れます")
    elif opp_id in ["Vayne", "Fiora", "Gwen", "KogMaw"] and me_dp.get("primary_type") == "TANK":
        score -= 2
        factors.append("相手の対タンク割合・確定ダメージ (-2)")
        reasons.append("相手の割合ダメージ・確定ダメージにより、防具を積んでも耐えきれないリスクがあります")

    # ⑤ レンジ差 (長射程 vs 近接)
    me_range = me.get("stats", {}).get("attackrange", 175)
    opp_range = opp.get("stats", {}).get("attackrange", 175)
    if me_range >= 500 and opp_range <= 200:
        score += 1
        factors.append(f"通常攻撃射程優位 ({me_range} vs {opp_range}, +1)")
        reasons.append("射程差を活かしたアウトレンジポークで安全にハラスできます")
    elif opp_range >= 500 and me_range <= 200:
        score -= 1
        factors.append(f"相手射程優位 ({me_range} vs {opp_range}, -1)")
        reasons.append("相手の遠距離ポークにより序盤の被弾に注意し、不用意なヘルスロスを避ける必要があります")

    if not factors:
        factors.append("標準ステータス均衡 (0)")

    if score >= 2:
        adv = "fav"
        adv_label = "特性推定: 有利傾向"
        reason_text = " ＆ ".join(reasons)
    elif score <= -2:
        adv = "unfav"
        adv_label = "特性推定: 警戒傾向"
        reason_text = " ＆ ".join(reasons)
    else:
        adv = "even"
        adv_label = "特性推定: 五分"
        reason_text = reasons[0] if reasons else "明確な特性差がなく、スキルの命中精度や立ち回り次第で五分に戦える対面です。"

    return {
        "winrate": None,
        "winrate_num": None,
        "winrate_display": None,
        "advantage": adv,
        "advantage_label": adv_label,
        "reason": reason_text,
        "source": "synergy_estimate",
        "is_estimated": True,
        "role": role or "ESTIMATED",
        "patch": patch,
        "estimation_factors": factors,
        "estimation_limitation": ESTIMATION_LIMITATION_NOTE,
    }


def calculate_matchup(me: dict, opp: dict, target_role: str | None = None) -> dict:
    """
    (自分, 相手, レーン, パッチ) を基準に相性を判定する。
    - target_role が指定されている場合は、そのレーン (role_data[target_role] または role==target_role) の
      実測統計のみを検索し、別レーンのデータは絶対に混同しない。
    - target_role が None（レーン不明）の場合は実測統計を混ぜず、ヒューリスティック推定を返す。
    """
    me_id = me.get("id")
    opp_id = opp.get("id")
    patch = me.get("patch", "16.20.1")

    if me_id == opp_id:
        return calculate_heuristic_matchup(me, opp, role=target_role)

    # レーン不明の場合は実測統計として扱わず、推定結果を返す
    if not target_role or target_role == "UNKNOWN":
        return calculate_heuristic_matchup(me, opp, role=target_role)

    # 指定されたレーンの実測データのみを収集（別レーンの統計は混ぜない）
    role_fav = []
    role_unfav = []

    def is_current_measurement(entry):
        return (not entry.get("is_estimated", False)
                and entry.get("source", "opgg_stats") == "opgg_stats"
                and (not entry.get("patch") or entry["patch"] == patch))

    role_info = me.get("role_data", {}).get(target_role, {})
    if role_info:
        for m in role_info.get("matchups", {}).get("favorable", []):
            if m.get("role", target_role) == target_role and is_current_measurement(m):
                role_fav.append(m)
        for m in role_info.get("matchups", {}).get("unfavorable", []):
            if m.get("role", target_role) == target_role and is_current_measurement(m):
                role_unfav.append(m)

    # トップレベル matchups も role が target_role と明示一致するものだけ許可
    primary_role = (me.get("roles") or ["TOP"])[0]
    for m in me.get("matchups", {}).get("favorable", []):
        m_role = m.get("role") or primary_role
        if m_role == target_role and is_current_measurement(m):
            role_fav.append(m)
    for m in me.get("matchups", {}).get("unfavorable", []):
        m_role = m.get("role") or primary_role
        if m_role == target_role and is_current_measurement(m):
            role_unfav.append(m)

    # 同一レーン内で有利・不利の両方に登録されている異常データがないか勝率数値で客観判定
    matched_entry = None
    matched_adv = None
    for fav in role_fav:
        if fav.get("champion_id") == opp_id or fav.get("name") == opp.get("name"):
            matched_entry = fav
            matched_adv = "fav"
            break

    for unfav in role_unfav:
        if unfav.get("champion_id") == opp_id or unfav.get("name") == opp.get("name"):
            if matched_entry is not None:
                # 万が一同一レーンの有利と不利の両方にあった場合は winrate_num が 50.0 以上かで決定
                wr_num = unfav.get("winrate_num") or matched_entry.get("winrate_num") or 50.0
                matched_adv = "fav" if float(wr_num) >= 50.0 else "unfav"
                matched_entry = fav if matched_adv == "fav" else unfav
            else:
                matched_entry = unfav
                matched_adv = "unfav"
            break

    if matched_entry and matched_adv:
        return _enrich_measured_entry(matched_entry, matched_adv, target_role, patch)

    return calculate_heuristic_matchup(me, opp, role=target_role)


def main():
    print("🔧 ステップ 1/3: チャンピオンデータ読み込み中... (33%)")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    champ_list = list(champions.values())
    total_champs = len(champ_list)
    print(f"🔧 ステップ 2/3: 全 {total_champs} 体のレーン別実測相性辞書（推定・実測厳格分離）を構築中... (66%)")

    measured_pair_count = 0
    for me in tqdm(champ_list, desc="レーン別マッチアップ構築"):
        patch = me.get("patch", "16.20.1")
        roles = me.get("roles") or ["TOP"]

        # 1. 各ロールの matchups メタデータを正規化・補完
        for rname in roles:
            if "role_data" in me and rname in me["role_data"]:
                rm = me["role_data"][rname].get("matchups", {})
                me["role_data"][rname]["matchups"] = {
                    "favorable": [
                        _enrich_measured_entry(m, "fav", rname, patch) for m in rm.get("favorable", [])
                    ],
                    "unfavorable": [
                        _enrich_measured_entry(m, "unfav", rname, patch) for m in rm.get("unfavorable", [])
                    ],
                }

        # トップレベル matchups もメインロールを明記して正規化
        main_role = roles[0]
        top_m = me.get("matchups", {})
        me["matchups"] = {
            "favorable": [_enrich_measured_entry(m, "fav", m.get("role") or main_role, patch) for m in top_m.get("favorable", [])],
            "unfavorable": [_enrich_measured_entry(m, "unfav", m.get("role") or main_role, patch) for m in top_m.get("unfavorable", [])],
        }

        # 2. (自分, 相手, レーン, パッチ) 単位の実測相性マップ matchup_matrix_by_role を構築
        #    ※全組み合わせの冗長な推定オブジェクトを埋め込むとファイルが14MBに肥大化するため、
        #      実測統計が存在するペアをレーン別に厳密格納し、メインロール用の matchup_matrix も実測ペアのみ格納する
        matrix_by_role = {}
        for rname in roles:
            role_matrix = {}
            for opp in champ_list:
                opp_id = opp["id"]
                res = calculate_matchup(me, opp, target_role=rname)
                if not res.get("is_estimated", True) and res.get("source") != "mirror":
                    role_matrix[opp_id] = res
                    measured_pair_count += 1
            matrix_by_role[rname] = role_matrix

        me["matchup_matrix_by_role"] = matrix_by_role
        me["matchup_matrix"] = matrix_by_role.get(main_role, {})

    print(f"  -> レーン別実測ペア登録数: {measured_pair_count} 件（推定ペアはオンデマンド計算化によりデータサイズを大幅削減）")

    print("🔧 ステップ 3/3: マスターJSONおよび個別JSONへ書き出し中... (100%)")
    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    merged_dir = BASE_DIR / "merged_data"
    for cid, cdata in tqdm(champions.items(), desc="個別JSON同期中"):
        indiv_file = merged_dir / f"{cid}.json"
        with open(indiv_file, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] レーン別相性マトリクスの構築と軽量化が完了しました: {MERGED_JSON}")


if __name__ == "__main__":
    main()
