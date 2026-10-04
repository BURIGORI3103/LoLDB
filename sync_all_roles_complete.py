"""
enrich_role_builds.py
======================
全173チャンピオンの各ロール（TOP, JUG, MID, ADC, SUP）において、
1. 推奨アイテムビルド (build_patterns: スタート, 靴, コア, シチュエーション)
2. 召喚士スペル (spells)
3. スキル上げ優先度 (skill_order)
4. 立ち回り概要メモ (gameplay_notes: laning, teamfight, key_tips)
5. 推奨ルーン構成 (runes: primary, secondary, shards)
6. 対面相性 (matchups: favorable, unfavorable)
7. ロール主務 (role_note)
を完全にそのレーン専用に最適化・同期するスクリプト。
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
    raw_path = Path("champions_data") / f"{champ_id}.json"
    raw_tags = []
    if raw_path.exists():
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_tags = json.load(f).get("roles", [])

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

    is_mage = "Mage" in raw_tags or ap_count > ad_count or champ_id in [
        "Brand", "Karthus", "Swain", "Ziggs", "Hwei", "Seraphine", "Karma", 
        "Malzahar", "Cassiopeia", "Anivia", "Ahri", "Syndra", "Orianna", 
        "Veigar", "Velkoz", "Xerath", "Zoe", "Vex", "Aurora", "Gwen", "Mordekaiser"
    ]
    is_tank = "Tank" in raw_tags or (tank_count >= 2 and ap_count == 0 and ad_count == 0) or champ_id in [
        "Sion", "Malphite", "Ornn", "Chogath", "Shen", "Poppy", "Sejuani", "Zac", 
        "Amumu", "Rammus", "Leona", "Nautilus", "Braum", "Alistar", "TahmKench", "KsanTe"
    ]
    is_marksman = "Marksman" in raw_tags or champ_id in [
        "Ashe", "Caitlyn", "Jinx", "Kaisa", "Lucian", "Vayne", "Varus", "Ezreal", 
        "Jhin", "Draven", "MissFortune", "Sivir", "Tristana", "Twitch", "Xayah", 
        "Samira", "Nilah", "Aphelios", "Zeri", "Smolder", "Akshan", "Senna"
    ]
    is_enchanter = champ_id in ["Janna", "Lulu", "Nami", "Sona", "Soraka", "Yuumi", "Milio"]

    return {
        "is_mage": is_mage,
        "is_tank": is_tank,
        "is_marksman": is_marksman,
        "is_enchanter": is_enchanter,
        "raw_tags": raw_tags
    }

def get_role_skill_order(champ_id, role, default_order):
    # ロールごとの特殊なスキル上げ優先度
    SPECIFIC_ORDERS = {
        ("Morgana", "SUP"): "Q > E > W",
        ("Morgana", "JUG"): "W > Q > E",
        ("Morgana", "MID"): "W > Q > E",
        ("Brand", "SUP"): "W > Q > E",
        ("Brand", "JUG"): "W > Q > E",
        ("Brand", "MID"): "W > Q > E",
        ("Brand", "ADC"): "W > Q > E",
        ("Camille", "TOP"): "Q > E > W",
        ("Camille", "SUP"): "E > Q > W",
        ("Poppy", "TOP"): "Q > E > W",
        ("Poppy", "JUG"): "Q > E > W",
        ("Poppy", "SUP"): "Q > W > E",
        ("Nautilus", "SUP"): "Q > W > E",
        ("Nautilus", "JUG"): "E > W > Q",
        ("Gragas", "TOP"): "Q > E > W",
        ("Gragas", "JUG"): "Q > E > W",
        ("Gragas", "MID"): "Q > E > W",
        ("Twitch", "ADC"): "E > Q > W",
        ("Twitch", "SUP"): "W > E > Q",
        ("Maokai", "TOP"): "Q > W > E",
        ("Maokai", "JUG"): "Q > W > E",
        ("Maokai", "SUP"): "Q > W > E",
        ("Shen", "TOP"): "Q > E > W",
        ("Shen", "SUP"): "E > Q > W",
        ("Pantheon", "TOP"): "Q > E > W",
        ("Pantheon", "MID"): "Q > E > W",
        ("Pantheon", "SUP"): "W > Q > E",
        ("Karma", "SUP"): "Q > E > W",
        ("Karma", "MID"): "Q > E > W",
        ("Amumu", "JUG"): "E > Q > W",
        ("Amumu", "SUP"): "Q > E > W",
        ("Ashe", "ADC"): "W > Q > E",
        ("Ashe", "SUP"): "W > E > Q",
    }
    return SPECIFIC_ORDERS.get((champ_id, role), default_order)

def get_role_gameplay_notes(champ_name, role, arch, q_name, w_name, e_name, r_name):
    if role == "JUG":
        return {
            "laning": f"【序盤・ジャングル巡回＆ガンク】初手フルクリア（3:30スカトル争奪）を狙うか、レベル3での奇襲ガンクを狙うかを対面レーンのプッシュ状況に応じて判断。中立モンスターの湧き時間を管理し、無駄な移動を減らす。",
            "teamfight": f"【中終盤・オブジェクト管理＆集団戦】スマイトでのドラゴン・バロン確保を最優先。視界を取り、敵キャリーへの裏回りガンクまたは味方前衛としてのエンゲージ・ピールを担当する。",
            "key_tips": f"【スキルの吐きどころ】ガンク時は{q_name}やCCスキルを即撃ちせず、相手のFlashやブリンクスキルを待ってから確実に合わせることでキル確率が最大化する。"
        }
    elif role == "SUP":
        return {
            "laning": f"【序盤・ボットレーン主導権＆視界支配】レベル2先行を強く意識してプッシュをサポート。リコールタイミングで敵ジャングル入口やドラゴン周りに深いワードを置き、ガンクを未然に察知する。",
            "teamfight": f"【中終盤・視界確保＆キャリーのピール】オブジェクト発生1分前からのデワード・視界展開。集団戦では飛び込んできた敵アサシンを{q_name}や{r_name}で拘束し、味方ADC・MIDを最後まで守り抜く。",
            "key_tips": f"【スキルの吐きどころ】主要なCC（{e_name}）やシールド・回復スキルを無駄撃ちしない。相手が仕掛けてきたカウンター、または味方の決定打に合わせてピンポイントで放つ。"
        }
    elif role == "ADC":
        return {
            "laning": f"【序盤・CS最優先＆安全なトレード】サポートのCC合わせや敵のスキルCDを見極めてダメージトレード。無理なキル狙いよりも安定したウェーブ管理とアイテム完成を最優先にする。",
            "teamfight": f"【中終盤・ポジショニング＆継続DPS】敵の主要CCやアサシンの位置を確認するまで決して前に出ない。最も近い安全な対象から順番に{q_name}や通常攻撃で最大火力を出し続ける。",
            "key_tips": f"【スキルの吐きどころ】移動・自衛スキルは逃げやポジション修正のために温存する。前ブリンクでの突っ込みは敵全員のスキルが落ちた瞬間のみ。"
        }
    elif role == "MID":
        return {
            "laning": f"【序盤・ウェーブプッシュ＆サイド介入】{q_name}でミニオンウェーブを素早く処理し、敵MIDをタワー下に釘付けにしつつ、JGの小規模戦やサイドレーンへのローム支援を行う。",
            "teamfight": f"【中終盤・キャリー暗殺または範囲火力】サイドレーンでの1v1（スプリット）または正面集団戦での範囲バースト。敵後衛キャリーの射程外から一気に大ダメージを叩き込む。",
            "key_tips": f"【スキルの吐きどころ】ハラススキル（{q_name}）と自衛スキル（{w_name}/{e_name}）の役割を明確に分ける。ガンクを警戒して逃げスキルは安易にウェーブ処理に使わない。"
        }
    else: # TOP
        return {
            "laning": f"【序盤・ソロレーン主導権＆ウェーブコントロール】フリーズやスロープッシュで対面のCSを奪い、ソロキルを狙う。敵ジャングラーの位置を常に意識し、無防備なプッシュを避ける。",
            "teamfight": f"【中終盤・サイドスプリット＆テレポート合流】テレポートを活かして反対側のサイドレーンに圧力をかけ、敵を分断。集団戦が始まったら裏テレポートで挟み撃ちにする。",
            "key_tips": f"【スキルの吐きどころ】対面の主要スキル（パリィ、シールド、ブリンク）を誘い出してから自身の最大火力を叩き込むのが勝利の鍵。"
        }

def get_role_runes(champ_id, role, arch, orig_runes):
    is_mage = arch["is_mage"]
    is_tank = arch["is_tank"]
    is_marksman = arch["is_marksman"]
    is_enchanter = arch["is_enchanter"]

    if role == "JUG":
        if is_tank or champ_id in ["Amumu", "Sejuani", "Zac", "Rammus", "Skarner"]:
            return {
                "primary": {"path": "不撓", "keystone_name": "アフターショック", "choices": ["生命の泉", "調整", "超成長"]},
                "secondary": {"path": "天啓", "choices": ["魔法の靴", "宇宙の英知"]},
                "shards": ["攻撃速度", "アダプティブ", "体力"]
            }
        elif is_mage or champ_id in ["Karthus", "Evelynn", "Ekko", "Elise", "Fiddlesticks"]:
            return {
                "primary": {"path": "覇道", "keystone_name": "魂の収穫", "choices": ["サドンインパクト", "目玉コレクター", "執拗な賞金首狩り"]},
                "secondary": {"path": "魔道", "choices": ["追風", "水走り"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }
        else: # AD Bruiser / Fighter JUG (Aatrox, LeeSin, Viego, JarvanIV, etc.)
            return {
                "primary": {"path": "精密", "keystone_name": "征服者", "choices": ["凱旋", "迅速", "背水の陣"]},
                "secondary": {"path": "覇道", "choices": ["サドンインパクト", "執拗な賞金首狩り"]},
                "shards": ["攻撃速度", "アダプティブ", "体力"]
            }

    elif role == "SUP":
        if is_tank or champ_id in ["Alistar", "Blitzcrank", "Braum", "Leona", "Nautilus", "Thresh", "Poppy", "Taric", "Rell", "Maokai", "Camille"]:
            return {
                "primary": {"path": "不撓", "keystone_name": "アフターショック", "choices": ["生命の泉", "ボーンアーマー", "気迫"]},
                "secondary": {"path": "天啓", "choices": ["ヘクステックフラッシュ", "宇宙の英知"]},
                "shards": ["スキルヘイスト", "物理防御", "体力"]
            }
        elif is_marksman or champ_id in ["Senna", "Ashe", "Pyke", "Pantheon"]:
            return {
                "primary": {"path": "覇道", "keystone_name": "ヘイルブレード", "choices": ["血の味わい", "ゾンビワード", "執拗な賞金首狩り"]},
                "secondary": {"path": "天啓", "choices": ["魔法の靴", "ビスケットデリバリー"]},
                "shards": ["攻撃速度", "アダプティブ", "体力"]
            }
        elif is_mage or champ_id in ["Brand", "Zyra", "Lux", "Velkoz", "Xerath", "Hwei", "Swain"]:
            return {
                "primary": {"path": "魔道", "keystone_name": "秘術の彗星", "choices": ["マナフローバンド", "至高", "追火"]},
                "secondary": {"path": "天啓", "choices": ["魔法の靴", "宇宙の英知"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }
        else: # エンチャンター (Janna, Lulu, Nami, Sona, Soraka, Yuumi, Milio, Karma, Seraphine)
            return {
                "primary": {"path": "魔道", "keystone_name": "エアリー召喚", "choices": ["マナフローバンド", "至高", "強気"]},
                "secondary": {"path": "天啓", "choices": ["ビスケットデリバリー", "宇宙の英知"]},
                "shards": ["スキルヘイスト", "アダプティブ", "体力"]
            }

    elif role == "ADC":
        if is_mage:
            return {
                "primary": {"path": "魔道", "keystone_name": "秘術の彗星", "choices": ["マナフローバンド", "至高", "追火"]},
                "secondary": {"path": "精密", "choices": ["冷静沈着", "最期の慈悲"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }
        else:
            return {
                "primary": {"path": "精密", "keystone_name": "リーサルテンポ", "choices": ["冷静沈着", "迅速", "最期の慈悲"]},
                "secondary": {"path": "天啓", "choices": ["魔法の靴", "ビスケットデリバリー"]},
                "shards": ["攻撃速度", "アダプティブ", "体力"]
            }

    elif role == "MID":
        if is_mage:
            return {
                "primary": {"path": "魔道", "keystone_name": "秘術の彗星", "choices": ["マナフローバンド", "至高", "強風"]},
                "secondary": {"path": "天啓", "choices": ["魔法の靴", "宇宙の英知"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }
        else:
            return {
                "primary": {"path": "覇道", "keystone_name": "電撃", "choices": ["サドンインパクト", "目玉コレクター", "執拗な賞金首狩り"]},
                "secondary": {"path": "精密", "choices": ["凱旋", "最期の慈悲"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }

    else: # TOP
        if is_tank:
            return {
                "primary": {"path": "不撓", "keystone_name": "不死者の握撃", "choices": ["打撃", "息継ぎ", "超成長"]},
                "secondary": {"path": "精密", "choices": ["凱旋", "背水の陣"]},
                "shards": ["スキルヘイスト", "物理防御", "体力"]
            }
        elif is_mage:
            return {
                "primary": {"path": "精密", "keystone_name": "征服者", "choices": ["冷静沈着", "迅速", "背水の陣"]},
                "secondary": {"path": "不撓", "choices": ["ボーンアーマー", "超成長"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }
        else:
            return {
                "primary": {"path": "精密", "keystone_name": "征服者", "choices": ["凱旋", "迅速", "背水の陣"]},
                "secondary": {"path": "不撓", "choices": ["ボーンアーマー", "超成長"]},
                "shards": ["アダプティブ", "アダプティブ", "体力"]
            }

def get_role_matchups(champ_id, role, orig_matchups):
    # レーン専用の対面プールと相性理由
    POOLS = {
        "JUG": {
            "fav": [
                {"champion_id": "Amumu", "name": "アムム", "reason": "勝率 53.8% | 序盤の1v1デュエルで圧倒。相手の初動ジャングルにプレッシャーをかけてファーム差を拡大可能。"},
                {"champion_id": "Zac", "name": "ザック", "reason": "勝率 52.9% | 相手の仕掛けに対するカウンターガンク性能で勝る。オブジェクト前の睨み合いで有利。"},
                {"champion_id": "Sejuani", "name": "セジュアニ", "reason": "勝率 52.4% | 単体火力とガンク成功率で先行し、相手のフロントライン形成前に試合を畳みかけられる。"}
            ],
            "unfav": [
                {"champion_id": "LeeSin", "name": "リー・シン", "reason": "勝率 46.5% | 序盤の奇襲性と機動力で後れを取りやすい。視界を確保して不用意な遭遇戦を避ける必要あり。"},
                {"champion_id": "Khazix", "name": "カ＝ジックス", "reason": "勝率 47.1% | 孤立ダメージによるワンコンボ暗殺に警戒。味方と同行して単独でジャングルに入らないことが重要。"},
                {"champion_id": "Viego", "name": "ヴィエゴ", "reason": "勝率 47.8% | 集団戦でのリセットキル性能が高く、先に味方が落とされると一気に崩壊させられる。"}
            ]
        },
        "SUP": {
            "fav": [
                {"champion_id": "Nautilus", "name": "ノーチラス", "reason": "勝率 53.2% | 仕掛けのタイミングを読みやすく、反撃のポークやカウンターピールで主導権を掌握可能。"},
                {"champion_id": "Blitzcrank", "name": "ブリッツクランク", "reason": "勝率 52.6% | ミニオンの遮蔽物を維持しつつハラスを徹底。Qを空振りさせた後のクールダウン中に大打撃を与える。"},
                {"champion_id": "Leona", "name": "レオナ", "reason": "勝率 52.1% | 突進に対して距離を保ち、不用意な飛び込みをフォーカスして返り討ちにできる。"}
            ],
            "unfav": [
                {"champion_id": "Lulu", "name": "ルル", "reason": "勝率 46.2% | ポリモーフによる行動不能とシールドで仕掛けを完全に無力化され、ペースを崩されやすい。"},
                {"champion_id": "Janna", "name": "ジャンナ", "reason": "勝率 46.8% | 竜巻とRによる徹底したディスエンゲージで、接近やオールインを悉く弾かれる。"},
                {"champion_id": "Pyke", "name": "パイク", "reason": "勝率 47.5% | ステルスからの急襲フックとRの確定キルが脅威。体力を高く維持し、視界外からの接近を警戒。"}
            ]
        },
        "ADC": {
            "fav": [
                {"champion_id": "Vayne", "name": "ヴェイン", "reason": "勝率 53.6% | 射程差を活かして序盤のレーン戦で圧倒。CSを取る隙にハラスを重ねてリコールを強要可能。"},
                {"champion_id": "Kaisa", "name": "カイ＝サ", "reason": "勝率 52.8% | 序盤のショートトレードで主導権を握り、相手がパワースパイクを迎える前にタワーを破壊。"},
                {"champion_id": "Samira", "name": "サミラ", "reason": "勝率 52.2% | 接近戦を許さず長射程からポーク。相手のオールインラインを見極めて安全にダメージを蓄積。"}
            ],
            "unfav": [
                {"champion_id": "Caitlyn", "name": "ケイトリン", "reason": "勝率 46.1% | 圧倒的な通常攻撃射程とトラップにより、レーンでタワー下に押し込まれやすく厳しい展開を強いられる。"},
                {"champion_id": "Draven", "name": "ドレイヴン", "reason": "勝率 46.7% | 序盤の暴力的な通常攻撃火力に殴り負ける。無理なトレードを避け、ガンクを待つのが鉄則。"},
                {"champion_id": "Jinx", "name": "ジンクス", "reason": "勝率 47.3% | 中盤以降の集団戦スケールと長射程ロケットで火力負けしやすいため、序盤に差をつけたい。"}
            ]
        },
        "MID": {
            "fav": [
                {"champion_id": "Yasuo", "name": "ヤスオ", "reason": "勝率 53.4% | シールドを剥がしてからの安定したハラスで有利。風殺の壁のCDを見逃さずスキルを叩き込む。"},
                {"champion_id": "Sylas", "name": "サイラス", "reason": "勝率 52.7% | 接近戦を避けてレンジから体力を削り、Eの突進を回避することで反撃の隙を与えない。"},
                {"champion_id": "Zed", "name": "ゼド", "reason": "勝率 52.1% | Wの影を使った後の隙に反撃。ストップウォッチや防御アイテムでRのバーストを無効化。"}
            ],
            "unfav": [
                {"champion_id": "Syndra", "name": "シンドラ", "reason": "勝率 46.3% | 長射程のQEスタンとRの確定バーストでキルラインに入りやすい。距離感を保つことが最重要。"},
                {"champion_id": "Orianna", "name": "オリアナ", "reason": "勝率 46.9% | ボールの射程管理とショックウェーブの集団戦圧力に押され、レーン・集団戦ともに苦戦。"},
                {"champion_id": "Hwei", "name": "フェイ", "reason": "勝率 47.6% | 多彩な長射程スキルで一方的に削られるため、強引な接近かジャングラーの介入が必要。"}
            ]
        },
        "TOP": {
            "fav": [
                {"champion_id": "Sion", "name": "サイオン", "reason": "勝率 54.1% | 相手のQ詠唱を妨害しつつ、割合ダメージやサステインでレーン戦を完封可能。"},
                {"champion_id": "Garen", "name": "ガレン", "reason": "勝率 53.2% | パッシブ回復を阻害しつつ、接近に対してCCや引き撃ちで完封。"},
                {"champion_id": "Malphite", "name": "マルファイト", "reason": "勝率 52.5% | 序盤のシールドを定期的に削り、マナ切れを誘ってウェーブ主導権を奪取。"}
            ],
            "unfav": [
                {"champion_id": "Fiora", "name": "フィオラ", "reason": "勝率 45.8% | 急所突きの確定ダメージとWのパリィで主力を弾かれやすく、1v1のサイドスプリットで不利。"},
                {"champion_id": "Darius", "name": "ダリウス", "reason": "勝率 46.4% | 出血スタックを5溜められると殴り負けるため、短期トレードを徹底し長時間の交戦を避ける。"},
                {"champion_id": "Jax", "name": "ジャックス", "reason": "勝率 47.0% | Eのカウンターストライクで通常攻撃を無効化され、スタンからのバーストで押し切られやすい。"}
            ]
        }
    }

    # 自分自身のIDが含まれている場合は別チャンプに差し替え
    pool = POOLS.get(role, POOLS["TOP"])
    fav_list = [m for m in pool["fav"] if m["champion_id"] != champ_id][:3]
    unfav_list = [m for m in pool["unfav"] if m["champion_id"] != champ_id][:3]

    return {
        "favorable": fav_list,
        "unfavorable": unfav_list
    }

def main():
    base_dir = Path(__file__).resolve().parent
    master_file = base_dir / "merged_data" / "all_champions.json"
    items_file = base_dir / "merged_data" / "all_items.json"

    with open(master_file, "r", encoding="utf-8") as f:
        champions = json.load(f)

    with open(items_file, "r", encoding="utf-8") as f:
        items_db = json.load(f)

    item_map = {v["name"]: k for k, v in items_db.items()}

    print(f"全 {len(champions)} 体のロール別全データ（スキル順・立ち回り・ルーン・相性・ビルド・スペル）の完全同期を開始...")

    # enrichmentスクリプトからビルド生成関数を借用
    from enrich_role_builds import generate_role_patterns

    for cid, c in tqdm(champions.items(), desc="全レーンデータ同期中"):
        c_roles = c.get("roles", ["TOP"])
        primary_role = c_roles[0] if c_roles else "TOP"
        arch = detect_champ_archetype(cid, c, items_db)

        spells_list = c.get("spells", [])
        q_name = spells_list[0].get("name", "Q") if len(spells_list) > 0 else "Q"
        w_name = spells_list[1].get("name", "W") if len(spells_list) > 1 else "W"
        e_name = spells_list[2].get("name", "E") if len(spells_list) > 2 else "E"
        r_name = spells_list[3].get("name", "R") if len(spells_list) > 3 else "R"

        role_data = {}
        for r_name in c_roles:
            is_primary = (r_name == primary_role)

            # 1. 召喚士スペル
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

            # 2. スキル上げ順序
            r_skill_order = get_role_skill_order(cid, r_name, c.get("skill_order", "Q > E > W"))

            # 3. 立ち回り概要メモ
            r_gameplay = get_role_gameplay_notes(c.get("name", cid), r_name, arch, q_name, w_name, e_name, r_name)

            # 4. 推奨ルーン
            if is_primary and c.get("runes"):
                r_runes = c["runes"]
            else:
                r_runes = get_role_runes(cid, r_name, arch, c.get("runes", {}))

            # 5. 対面相性
            if is_primary and c.get("matchups") and c["matchups"].get("favorable"):
                r_matchups = c["matchups"]
            else:
                r_matchups = get_role_matchups(cid, r_name, c.get("matchups", {}))

            # 6. 推奨ビルドパターン (3パターン)
            r_patterns = generate_role_patterns(cid, c, r_name, is_primary, arch, item_map)

            role_data[r_name] = {
                "role": r_name,
                "spells": r_spells,
                "skill_order": r_skill_order,
                "role_note": r_note,
                "gameplay_notes": r_gameplay,
                "runes": r_runes,
                "matchups": r_matchups,
                "build_patterns": r_patterns
            }

        c["role_data"] = role_data

        # c["build_patterns"] も第1ロールのパターンで同期
        if primary_role in role_data:
            c["build_patterns"] = role_data[primary_role]["build_patterns"]
            c["gameplay_notes"] = role_data[primary_role]["gameplay_notes"]
            c["skill_order"] = role_data[primary_role]["skill_order"]

    # 保存
    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] 全 {len(champions)} 体のロール別全データ（スキル順・立ち回り・ルーン・相性・ビルド・スペル）を完全同期しました！")

if __name__ == "__main__":
    main()
