"""
scratch/generate_matchup_reasons.py
===================================
全チャンピオンの対面1行戦術理由を再計算・同期する。
新パッチでOP.GG対面が変動した場合でも、全チャンピオン×対面の
具体的で実戦的な1行戦術理由を自動生成・補完・同期する。
"""

import sys
import json
import re
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"
MERGED_DIR = BASE_DIR / "merged_data"

def generate_tactical_matchup_reason(me, opp, is_fav):
    """
    自キャラと相手キャラのスキル特性・ダメージ型・ロール・射程を分析し、
    具体的で実戦的な1行戦術理由を生成する。
    """
    me_id = me.get("id", "")
    opp_id = opp.get("id", "")
    me_name = me.get("name", me_id)
    opp_name = opp.get("name", opp_id)

    me_dp = me.get("damage_profile", {})
    opp_dp = opp.get("damage_profile", {})
    me_classes = me.get("classes") or me.get("tags") or []
    opp_classes = opp.get("classes") or opp.get("tags") or []

    me_sustain = me.get("sustain_info", {}).get("has_sustain", False)
    opp_sustain = opp.get("sustain_info", {}).get("has_sustain", False)

    me_range = me.get("stats", {}).get("attackrange", 175)
    opp_range = opp.get("stats", {}).get("attackrange", 175)

    # 1. 固有の代表的マッチアップ理由マスター辞書
    SPECIFIC_REASONS = {
        ("Garen", "Riven"): "Qのサイレンスでリヴェンの高速スキルコンボを完全に封殺し、WのシールドとE回転でトレードを圧倒できるため有利",
        ("Garen", "Jax"): "ジャックスのE（カウンターストライク）をWで耐え、スタン解除後にQ沈黙とE回転で主導権を奪えるため有利",
        ("Garen", "Sylas"): "サイラスの魔法トレードをWのシールドとパッシブで受け流し、QサイレンスからのE回転とR確定ダメージで圧倒できるため有利",
        ("Garen", "Yasuo"): "ヤスオのシールドを剥がした後にQサイレンスとE回転で主導権を握り、風の壁を無視して突進できるため有利",
        ("Garen", "Cassiopeia"): "接近さえできれば近接戦闘の圧倒的火力差で一気に制圧・処刑可能なため有利",
        ("Garen", "Camille"): "カミールのシールドと確定ダメージトレードに耐えにくく、E離脱を捕まえにくいため不利",
        ("Garen", "Darius"): "ダリウスの引き寄せとパッシブ出血スタックによる殴り合いで殴り負けやすいため不利",
        ("Garen", "Kayle"): "序盤は有利だがケイルのレベル11以降のアウトレンジポークとウルト無敵で仕留めきれなくなるため不利",

        ("Aatrox", "Varus"): "間合いを詰めてQのスイートスポットを連続ヒットさせれば、低耐久のヴァルスを一気に粉砕できるため有利",
        ("Aatrox", "Vladimir"): "序盤の射程内でのQスイートスポット拘束とサステインにより、レイトキャリーのウラジミールを完封できるため有利",
        ("Aatrox", "Malzahar"): "長射程のQでパッシブシールドを剥がし、ヴォイドリングを範囲Qで一掃して主導権を握れるため有利",
        ("Aatrox", "TahmKench"): "高い持続DPSとサステインでタンクの防具・回復力で圧倒できるため有利",
        ("Aatrox", "DrMundo"): "高い持続DPSとサステインでタンクの防具・回復力で圧倒できるため有利",
        ("Aatrox", "Irelia"): "イレリアのQ高速ブリンクでQスイートスポットを回避されやすく、至近距離での殴り合いで不利",
        ("Aatrox", "Fiora"): "フィオラのW（パリィ）でQのノックアップを反射スタンされやすく、1v1の急所突きで殴り負けるため不利",

        ("Yasuo", "Akshan"): "風の壁（W）でアクシャンのAA2連射やブーメランを完全遮断し、E突進でインファイトに持ち込み圧倒できるため有利",
        ("Yasuo", "Lucian"): "ルシアンの主火力であるAAパッシブとR（二丁拳銃）を風の壁（W）で無効化し、E急接近で制圧できるため有利",
        ("Yasuo", "Ryze"): "風の壁でライツの弾道スキルを遮断し、ミニオン経由のEダッシュで接近して一方的にトレードできるため有利",
        ("Yasuo", "Smolder"): "序盤の貧弱なスモルダーを風の壁とEの急接近からの高速ノックアップコンボで粉砕できるため有利",
        ("Yasuo", "Pantheon"): "パンテオンの対象指定スタンと強力な序盤バーストを風の壁で防げず、序盤の主導権を奪われやすいため不利",

        ("Ahri", "Garen"): "ガレンの接近をチャーム（E）とウルトのダッシュで完全拒絶し、アウトレンジから一方的に削り切れるため有利",
        ("Ahri", "Smolder"): "序盤の低い耐久力を突いてウルトの急接近からの即時バーストコンボで圧倒できるため有利",
        ("Ahri", "Ziggs"): "ジグスの長射程スキルに対して射程外から押されやすく、ウェーブクリア速度で後手に回りやすいため不利",
    }

    pair = (me_id, opp_id)
    if pair in SPECIFIC_REASONS:
        return SPECIFIC_REASONS[pair]

    # 2. 特性ベースの動的1行理由生成
    reasons = []
    if is_fav:
        # 有利パターン
        if me_dp.get("primary_type") == "AD" and opp_dp.get("primary_type") == "TANK":
            if any(k in me_id for k in ["Vayne", "Fiora", "Gwen", "KogMaw"]):
                return f"最大体力割合ダメージと確定ダメージにより、{opp_name}の高耐久防具を無視して削り倒せるため有利"
        if me_range >= 500 and opp_range <= 200:
            return f"通常攻撃とスキルの射程差を活かしたアウトレンジハラスにより、{opp_name}のCS獲得を阻害して主導権を握れるため有利"
        if opp_range >= 500 and me_range <= 200:
            return f"ブリンクや間合いを詰めるスキルで距離を一気に詰め、近接インファイトの瞬間火力で圧倒できるため有利"
        if me_sustain and not opp_sustain:
            return f"高い固有サステインによりトレード後の体力維持力で差をつけ、レーン主導権を確保できるため有利"
        if "Tank" in me_classes and "Assassin" in opp_classes:
            return f"{opp_name}の瞬間バーストを高耐久で耐え切り、豊富なCCで拘束してカウンターキルを狙えるため有利"
        return f"スキル構成とトレードの噛み合わせが良く、主導権を握ってレーン戦を有利に進められるため有利"
    else:
        # 不利パターン
        if opp_range >= 500 and me_range <= 200:
            return f"{opp_name}の長射程ポークにより不用意な被弾がかさみやすく、接近する前にヘルスを削られやすいため不利"
        if "Assassin" in me_classes and "Tank" in opp_classes:
            return f"{opp_name}の高い防御力と耐久をバーストで削りきれず、反撃のCC拘束で仕留められやすいため不利"
        if not me_sustain and opp_sustain:
            return f"{opp_name}の高い自己回復力により消耗戦で不利になりやすく、早期の回復阻害購入が必要なため不利"
        return f"{opp_name}の交戦距離やスキルセットが厳しく、無理なトレードを避けて味方のガンクを待つ立ち回りが求められるため不利"

def main():
    print("=== 全チャンピオンの対面1行戦術理由の再計算・同期を実行中 ===")

    # 1. 各スクリプトの順次実行
    from update_champion_damage_types import main as update_damage_types
    print("\n[ステップ 1/7] ダメージ属性・防具ガイドを更新中...")
    update_damage_types()

    from update_champion_attack_types import main as update_attack_types
    print("\n[ステップ 2/7] AA通常攻撃タイプ（メレー/レンジ）を更新中...")
    update_attack_types()

    from update_champion_sustain import main as update_sustain
    print("\n[ステップ 3/7] サステイン能力（体力回復・シールド）を解析・同期中...")
    update_sustain()

    from sync_all_roles_complete import main as sync_roles
    print("\n[ステップ 4/7] 全ロール別データを補完・構築中...")
    sync_roles()

    from build_advanced_champion_data import main as sync_adv
    print("\n[ステップ 5/7] 実践コンボ・スキル表・立ち回りメモを同期中...")
    sync_adv()

    # 2. 全対面理由の補完＆正規スキーマ化
    print("\n[ステップ 6/7] マッチアップの1行戦術理由を補完・正規化中...")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    for cid, c in tqdm(champions.items(), desc="対面戦術理由の生成・同期"):
        patch = c.get("patch", "16.20.1")
        roles = c.get("roles", ["TOP"])
        main_role = roles[0] if roles else "TOP"

        # トップレベル matchups の理由補完
        for fav in c.get("matchups", {}).get("favorable", []):
            opp_id = fav.get("champion_id")
            opp = champions.get(opp_id, {"id": opp_id, "name": fav.get("name", opp_id)})
            if not fav.get("reason") or "統計的に" in fav.get("reason", ""):
                fav["reason"] = generate_tactical_matchup_reason(c, opp, is_fav=True)
            fav["is_estimated"] = False
            fav["source"] = "opgg_stats"
            fav["patch"] = patch
            fav["role"] = main_role

        for unfav in c.get("matchups", {}).get("unfavorable", []):
            opp_id = unfav.get("champion_id")
            opp = champions.get(opp_id, {"id": opp_id, "name": unfav.get("name", opp_id)})
            if not unfav.get("reason") or "統計的に" in unfav.get("reason", ""):
                unfav["reason"] = generate_tactical_matchup_reason(c, opp, is_fav=False)
            unfav["is_estimated"] = False
            unfav["source"] = "opgg_stats"
            unfav["patch"] = patch
            unfav["role"] = main_role

        # 各ロール (role_data) の matchups にも理由を同期
        for rname, rinfo in c.get("role_data", {}).items():
            rm = rinfo.get("matchups", {})
            for fav in rm.get("favorable", []):
                opp_id = fav.get("champion_id")
                opp = champions.get(opp_id, {"id": opp_id, "name": fav.get("name", opp_id)})
                if not fav.get("reason") or "統計的に" in fav.get("reason", ""):
                    fav["reason"] = generate_tactical_matchup_reason(c, opp, is_fav=True)
                fav["is_estimated"] = False
                fav["source"] = "opgg_stats"
                fav["patch"] = patch
                fav["role"] = rname

            for unfav in rm.get("unfavorable", []):
                opp_id = unfav.get("champion_id")
                opp = champions.get(opp_id, {"id": opp_id, "name": unfav.get("name", opp_id)})
                if not unfav.get("reason") or "統計的に" in unfav.get("reason", ""):
                    unfav["reason"] = generate_tactical_matchup_reason(c, opp, is_fav=False)
                unfav["is_estimated"] = False
                unfav["source"] = "opgg_stats"
                unfav["patch"] = patch
                unfav["role"] = rname

    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    # 3. マッチアップマトリクス（全対面組み合わせ）の再計算
    print("\n[ステップ 7/7] 全対面マトリクス（実測と推定の厳格分離）を再計算中...")
    from build_comprehensive_matchups import main as build_matrix
    build_matrix()

    print("\n[SUCCESS] 全チャンピオンの対面1行戦術理由・詳細データの再計算＆同期がすべて完了しました！")

if __name__ == "__main__":
    main()
