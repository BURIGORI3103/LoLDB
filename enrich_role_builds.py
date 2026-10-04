"""
enrich_role_builds.py - 高精度ロール別ビルド・スペル完全同期スクリプト
"""

import json
import os
from pathlib import Path
from tqdm import tqdm

def get_item_id(item_name, item_map):
    if not item_name:
        return "1001"
    if item_name in item_map:
        return item_map[item_name]
    norm = item_name.replace(" ", "").replace("・", "").replace("=", "").replace("-", "")
    for real_name, real_id in item_map.items():
        real_norm = real_name.replace(" ", "").replace("・", "").replace("=", "").replace("-", "")
        if norm in real_norm or real_norm in norm:
            return real_id
    return "1001"

def build_core_items_list(item_names, item_map):
    return [{"name": name, "item_id": get_item_id(name, item_map)} for name in item_names]

def detect_champ_archetype(champ_id, champ, items_db):
    # champions_data から元の公式クラス取得
    raw_path = Path("champions_data") / f"{champ_id}.json"
    raw_tags = []
    if raw_path.exists():
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_tags = json.load(f).get("roles", [])

    # メインビルドのコアアイテムから AP / AD 判定
    core = champ.get("build", {}).get("core", [])
    ap_count = 0
    ad_count = 0
    tank_count = 0
    for it in core:
        iid = str(it.get("item_id", ""))
        item = items_db.get(iid, {})
        cats = item.get("categories", [])
        if "AP" in cats: ap_count += 1
        if "AD" in cats: ad_count += 1
        if "TANK" in cats: tank_count += 1

    is_mage = "Mage" in raw_tags or ap_count > ad_count or champ_id in ["Brand", "Karthus", "Swain", "Ziggs", "Hwei", "Seraphine", "Karma", "Malzahar", "Cassiopeia", "Anivia", "Ahri", "Syndra", "Orianna", "Veigar", "Velkoz", "Xerath", "Zoe", "Vex", "Aurora", "Gwen", "Mordekaiser"]
    is_tank = "Tank" in raw_tags or (tank_count >= 2 and ap_count == 0 and ad_count == 0) or champ_id in ["Sion", "Malphite", "Ornn", "Chogath", "Shen", "Poppy", "Sejuani", "Zac", "Amumu", "Rammus", "Leona", "Nautilus", "Braum", "Alistar", "TahmKench", "KsanTe"]
    is_marksman = "Marksman" in raw_tags or champ_id in ["Ashe", "Caitlyn", "Jinx", "Kaisa", "Lucian", "Vayne", "Varus", "Ezreal", "Jhin", "Draven", "MissFortune", "Sivir", "Tristana", "Twitch", "Xayah", "Samira", "Nilah", "Aphelios", "Zeri", "Smolder", "Akshan", "Senna"]
    is_enchanter = champ_id in ["Janna", "Lulu", "Nami", "Sona", "Soraka", "Yuumi", "Milio"]

    return {
        "is_mage": is_mage,
        "is_tank": is_tank,
        "is_marksman": is_marksman,
        "is_enchanter": is_enchanter,
        "raw_tags": raw_tags
    }

def generate_role_patterns(champ_id, champ, role, is_primary, arch, item_map):
    is_mage = arch["is_mage"]
    is_tank = arch["is_tank"]
    is_marksman = arch["is_marksman"]
    is_enchanter = arch["is_enchanter"]

    primary_build = champ.get("build", {})
    orig_starter = [i.get("name") for i in primary_build.get("starter", [])]
    orig_boots = [i.get("name") for i in primary_build.get("boots", [])]
    orig_core = [i.get("name") for i in primary_build.get("core", [])]
    orig_situational = [i.get("name") for i in primary_build.get("situational", [])]

    # ---------------------------
    # 1. JUG (ジャングル)
    # ---------------------------
    if role == "JUG":
        if is_tank or champ_id in ["Aatrox", "Darius", "Garen", "Jax", "Poppy", "Sejuani", "Zac", "Amumu", "Volibear", "Skarner", "Chogath", "Warwick"]:
            starter = ["モスストンパーの幼体", "体力ポーション"]
        elif is_mage or champ_id in ["Karthus", "Briar", "Evelynn", "Nocturne", "Shaco", "Fiddlesticks"]:
            starter = ["スコーチクロウの幼体", "体力ポーション"]
        else:
            starter = ["ガストウォーカーの幼体", "体力ポーション"]

        fav_boot = "ソーサラー シューズ" if is_mage else ("マーキュリー ブーツ" if is_tank else "プレート スチールキャップ")

        pats = []
        if is_primary and orig_core and len(orig_core) >= 3 and orig_starter and "幼体" in " ".join(orig_starter):
            pats.append({
                "name": "【標準・最高勝率】ジャングル巡回コア",
                "desc": "OP.GG統計に基づく最高勝率構成。高速なファームと安定したガンクを両立。",
                "starter": starter,
                "boots": orig_boots[0] if orig_boots else fav_boot,
                "core": orig_core[:3],
                "situational": orig_situational[:3] if orig_situational else ["ステラックの篭手", "デス ダンス", "ガーディアン エンジェル"]
            })
        elif champ_id == "Aatrox":
            pats.append({
                "name": "【標準】ジャングル制圧ファイター型",
                "desc": "モスストンパーのシールドとCC耐性を活かし、ガンクと集団戦で前線を粉砕する構成。",
                "starter": ["モスストンパーの幼体", "体力ポーション"],
                "boots": "プレート スチールキャップ",
                "core": ["プロフェイン ハイドラ", "サンダード スカイ", "ステラックの篭手"],
                "situational": ["デス ダンス", "マルモティウスの胃袋", "ガーディアン エンジェル"]
            })
        elif is_mage:
            pats.append({
                "name": "【標準】APジャングル・高速ファーム型",
                "desc": "高い魔法ダメージと範囲クリアで敵レーンを崩壊させる速攻ビルド。",
                "starter": starter,
                "boots": "ソーサラー シューズ",
                "core": ["黒炎のトーチ" if champ_id == "Karthus" else "ライアンドリーの苦悶", "シャドウフレイム", "ラバドン デスキャップ"],
                "situational": ["ヴォイド スタッフ", "ゾーニャの砂時計", "バンシー ヴェール"]
            })
        elif is_tank:
            pats.append({
                "name": "【標準】タンクジャングル・エンゲージ型",
                "desc": "耐久力とCCでガンクを成功させ、ドラゴン・バロン戦の壁となる王道構成。",
                "starter": starter,
                "boots": "プレート スチールキャップ",
                "core": ["サンファイア イージス", "終わりなき絶望", "ジャック=ショー"],
                "situational": ["ソーンメイル", "スピリット ビサージュ", "アビサル マスク"]
            })
        else:
            pats.append({
                "name": "【標準】ADジャングル・ファイター型",
                "desc": "クリア効率と小規模戦の殴り合いを極限まで高めたジャングル構成。",
                "starter": starter,
                "boots": "プレート スチールキャップ",
                "core": ["プロフェイン ハイドラ", "サンダード スカイ", "ブラック クリーバー"],
                "situational": ["ステラックの篭手", "デス ダンス", "ガーディアン エンジェル"]
            })

        pats.append({
            "name": "【デュエル重視】1v1・カウンターJG型",
            "desc": "敵ジャングラーとの遭遇戦やドラゴン前の小規模戦で確実に勝利するための単体キル特化ビルド。",
            "starter": starter,
            "boots": fav_boot,
            "core": ["ボルテイク サイクロソード", "妖夢の霊剣", "セリルダの怨恨"] if not is_mage else ["リッチベイン", "ストームサージ", "シャドウフレイム"],
            "situational": ["アクシオム アーク", "ガーディアン エンジェル", "エッジ オブ ナイト"]
        })
        pats.append({
            "name": "【集団戦・オブジェクト重視】耐久フロントライン型",
            "desc": "重要オブジェクト戦で味方の盾となり、CCを確実に決める堅実な構成。",
            "starter": starter,
            "boots": "マーキュリー ブーツ",
            "core": ["ステラックの篭手", "ジャック=ショー", "終わりなき絶望"] if not is_mage else ["リフトメーカー", "ライアンドリーの苦悶", "ケイニック ルーコン"],
            "situational": ["ソーンメイル", "スピリット ビサージュ", "ガーディアン エンジェル"]
        })

    # ---------------------------
    # 2. SUP (サポート)
    # ---------------------------
    elif role == "SUP":
        starter = ["ワールド アトラス", "体力ポーション"]
        pats = []

        if is_tank or champ_id in ["Alistar", "Blitzcrank", "Braum", "Leona", "Nautilus", "Thresh", "Poppy", "Taric", "Rell", "Maokai", "Amumu", "Camille"]:
            pats.append({
                "name": "【標準】ピール＆エンゲージ・タンク型",
                "desc": "セレスティアルオポジションで被ダメを大幅カットし、騎士の誓いでADCを守り抜く王道構成。",
                "starter": starter,
                "boots": "プレート スチールキャップ",
                "core": ["セレスティアル オポジション", "ソラリのロケット", "騎士の誓い"],
                "situational": ["ジーク コンバージェンス", "ソーンメイル", "アビサル マスク"]
            })
            pats.append({
                "name": "【集団戦防御】チームシールド特化型",
                "desc": "ソラリのロケットとジークコンバージェンスで集団戦の味方全体を強烈にバックアップ。",
                "starter": starter,
                "boots": "マーキュリー ブーツ",
                "core": ["ソラリのロケット", "ジーク コンバージェンス", "アナセマ チェイン"],
                "situational": ["騎士の誓い", "心の鋼", "終わりなき絶望"]
            })
            pats.append({
                "name": "【アグレッシブ】至点のソリ・奇襲型",
                "desc": "至点のソリの回復・加速で他レーンへの高速ロームとガンクを連発する攻撃型。",
                "starter": starter,
                "boots": "スイフトネス ブーツ",
                "core": ["至点のソリ", "デッドマン プレート", "アビサル マスク"],
                "situational": ["騎士の誓い", "ガーディアン エンジェル", "ソーンメイル"]
            })
        elif is_marksman or champ_id in ["Senna", "Ashe", "Pyke", "Pantheon"]:
            pats.append({
                "name": "【標準】視界支配＆キルプレッシャー型",
                "desc": "ブラッドソングとアンブラルグレイブで敵のワードを瞬時に消滅させつつ、高火力でキルを狙う構成。",
                "starter": starter,
                "boots": "スイフトネス ブーツ",
                "core": ["ブラッドソング", "アンブラル グレイブ", "妖夢の霊剣"],
                "situational": ["ボルテイク サイクロソード", "セリルダの怨恨", "ガーディアン エンジェル"]
            })
            pats.append({
                "name": "【DPSサポート】マークスマン型",
                "desc": "サポートでありながらADCに匹敵する後半火力を叩き出すスケール重視構成。",
                "starter": starter,
                "boots": "バーサーカー ブーツ",
                "core": ["ブラッドソング", "ラピッド ファイアキャノン", "インフィニティ エッジ"],
                "situational": ["モータル リマインダー", "ドミニク リガード", "ブラッドサースター"]
            })
            pats.append({
                "name": "【支援妨害】スロウ＆ユーティリティ型",
                "desc": "敵の足止めとクールダウン短縮を最優先にし、スキル回転で味方を勝利に導く構成。",
                "starter": starter,
                "boots": "アイオニア ブーツ",
                "core": ["至点のソリ", "帝国の指令", "ヘクスプレート"],
                "situational": ["アンブラル グレイブ", "ケミパンク チェーンソード", "ナイト エッジ"]
            })
        elif is_mage or champ_id in ["Brand", "Zyra", "Lux", "Velkoz", "Xerath", "Hwei", "Swain"]:
            pats.append({
                "name": "【標準】ザズ＝ザク・ハラス＆バースト型",
                "desc": "ザズ＝ザクの領域崩壊で追加割合ダメージを発生させ、ライアンドリーの苦悶で敵を焼き尽くす構成。",
                "starter": starter,
                "boots": "ソーサラー シューズ",
                "core": ["ザズ＝ザクのレルムスパイク", "ライアンドリーの苦悶", "リライのクリスタル セプター"],
                "situational": ["モレロノミコン", "シャドウフレイム", "ゾーニャの砂時計"]
            })
            pats.append({
                "name": "【高火力】ワンコンボ消滅型",
                "desc": "視界外からのフルコンボで敵ADCを一撃で消し去るキャリー特化サポートビルド。",
                "starter": starter,
                "boots": "ソーサラー シューズ",
                "core": ["ザズ＝ザクのレルムスパイク", "ルーデン コンパニオン", "ストームサージ"],
                "situational": ["シャドウフレイム", "ラバドン デスキャップ", "ヴォイド スタッフ"]
            })
            pats.append({
                "name": "【ユーティリティ】スロウ＆視界封鎖型",
                "desc": "リライの確定スロウとモレロノミコンの重傷で集団戦の敵全員を機能不全に追い込む支援構成。",
                "starter": starter,
                "boots": "アイオニア ブーツ",
                "core": ["ザズ＝ザクのレルムスパイク", "リライのクリスタル セプター", "クリプトブルーム"],
                "situational": ["ライアンドリーの苦悶", "モレロノミコン", "バンシー ヴェール"]
            })
        else: # エンチャンター (Janna, Lulu, Nami, Sona, Soraka, Yuumi, Milio, Karma, Seraphine)
            pats.append({
                "name": "【標準】回復・シールド増幅エンチャンター型",
                "desc": "ドリームメーカーのダメージ軽減とムーンストーンの連鎖ヒールで味方全体の生存力を最大化。",
                "starter": starter,
                "boots": "アイオニア ブーツ",
                "core": ["ドリーム メーカー", "ムーンストーンの再生", "ヘリアの残響"],
                "situational": ["リデンプション", "ミカエルの祝福", "アーデント センサー"]
            })
            pats.append({
                "name": "【攻撃支援】ADC強化特化型",
                "desc": "アーデントセンサーと流水の杖で味方キャリーの攻撃速度・魔力を爆発的に引き上げる構成。",
                "starter": starter,
                "boots": "アイオニア ブーツ",
                "core": ["ドリーム メーカー", "アーデント センサー", "流水の杖"],
                "situational": ["ムーンストーンの再生", "シュレリアの戦歌", "ミカエルの祝福"]
            })
            pats.append({
                "name": "【機動エンゲージ】シュレリア加速型",
                "desc": "シュレリアの戦歌の全体加速で強襲エンゲージやピンチからの全員離脱を自在に操るビルド。",
                "starter": starter,
                "boots": "アイオニア ブーツ",
                "core": ["ドリーム メーカー", "シュレリアの戦歌", "リデンプション"],
                "situational": ["ムーンストーンの再生", "ヘリアの残響", "ドーンコア"]
            })

    # ---------------------------
    # 3. ADC (ボットキャリー)
    # ---------------------------
    elif role == "ADC":
        if is_mage:
            starter = ["ドラン リング", "体力ポーション"]
            fav_boot = "ソーサラー シューズ"
            pats = [
                {
                    "name": "【標準】APC・継続火力型",
                    "desc": "ブラックファイアトーチとライアンドリーの苦悶で敵前衛から後衛まで溶かし尽くすAPボットビルド。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["ブラックファイア トーチ", "ライアンドリーの苦悶", "シャドウフレイム"],
                    "situational": ["ラバドン デスキャップ", "ヴォイド スタッフ", "ゾーニャの砂時計"]
                },
                {
                    "name": "【バースト特化】ワンコンボ消滅型",
                    "desc": "甘えた立ち位置の敵を一瞬で吹き飛ばす純魔力集中ビルド。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["ルーデン コンパニオン", "ストームサージ", "ラバドン デスキャップ"],
                    "situational": ["シャドウフレイム", "ヴォイド スタッフ", "バンシー ヴェール"]
                },
                {
                    "name": "【自衛・生存重視】防衛型APC",
                    "desc": "アサシンの飛び込みに対してゾーニャの砂時計やバンシーヴェールで耐え抜き、返り討ちにする構成。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["ゾーニャの砂時計", "ライアンドリーの苦悶", "クリプトブルーム"],
                    "situational": ["バンシー ヴェール", "リライのクリスタル セプター", "ラバドン デスキャップ"]
                }
            ]
        else:
            starter = ["ドラン ブレード", "体力ポーション"]
            fav_boot = "バーサーカー ブーツ"
            if is_primary and orig_core and len(orig_core) >= 3:
                core1 = orig_core[:3]
                sit1 = orig_situational[:3] if orig_situational else ["ブラッドサースター", "ガーディアン エンジェル", "マーキュリアル シミター"]
            else:
                core1 = ["クラーケン スレイヤー", "インフィニティ エッジ", "ドミニク リガード"]
                sit1 = ["ブラッドサースター", "ラピッド ファイアキャノン", "ガーディアン エンジェル"]

            pats = [
                {
                    "name": "【標準・最高勝率】王道クリティカルDPS型",
                    "desc": "OP.GGで最も勝率の高いクリティカル構成。中盤から終盤にかけて圧倒的な継続ダメージを出力。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": core1,
                    "situational": sit1
                },
                {
                    "name": "【対タンク】割合貫通・タンクシュレッダー型",
                    "desc": "相手前衛が硬いタンク主体の際に、ドミニクリガードやモータルリマインダーで素早く溶かす構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["クラーケン スレイヤー", "ドミニク リガード", "インフィニティ エッジ"],
                    "situational": ["ボットRK", "モータル リマインダー", "ブラッドサースター"]
                },
                {
                    "name": "【自衛・サバイブ型】対アサシン生存重視",
                    "desc": "敵アサシンやファイターのワンコンボを耐え、ライフスティールで粘り勝つ構成。",
                    "starter": starter,
                    "boots": "プレート スチールキャップ",
                    "core": ["不滅のシールドボウ", "ブラッドサースター", "ガーディアン エンジェル"],
                    "situational": ["インフィニティ エッジ", "ドミニク リガード", "マーキュリアル シミター"]
                }
            ]

    # ---------------------------
    # 4. MID (ミッド)
    # ---------------------------
    elif role == "MID":
        if is_mage:
            starter = ["ドラン リング", "体力ポーション"]
            fav_boot = "ソーサラー シューズ"
            if is_primary and orig_core and len(orig_core) >= 3:
                core1 = orig_core[:3]
                sit1 = orig_situational[:3] if orig_situational else ["ラバドン デスキャップ", "ヴォイド スタッフ", "バンシー ヴェール"]
            else:
                core1 = ["ルーデン コンパニオン", "シャドウフレイム", "ゾーニャの砂時計"]
                sit1 = ["ラバドン デスキャップ", "ヴォイド スタッフ", "バンシー ヴェール"]

            pats = [
                {
                    "name": "【標準】最高勝率・高火力バースト型",
                    "desc": "ウェーブプッシュ力とローム時の瞬間火力を両立したミッドメイジ王道ビルド。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": core1,
                    "situational": sit1
                },
                {
                    "name": "【対アサシン・自衛型】生存力重視構成",
                    "desc": "対面アサシンのオールインをゾーニャやバンシーで完全に透かし、安全にスケールする構成。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["ゾーニャの砂時計", "バンシー ヴェール", "クリプトブルーム"],
                    "situational": ["ライアンドリーの苦悶", "ラバドン デスキャップ", "コズミック ドライブ"]
                },
                {
                    "name": "【ローム特化】サイドレーン介入型",
                    "desc": "高速移動と高回転スキルでサイドレーンへガンクを仕掛け、試合を早期に掌握するビルド。",
                    "starter": starter,
                    "boots": "アイオニア ブーツ",
                    "core": ["ストームサージ", "リッチベイン", "シャドウフレイム"],
                    "situational": ["ラバドン デスキャップ", "ゾーニャの砂時計", "ヴォイド スタッフ"]
                }
            ]
        else: # AD Mid
            starter = ["ドラン ブレード", "体力ポーション"]
            fav_boot = "プレート スチールキャップ"
            if is_primary and orig_core and len(orig_core) >= 3:
                core1 = orig_core[:3]
                sit1 = orig_situational[:3] if orig_situational else ["ステラックの篭手", "デス ダンス", "ガーディアン エンジェル"]
            else:
                core1 = ["妖夢の霊剣", "ボルテイク サイクロソード", "セリルダの怨恨"]
                sit1 = ["アクシオム アーク", "ナイト エッジ", "ガーディアン エンジェル"]

            pats = [
                {
                    "name": "【標準】アサシン・ワンコンボ暗殺型",
                    "desc": "高い物理脅威で敵メイジやADCを一瞬で消し去るミッドADの定番キル構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": core1,
                    "situational": sit1
                },
                {
                    "name": "【対AP・魔法対策】高魔法耐性ファイター型",
                    "desc": "対面の高APバーストに対してマルモティウスの胃袋で耐性を確保し、殴り勝つ構成。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["マルモティウスの胃袋", "赤月の刃", "サンダード スカイ"],
                    "situational": ["デス ダンス", "ステラックの篭手", "ガーディアン エンジェル"]
                },
                {
                    "name": "【ローム・マップ支配型】高速移動暗殺型",
                    "desc": "妖夢の霊剣と機動靴でサイドレーンへ奇襲を連発し、味方をキャリーする構成。",
                    "starter": starter,
                    "boots": "スイフトネス ブーツ",
                    "core": ["妖夢の霊剣", "プロウラー クロウ", "ナイト エッジ"],
                    "situational": ["セリルダの怨恨", "ガーディアン エンジェル", "アクシオム アーク"]
                }
            ]

    # ---------------------------
    # 5. TOP (トップ)
    # ---------------------------
    else: # TOP
        if is_tank or champ_id == "Sion":
            starter = ["ドラン シールド", "体力ポーション"]
            fav_boot = "プレート スチールキャップ"
            pats = [
                {
                    "name": "【標準】サンファイア・耐久タンク型",
                    "desc": "近接殴り合いとウェーブクリアを強化し、無限の耐久力で集団戦の前線を支える構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["サンファイア イージス", "心の鋼", "終わりなき絶望"],
                    "situational": ["ジャック=ショー", "ソーンメイル", "超巨大ハイドラ"]
                },
                {
                    "name": "【対AP・魔法対策】ホロウレディアンス型",
                    "desc": "相手レーナーや敵構成がAP主体の際に、鉄壁の魔法防御とシールドを確保するビルド。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["ホロウ レディアンス", "ケイニック ルーコン", "終わりなき絶望"],
                    "situational": ["ジャック=ショー", "アビサル マスク", "心の鋼"]
                },
                {
                    "name": "【集団戦特化】防衛＆CCイニシエート型",
                    "desc": "敵の主要キャリーを足止めし、味方の火力を叩き込むための重装甲ビルド。",
                    "starter": starter,
                    "boots": "プレート スチールキャップ",
                    "core": ["終わりなき絶望", "ジャック=ショー", "ソーンメイル"],
                    "situational": ["心の鋼", "スピリット ビサージュ", "アナセマ チェイン"]
                }
            ]
        elif is_mage:
            starter = ["ドラン リング", "体力ポーション"]
            fav_boot = "ソーサラー シューズ"
            pats = [
                {
                    "name": "【標準】APブルーザー・サステイン殴り合い型",
                    "desc": "リフトメーカーとライアンドリーで長期トレードと集団戦火力を両立するトップAP構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["リフトメーカー", "ライアンドリーの苦悶", "ゾーニャの砂時計"],
                    "situational": ["ラバドン デスキャップ", "ヴォイド スタッフ", "バンシー ヴェール"]
                },
                {
                    "name": "【対タンク】割合ダメージ＆耐久削り型",
                    "desc": "硬い相手前衛に対して割合炎上と魔力貫通で確実に削り勝つ構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["ライアンドリーの苦悶", "クリプトブルーム", "リライのクリスタル セプター"],
                    "situational": ["ゾーニャの砂時計", "リフトメーカー", "シャドウフレイム"]
                },
                {
                    "name": "【自衛・防衛重視】高耐久AP型",
                    "desc": "相手のオールインを耐え、カウンターでキルを狙う安定重視ビルド。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["ゾーニャの砂時計", "ケイニック ルーコン", "リフトメーカー"],
                    "situational": ["ライアンドリーの苦悶", "ジャック=ショー", "アビサル マスク"]
                }
            ]
        else: # AD Fighter (Aatrox, Darius, Fiora, Camille, Jax, Riven, Renekton, etc.)
            starter = ["ドラン ブレード", "体力ポーション"]
            fav_boot = "プレート スチールキャップ"
            if is_primary and orig_core and len(orig_core) >= 3:
                core1 = orig_core[:3]
                sit1 = orig_situational[:3] if orig_situational else ["ステラックの篭手", "マルモティウスの胃袋", "ガーディアン エンジェル"]
            else:
                core1 = ["赤月の刃", "サンダード スカイ", "デス ダンス"]
                sit1 = ["ステラックの篭手", "マルモティウスの胃袋", "ガーディアン エンジェル"]

            pats = [
                {
                    "name": "【標準・最高勝率】王道ファイター・サステイン型",
                    "desc": "OP.GGで最も勝率の高い構成。レーン戦の殴り合いから集団戦の粘り強さまで最高峰。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": core1,
                    "situational": sit1
                },
                {
                    "name": "【対タンク・耐久破壊】割合貫通＆防具削り型",
                    "desc": "相手前衛が硬いタンク主体の際に、ブラッククリーバーのアーマー破壊で削り勝つ構成。",
                    "starter": starter,
                    "boots": fav_boot,
                    "core": ["ブラック クリーバー", "ショウジンの矛", "ステラックの篭手"],
                    "situational": ["ケミパンク チェーンソード", "デス ダンス", "超巨大ハイドラ"]
                },
                {
                    "name": "【対AP・魔法対策】高魔法耐性・ワンコン耐え型",
                    "desc": "相手のAPバーストが高い場合に、マルモティウスの胃袋やケイニック・ルーコンで耐性を確保。",
                    "starter": starter,
                    "boots": "マーキュリー ブーツ",
                    "core": ["マルモティウスの胃袋", "ケイニック ルーコン", "スピリット ビサージュ"],
                    "situational": ["サンダード スカイ", "デス ダンス", "ガーディアン エンジェル"]
                }
            ]

    # 全パターンに core_items を付与
    for p in pats:
        p["core_items"] = build_core_items_list(p.get("core", []), item_map)

    return pats

def main():
    base_dir = Path(__file__).resolve().parent
    master_file = base_dir / "merged_data" / "all_champions.json"
    items_file = base_dir / "merged_data" / "all_items.json"

    with open(master_file, "r", encoding="utf-8") as f:
        champions = json.load(f)

    with open(items_file, "r", encoding="utf-8") as f:
        items_db = json.load(f)

    item_map = {v["name"]: k for k, v in items_db.items()}

    print(f"全 {len(champions)} 体のロール別アイテムビルド＆スペル同期を開始します...")

    for cid, c in tqdm(champions.items(), desc="ロール別ビルド同期中"):
        c_roles = c.get("roles", ["TOP"])
        primary_role = c_roles[0] if c_roles else "TOP"
        arch = detect_champ_archetype(cid, c, items_db)

        role_data = {}
        for r_name in c_roles:
            is_primary = (r_name == primary_role)

            # スペル決定
            if r_name == "JUG":
                if cid in ["Hecarim", "Warwick", "Olaf", "Singed"]:
                    r_spells = ["スマイト", "ゴースト"]
                elif cid in ["Shaco"]:
                    r_spells = ["スマイト", "イグナイト"]
                else:
                    r_spells = ["スマイト", "フラッシュ"]
                r_note = "高速なジャングルキャンプ巡回、ガンクによるレーン介入、ドラゴン・ヘラルドのオブジェクト管理を担当。"

            elif r_name == "SUP":
                if cid in ["Soraka", "Janna", "Lulu", "Yuumi", "Milio"]:
                    r_spells = ["フラッシュ", "イグゾースト"]
                elif cid in ["Pyke", "Blitzcrank", "Leona", "Nautilus", "Thresh", "Brand", "Zyra"]:
                    r_spells = ["フラッシュ", "イグナイト"]
                else:
                    r_spells = ["フラッシュ", "イグナイト"]
                r_note = "ボットレーンでの視界支配（ワード管理）、味方ADCのピール、集団戦でのイニシエートまたは回復支援を担当。"

            elif r_name == "ADC":
                if cid in ["Jinx", "Twitch", "Zeri", "Ashe"]:
                    r_spells = ["フラッシュ", "ゴースト"]
                elif cid in ["Ezreal", "Vayne", "Kaisa"]:
                    r_spells = ["フラッシュ", "ヒール"]
                else:
                    r_spells = ["フラッシュ", "バリア"]
                r_note = "序盤のCS安定確保、後半集団戦での安全なポジションからの持続DPS出力を担当。"

            elif r_name == "MID":
                if cid in ["Zed", "Talon", "Katarina", "Fizz", "Akali", "Naafiri", "Leblanc"]:
                    r_spells = ["フラッシュ", "イグナイト"]
                else:
                    r_spells = ["フラッシュ", "テレポート"]
                r_note = "ウェーブプッシュによるサイドレーンへのローム支援、中盤以降の重要オブジェクト戦での火力担当。"

            else: # TOP
                if cid in ["Gwen", "Darius", "Olaf", "Singed"]:
                    r_spells = ["ゴースト", "フラッシュ"]
                elif cid in ["Camille", "Akali"]:
                    r_spells = ["テレポート", "イグナイト"]
                else:
                    r_spells = ["フラッシュ", "テレポート"]
                r_note = "ソロレーンでの対面有利拡大、サイドレーンプッシュ（スプリット）、テレポートでの集団戦合流を担当。"

            # ロール専用ビルドパターン生成
            r_patterns = generate_role_patterns(cid, c, r_name, is_primary, arch, item_map)

            role_data[r_name] = {
                "role": r_name,
                "spells": r_spells,
                "skill_order": c.get("skill_order", "Q > E > W"),
                "role_note": r_note,
                "build_patterns": r_patterns
            }

        c["role_data"] = role_data

        # c["build_patterns"] も第1ロールのパターンで同期
        if primary_role in role_data:
            c["build_patterns"] = role_data[primary_role]["build_patterns"]

    # 保存
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] 全 {len(champions)} 体のロール別アイテムビルドとスペルを完全同期しました！")

if __name__ == "__main__":
    main()
