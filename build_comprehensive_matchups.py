import json
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"

def calculate_matchup(me, opp):
    """
    2体のチャンピオン特性を分析し、実測統計データまたは推定相性を算出する。
    ハッシュ値による擬似勝率生成は完全廃止し、実測と推定を明確に区別する。
    """
    me_id = me.get("id")
    opp_id = opp.get("id")
    patch = me.get("patch", "16.20.1")

    # 0. ミラーマッチ
    if me_id == opp_id:
        return {
            "winrate": "50.0%",
            "winrate_num": 50.0,
            "winrate_display": "勝率 50.0%",
            "advantage": "even",
            "advantage_label": "五分（ミラーマッチ）",
            "reason": "同チャンピオン対決です。ルーン選択、スキルの命中率、ウェーブコントロール等の技量勝負になります。",
            "source": "mirror",
            "is_estimated": False,
            "patch": patch
        }

    # 1. 既存の実測統計データ（OP.GG個別収集データ）があるかチェック
    # トップレベルおよび全role_dataを検索
    all_matchups_fav = list(me.get("matchups", {}).get("favorable", []))
    all_matchups_unfav = list(me.get("matchups", {}).get("unfavorable", []))

    for rname, rinfo in me.get("role_data", {}).items():
        all_matchups_fav.extend(rinfo.get("matchups", {}).get("favorable", []))
        all_matchups_unfav.extend(rinfo.get("matchups", {}).get("unfavorable", []))

    for fav in all_matchups_fav:
        if fav.get("champion_id") == opp_id or fav.get("name") == opp.get("name"):
            wr_str = fav.get("winrate")
            wr_num = fav.get("winrate_num")
            wr_disp = fav.get("winrate_display") or (f"勝率 {wr_str}" if wr_str else "有利")
            detail = fav.get("reason") or "統計的に主導権を握りやすい有利なマッチアップです。"
            return {
                "winrate": wr_str,
                "winrate_num": wr_num,
                "winrate_display": wr_disp,
                "advantage": "fav",
                "advantage_label": f"有利（{wr_disp}）" if wr_str else "有利（実測統計）",
                "reason": detail,
                "source": fav.get("source", "opgg_stats"),
                "is_estimated": False,
                "patch": fav.get("patch", patch),
                "role": fav.get("role", me.get("roles", ["TOP"])[0])
            }

    for unfav in all_matchups_unfav:
        if unfav.get("champion_id") == opp_id or unfav.get("name") == opp.get("name"):
            wr_str = unfav.get("winrate")
            wr_num = unfav.get("winrate_num")
            wr_disp = unfav.get("winrate_display") or (f"勝率 {wr_str}" if wr_str else "不利")
            detail = unfav.get("reason") or "統計的に警戒すべき不利なマッチアップです。無理なトレードを避ける必要があります。"
            return {
                "winrate": wr_str,
                "winrate_num": wr_num,
                "winrate_display": wr_disp,
                "advantage": "unfav",
                "advantage_label": f"警戒・不利（{wr_disp}）" if wr_str else "警戒・不利（実測統計）",
                "reason": detail,
                "source": unfav.get("source", "opgg_stats"),
                "is_estimated": False,
                "patch": unfav.get("patch", patch),
                "role": unfav.get("role", me.get("roles", ["TOP"])[0])
            }

    # 2. 実測データがない場合：統計的シナジー・特性相性エンジン（推定相性）
    # ※ハッシュ値によるランダム・疑似勝率生成は完全廃止し、winrateはNoneとする。
    score = 0  # 0を基準にアドバンテージを算出

    me_dp = me.get("damage_profile", {})
    opp_dp = opp.get("damage_profile", {})
    me_sustain = me.get("sustain_info", {}).get("has_sustain", False)
    opp_sustain = opp.get("sustain_info", {}).get("has_sustain", False)

    reasons = []

    # ① ダメージ属性と防具特性
    # マルファイト、ラムス vs AD
    if me_id in ["Malphite", "Rammus"] and opp_dp.get("primary_type") == "AD":
        score += 3
        reasons.append("物理防御(AR)スケールにより、相手のAD物理ダメージを大幅に軽減できます")
    elif opp_id in ["Malphite", "Rammus"] and me_dp.get("primary_type") == "AD":
        score -= 3
        reasons.append("相手の高い物理防御と通常攻撃反射により、ADダメージが通りにくい対面です")

    # ガリオ、カサディン vs AP
    if me_id in ["Galio", "Kassadin"] and opp_dp.get("primary_type") == "AP":
        score += 3
        reasons.append("魔法耐性パッシブと魔法シールドにより、相手のAPバーストを容易に耐えきれます")
    elif opp_id in ["Galio", "Kassadin"] and me_dp.get("primary_type") == "AP":
        score -= 3
        reasons.append("相手の対AP防御性能とシールドにより、こちらの魔法バーストが軽減されます")

    # ② サステイン（回復力）格差
    if me_sustain and not opp_sustain:
        score += 1
        reasons.append("高い固有サステインによりショートトレード後の体力差でレーン主導権を握れます")
    elif not me_sustain and opp_sustain:
        score -= 1
        reasons.append("相手のサステイン回復により消耗戦で不利になりやすいため、早期の重傷アイテム購入が有効です")

    # ③ ロール・クラスのジャンケン相性
    me_classes = me.get("classes") or me.get("tags") or []
    opp_classes = opp.get("classes") or opp.get("tags") or []
    is_opp_assassin = "Assassin" in opp_classes or any(k in opp_id for k in ["Zed", "Talon", "Qiyana", "Katarina"])
    is_me_assassin = "Assassin" in me_classes or any(k in me_id for k in ["Zed", "Talon", "Qiyana", "Katarina"])

    if ("Tank" in me_classes or me_dp.get("primary_type") == "TANK") and is_opp_assassin:
        score += 2
        reasons.append("アサシンの瞬間バーストを耐久力で受け止め、CCで拘束して反撃できます")
    elif ("Tank" in opp_classes or opp_dp.get("primary_type") == "TANK") and is_me_assassin:
        score -= 2
        reasons.append("相手の高耐久を削りきれず、アサシン側のバーストが通りにくい構成です")

    # 割合ダメージ・タンクキラー
    if me_id in ["Vayne", "Fiora", "Gwen", "KogMaw"] and opp_dp.get("primary_type") == "TANK":
        score += 2
        reasons.append("最大体力割合ダメージと確定ダメージにより、相手の防具を無視して削れます")
    elif opp_id in ["Vayne", "Fiora", "Gwen", "KogMaw"] and me_dp.get("primary_type") == "TANK":
        score -= 2
        reasons.append("相手の割合ダメージ・確定ダメージにより、防具を積んでも耐えきれないリスクがあります")

    # レンジ差 (長射程 vs 近接)
    me_range = me.get("stats", {}).get("attackrange", 175)
    opp_range = opp.get("stats", {}).get("attackrange", 175)
    if me_range >= 500 and opp_range <= 200:
        score += 1
        reasons.append("射程差を活かしたアウトレンジポークで安全にハラスできます")
    elif opp_range >= 500 and me_range <= 200:
        score -= 1
        reasons.append("相手の遠距離ポークにより序盤の被弾に注意し、不用意なヘルスロスを避ける必要があります")

    # 判定 (実測勝率はNone)
    if score >= 2:
        adv = "fav"
        adv_label = "推定有利"
        reason_text = " ＆ ".join(reasons) if reasons else "スキル構成と特性の噛み合わせにより主導権を握りやすい推定対面です。"
    elif score <= -2:
        adv = "unfav"
        adv_label = "推定警戒・不利"
        reason_text = " ＆ ".join(reasons) if reasons else "相手の特性や交戦距離が厳しく、慎重な立ち回りが求められる推定対面です。"
    else:
        adv = "even"
        adv_label = "推定五分"
        reason_text = reasons[0] if reasons else "明確な相性差がなく、スキルの命中精度や立ち回り次第で五分に戦える対面です。"

    return {
        "winrate": None,
        "winrate_num": None,
        "winrate_display": None,
        "advantage": adv,
        "advantage_label": adv_label,
        "reason": reason_text,
        "source": "synergy_estimate",
        "is_estimated": True,
        "patch": patch
    }

def main():
    print("チャンピオンデータ読み込み中...")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    champ_list = list(champions.values())
    total_champs = len(champ_list)
    print(f"全 {total_champs} 体の全組み合わせマッチアップ辞書（推定・実測厳格分離）を構築中...")

    for me in tqdm(champ_list, desc="マッチアップマトリクス構築"):
        me_id = me["id"]
        matrix = {}
        for opp in champ_list:
            opp_id = opp["id"]
            res = calculate_matchup(me, opp)
            matrix[opp_id] = res

        me["matchup_matrix"] = matrix

    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    # 個別JSONも更新
    merged_dir = BASE_DIR / "merged_data"
    for cid, cdata in tqdm(champions.items(), desc="個別JSON同期中"):
        indiv_file = merged_dir / f"{cid}.json"
        with open(indiv_file, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] 全チャンピオンに対面マトリクスを埋め込み同期完了しました: {MERGED_JSON}")

if __name__ == "__main__":
    main()
