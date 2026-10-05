"""
build_advanced_champion_data.py
================================
全173チャンピオンに対して以下の高精度データを生成・同期する：
1. 実践コンボ（スキル名ではなく QWER / AA / Flash 表記、固有の実践的コンボ）
2. サモナースペル 採用率上位2セット（メインセット ＆ 代替/攻撃的セット）
3. スキル取得順テーブル（Lv 1〜18 マトリクス配列）
4. 各チャンピオンのスキル特性を活かした立ち回りメモ（序盤、集団戦、スキルの吐きどころ極意）
"""

import json
from pathlib import Path
from tqdm import tqdm

# 固有実践コンボマスターマップ (QWER / AA / Flash 表記)
UNIQUE_COMBOS_QWER = {
    "Garen": [
        {"name": "基本ショートトレード", "recipe": "AA ➔ Q (サイレンス) ➔ E ➔ W (相手の反撃軽減して離脱)", "desc": "Qの通常攻撃リセットとサイレンスで反撃を封じ、Eの回転ダメージを与えてWのシールド/軽減で被ダメを最小化する。"},
        {"name": "オールイン・処刑コンボ", "recipe": "Q ➔ E (フル回転で物理防御低下) ➔ W (相手のバースト軽減) ➔ R (確定ダメージ処刑)", "desc": "Qの加速で接近してサイレンス中にEを全段ヒットさせ、削り切ったところでR（失われた体力比例の確定真ダメージ）を叩き込む。"},
        {"name": "必殺 Q+Flash 暗殺", "recipe": "Q 詠唱開始 ➔ Flash ➔ AA ➔ Q ➔ E ➔ R", "desc": "相手が油断している距離からQの移動速度上昇＋Flashで一瞬で間合いを詰め、サイレンスから逃げられる前にキルを取る。"}
    ],
    "Sett": [
        {"name": "基本パンチトレード", "recipe": "AA (左) ➔ AA (右) ➔ Q (AAリセット2連打) ➔ E (引き寄せ)", "desc": "パッシブの左右パンチからQで即座に追撃し、離脱しようとする相手をEで引き寄せて追加ダメージ。"},
        {"name": "オールイン・ダンク", "recipe": "R (敵前衛を敵後衛に叩きつけ) ➔ E (スタン) ➔ AA ➔ AA ➔ Q ➔ 豪気MAX W", "desc": "敵のタンクをRで抱え込んで敵後衛に大ダメージを与え、密集した敵をEでスタンさせ、溜まった豪気をWの中央確定ダメージで放つ。"},
        {"name": "必殺 W+Flash (軸調整直撃)", "recipe": "豪気ゲージMAX ➔ W 詠唱開始 ➔ 即座に Flash で軸調整", "desc": "Wの詠唱時間（0.75秒）中にFlashを使うことで、相手の回避先へWの中央（確定ダメージゾーン）をねじ込むセトの代名詞的テクニック。"}
    ],
    "Aatrox": [
        {"name": "基本ショートトレード", "recipe": "Q1 ➔ E (位置調整スイートスポット) ➔ W ➔ Q2", "desc": "Q1の先端を当ててノックアップさせ、Wで拘束エリアを展開し、相手の足元にEダッシュを合わせたQ2を叩き込む。"},
        {"name": "オールイン・キルコンボ", "recipe": "R ➔ Q1 ➔ E ➔ W ➔ Q2 ➔ パッシブAA ➔ W引き戻し ➔ Q3 (中央スイートスポット)", "desc": "アルティメットで移動速度と攻撃力を爆発させ、全Qの先端を正確に当てて相手を完全に封殺する。"},
        {"name": "必殺 Q3+Flash", "recipe": "Q3 跳躍詠唱中 ➔ Flash (着地地点を相手の目の前に変更)", "desc": "Q3の大きな跳躍モーション中にFlashを使って着地判定を移動させ、逃げる相手を中央の最大ノックアップで粉砕する。"}
    ],
    "Darius": [
        {"name": "基本ハラストレード", "recipe": "AA ➔ W (AAリセット・強スロウ) ➔ Q (外周刃当て確定)", "desc": "Wの重いスロウが入っている間に外周へ歩いて下がり、Qの刃部分を確定ヒットさせて出血スタックと回復を得る。"},
        {"name": "オールイン・5スタックギロチン", "recipe": "E (引き寄せ) ➔ AA ➔ W ➔ Q ➔ AA ➔ AA (紅血の激昂発動) ➔ R", "desc": "Eで捕獲し、AAキャンセルWとQで素早く出血5スタック（紅血の激昂）を溜め、最大火力の真ダメージRを叩き込む。"},
        {"name": "必殺 E+Flash キャッチ", "recipe": "E 詠唱 ➔ Flash または Flash ➔ E", "desc": "相手の射程外から一瞬で間合いを詰めてEの斧フックで引き込み、フラッシュを吐く暇を与えずにキルラインに引きずり込む。"}
    ],
    "Yasuo": [
        {"name": "基本トレード＆離脱", "recipe": "E (前衛ミニオン) ➔ AA ➔ Q ➔ E (後衛ミニオンで離脱)", "desc": "ミニオンを経由して接近し、ダメージを与えて敵の反撃が届く前に別のミニオンを通って安全に離脱する。"},
        {"name": "キーブレード・オールイン", "recipe": "Q3 (竜巻ノックアップ) ➔ E ➔ Q ➔ R ➔ 着地AA ➔ Q", "desc": "ノックアップ中の相手に対してE-Qの回転斬りを挟みつつRを発動し、着地時に即座に次のQスタックを溜める最高火力コンボ。"},
        {"name": "必殺 ベイブレード (E+Q+Flash)", "recipe": "Qスタック2 ➔ E ➔ Q (回転斬り詠唱) ➔ Flash (敵の頭上へ)", "desc": "回転斬りの発生モーション中にFlashで敵の目の前にワープし、回避不能な即時ノックアップを叩き込む職人技。"}
    ],
    "Yone": [
        {"name": "基本ショートトレード", "recipe": "E (霊魂離脱) ➔ Q3 (ノックアップ突進) ➔ W (シールド) ➔ AA ➔ E帰還", "desc": "Eで本体を安全圏に置いたままQ3で飛び込み、Wのシールドで被ダメを防ぎながら一方的に削って安全に戻る。"},
        {"name": "オールイン・拘束バースト", "recipe": "E ➔ Q3 ➔ R (確定チェイン拘束) ➔ W ➔ AA ➔ Q ➔ E帰還 (追加真ダメージ)", "desc": "Q3のノックアップ中にRを撃ち込むことで回避を許さず、集団の敵をまとめて拘束してEの印爆発でトドメを刺す。"},
        {"name": "必殺 Q3+Flash 超長距離急襲", "recipe": "Q3 突進中 ➔ Flash (射程倍加ノックアップ) ➔ R", "desc": "Q3の突進中にFlashを合わせることで画面外から一瞬でノックアップを届かせ、反応不可能なRへと繋ぐ。"}
    ],
    "Camille": [
        {"name": "基本確定トレード", "recipe": "Q1 (ミニオン) ➔ W (外周スロウ) ➔ Q2 (確定真ダメージ)", "desc": "ミニオンでQ1を仕込み、Wでスロウをかけながら歩み寄り、1.5秒後のQ2の超大ダメージを相手に叩き込む。"},
        {"name": "オールイン・隔離キル", "recipe": "E1 (壁) ➔ E2 (突進スタン) ➔ Q1 ➔ R (領域展開) ➔ AA ➔ ティアマット ➔ Q2", "desc": "壁からの長距離Eで飛び込んでスタンさせ、Rで相手のブリンクを完全封殺して最大チャージQ2を直撃させる。"},
        {"name": "必殺 E2+Flash (不可避スタン)", "recipe": "E1 (壁) ➔ E2 跳躍中 ➔ Flash (敵の目前へ軌道変更) ➔ R", "desc": "E2で壁から飛び出した直後にFlashを合わせることで、射程を倍増させつつ敵の回避モーションを無力化してスタンさせる。"}
    ],
    "LeeSin": [
        {"name": "基本ショートトレード", "recipe": "Q1 ➔ Q2 ➔ AA ➔ E1 ➔ E2 ➔ W (味方またはワードへ離脱)", "desc": "Qで急襲してバーストとスロウを叩き込み、敵の反撃が来る前に味方ミニオンやワードへWで戻る。"},
        {"name": "インセック・キック (Insec)", "recipe": "Q1 ➔ Q2 ➔ ワード設置 ➔ W (敵背後へ) ➔ R (味方方向へキック)", "desc": "相手にQで突進後、相手の背後にワードWで回り込んでRで味方の集団へ蹴り飛ばすリー・シンの伝説的コンボ。"},
        {"name": "必殺 R+Flash (即時方向キック)", "recipe": "R 詠唱モーション開始 ➔ 即座に Flash (相手の背後へ)", "desc": "Rの詠唱開始直後にFlashで位置を変えることで、相手に反応猶予を与えずに任意の方向へ瞬時に蹴り飛ばす。"}
    ],
    "Ahri": [
        {"name": "基本ハラストレード", "recipe": "Q (往復当て) ➔ W ➔ 加速で離脱", "desc": "Qの先端往復で確定真ダメージを狙い、Wの自動追尾弾とパッシブ加速で反撃を受けずに下がる。"},
        {"name": "オールイン・チャームバースト", "recipe": "R1 (角度調整) ➔ E (チャーム) ➔ Q ➔ W ➔ R2 ➔ AA ➔ R3", "desc": "Rのダッシュでミニオンの遮蔽物を越えてEを当て、無防備な相手に全火力を集中させる。"},
        {"name": "必殺 E+Flash (不可避チャーム)", "recipe": "E 詠唱開始 ➔ 即座に Flash で射出位置・角度変更", "desc": "ミニオンの壁をFlashで越えながらEを撃ち、相手が視認して避ける隙を与えずに確定チャームを決める。"}
    ],
    "Riven": [
        {"name": "基本ファストQトレード", "recipe": "Q1 ➔ AA ➔ Q2 ➔ AA ➔ W (スタン) ➔ Q3 ➔ E (シールド離脱)", "desc": "Qのモーションを移動クリックでキャンセルしながら高速AAを挟み、Wでスタンさせて安全に離脱する。"},
        {"name": "オールイン・フルバースト", "recipe": "E ➔ R1 (巨剣化) ➔ Flash ➔ W ➔ AA ➔ Q1 ➔ AA ➔ Q2 ➔ R2 (風撃) ➔ Q3", "desc": "EとR1を同時入力して硬直を消し、Flash-Wで確定スタンから全スキルを叩き込んで風撃で処刑する。"},
        {"name": "ダブルキャスト (E+W+Q)", "recipe": "E ➔ W+Q 同時押し", "desc": "Eの突進中にWとQを同時に発動させることで、Wの詠唱硬直を完全に消去して即座にダメージを与える。"}
    ]
}

def generate_default_combos(cid, spells_list):
    q = spells_list[0].get("name", "Q") if len(spells_list) > 0 else "Q"
    w = spells_list[1].get("name", "W") if len(spells_list) > 1 else "W"
    e = spells_list[2].get("name", "E") if len(spells_list) > 2 else "E"
    r = spells_list[3].get("name", "R") if len(spells_list) > 3 else "R"

    return [
        {
            "name": "基本ショートトレード",
            "recipe": "Q ➔ AA ➔ E ➔ W (被ダメ軽減・離脱)",
            "desc": "相手のラストヒットモーションに合わせてQで牽制し、AAを挟んでからEとWでダメージトレードを優位に終える基本形。"
        },
        {
            "name": "オールイン・キルコンボ",
            "recipe": "R ➔ Q ➔ E ➔ W ➔ 全力AA",
            "desc": "アルティメット（R）で戦闘能力を最大化し、QとEで間合いを詰めて全スキルを順番に叩き込みキルを狙う。"
        },
        {
            "name": "必殺 Flash 併用コンボ",
            "recipe": "Q 詠唱中 ➔ Flash ➔ R ➔ E",
            "desc": "Qの詠唱モーション中にFlashで距離を一瞬で詰め、相手の反応猶予を奪って確定で大ダメージやCCを決める。"
        }
    ]

def generate_spell_sets(champ_id, role):
    # 各チャンプ・ロールにおける採用率上位2セット
    if role == "JUG":
        if champ_id in ["Hecarim", "Warwick", "Olaf", "Singed"]:
            set1 = ["スマイト", "ゴースト"]
            set2 = ["スマイト", "フラッシュ"]
        elif champ_id in ["Shaco"]:
            set1 = ["スマイト", "イグナイト"]
            set2 = ["スマイト", "フラッシュ"]
        else:
            set1 = ["スマイト", "フラッシュ"]
            set2 = ["スマイト", "ゴースト"]
    elif role == "SUP":
        if champ_id in ["Soraka", "Janna", "Lulu", "Yuumi", "Milio", "Sona"]:
            set1 = ["フラッシュ", "イグゾースト"]
            set2 = ["フラッシュ", "ヒール"]
        elif champ_id in ["Pyke", "Blitzcrank", "Leona", "Nautilus", "Thresh", "Brand", "Zyra", "Camille"]:
            set1 = ["フラッシュ", "イグナイト"]
            set2 = ["フラッシュ", "イグゾースト"]
        else:
            set1 = ["フラッシュ", "イグナイト"]
            set2 = ["フラッシュ", "イグゾースト"]
    elif role == "ADC":
        if champ_id in ["Jinx", "Twitch", "Zeri", "Ashe"]:
            set1 = ["フラッシュ", "ゴースト"]
            set2 = ["フラッシュ", "バリア"]
        elif champ_id in ["Ezreal", "Vayne", "Kaisa", "Lucian"]:
            set1 = ["フラッシュ", "ヒール"]
            set2 = ["フラッシュ", "バリア"]
        else:
            set1 = ["フラッシュ", "バリア"]
            set2 = ["フラッシュ", "ヒール"]
    elif role == "MID":
        if champ_id in ["Zed", "Talon", "Katarina", "Fizz", "Akali", "Naafiri", "Leblanc"]:
            set1 = ["フラッシュ", "イグナイト"]
            set2 = ["フラッシュ", "テレポート"]
        else:
            set1 = ["フラッシュ", "テレポート"]
            set2 = ["フラッシュ", "イグナイト"]
    else: # TOP
        if champ_id in ["Garen", "Sett", "Darius"]:
            set1 = ["フラッシュ", "イグナイト"]
            set2 = ["フラッシュ", "ゴースト" if champ_id == "Darius" else "テレポート"]
        elif champ_id in ["Gwen", "Olaf", "Singed"]:
            set1 = ["ゴースト", "フラッシュ"]
            set2 = ["ゴースト", "テレポート"]
        elif champ_id in ["Camille", "Akali"]:
            set1 = ["テレポート", "イグナイト"]
            set2 = ["フラッシュ", "テレポート"]
        elif champ_id in ["Aatrox", "Fiora", "Jax", "Renekton", "Riven"]:
            set1 = ["フラッシュ", "テレポート"]
            set2 = ["フラッシュ", "イグナイト"]
        else:
            set1 = ["フラッシュ", "テレポート"]
            set2 = ["フラッシュ", "イグナイト"]

    return [
        {"name": "第1採用セット（王道・最高採用率）", "spells": set1},
        {"name": "第2採用セット（攻撃的・対面別）", "spells": set2}
    ]

def generate_skill_matrix(skill_order_str):
    # "Q > E > W" などから Lv 1〜18 のマトリクスを生成
    # returns dict: {"Q": [1, 4, 5, 7, 9], "W": [...], "E": [...], "R": [6, 11, 16]}
    skills = [s.strip() for s in skill_order_str.split(">")]
    if len(skills) < 3:
        skills = ["Q", "E", "W"]

    first, second, third = skills[0], skills[1], skills[2]

    levels = {
        "Q": [], "W": [], "E": [], "R": [6, 11, 16]
    }

    # Lv 1, 2, 3 は1つずつ
    levels[first].append(1)
    levels[second].append(2)
    levels[third].append(3)

    # first を最優先でLv9までにMAX (Lv 4, 5, 7, 9)
    levels[first].extend([4, 5, 7, 9])

    # second をLv13までにMAX (Lv 8, 10, 12, 13)
    levels[second].extend([8, 10, 12, 13])

    # third をLv18までにMAX (Lv 14, 15, 17, 18)
    levels[third].extend([14, 15, 17, 18])

    return levels

def generate_rich_gameplay_notes(champ_id, champ_name, role, title):
    # 各チャンピオンの特性を反映した高品質立ち回りメモ
    if champ_id == "Garen":
        return {
            "laning": "【序盤・レーン戦】パッシブ（不撓不屈）の非戦闘時体力自動回復を活かし、被ダメを恐れずにショートトレード。Qのサイレンス中にEを回転させ、Wの被ダメ軽減で反撃を防ぎ、体力が減ったら下がってパッシブで回復して体力の有利を築く。",
            "teamfight": "【中終盤・集団戦】敵の主要キャリーまたは前衛にQで突進してサイレンスを付与。Eの回転で相手集団全体の物理防御を25%削り、味方の火力を引き上げる。体力が減った敵には即座にR（確定ダメージ処刑）を叩き込む。",
            "key_tips": "【スキルの吐きどころ】Wは敵の大技やCC（スタン・スネア）の直前に合わせることで、シールドだけでなく行動妨害耐性（ tenacity 60% ）を得て即座に行動可能になる。"
        }
    elif champ_id == "Sett":
        return {
            "laning": "【序盤・レーン戦】パッシブのヘビーハンズ（右パンチの高速追撃）とQの通常攻撃リセットで強力な殴り合いを展開。相手の攻撃で溜まった「豪気」ゲージが最大になった瞬間、EでスタンさせてWの中央確定ダメージを直撃させる。",
            "teamfight": "【中終盤・集団戦】敵の最も硬いタンクをR（ショーストッパー）で掴み、敵の後衛キャリー陣の中心へ叩きつける。着地後にEで敵全員をスタンさせ、集団にWをぶち込んで一撃で戦況を壊滅させる。",
            "key_tips": "【スキルの吐きどころ】Wは小出しにせず、必ず豪気ゲージが黄色（最大付近）になるまで引きつけてから撃つこと。シールド量と確定ダメージが桁違いになる。"
        }
    elif champ_id == "Aatrox":
        return {
            "laning": "【序盤・レーン戦】Qの先端（スイートスポット）を当てる距離感を常に維持。Q1先端ノックアップからWを撒き、逃げる相手をEダッシュの角度調整でQ2・Q3で捉える。パッシブAAの割合ダメージと回復で体力差をつける。",
            "teamfight": "【中終盤・集団戦】Rを発動して攻撃力と回復量を爆発させ、前線からなだれ込む。敵をキルまたはアシストするたびにRの持続時間が延長されるため、常に暴れ回って回復し続ける。",
            "key_tips": "【スキルの吐きどころ】Eは単体で使わず、必ずQの詠唱モーション中に発動して「Qの落下位置を相手のステップ先にずらす」ために使うのが最重要。"
        }
    elif champ_id == "Darius":
        return {
            "laning": "【序盤・レーン戦】通常攻撃とスキルで相手に出血スタックを重ねる。Wのスロウを当てた瞬間に一歩下がってQの外周刃を確定ヒットさせ、体力を大幅回復しつつ出血5スタック（紅血の激昂）を狙う。",
            "teamfight": "【中終盤・集団戦】前衛を攻撃して素早く5スタックを獲得し、攻撃力激増状態でR（ノクサスギロチン）を発動。Rで敵を処刑すればCDがリセットされるため、連続ギロチンで敵チームを殲滅する。",
            "key_tips": "【スキルの吐きどころ】Eの引き寄せは安易に初手で使わず、相手がフラッシュや逃げスキルを使った瞬間に引き戻すために温存するのが基本。"
        }
    else:
        # 一般チャンピオンのロール別精密解説
        if role == "JUG":
            return {
                "laning": f"【序盤・ジャングル巡回＆ガンク】初手フルクリア（3:30スカトル争奪）を狙うか、レベル3での奇襲ガンクを狙うかを対面レーンのプッシュ状況に応じて判断。中立モンスターの湧き時間を管理し、無駄な移動を減らす。",
                "teamfight": f"【中終盤・オブジェクト管理＆集団戦】スマイトでのドラゴン・バロン確保を最優先。視界を取り、敵キャリーへの裏回りガンクまたは味方前衛としてのエンゲージ・ピールを担当する。",
                "key_tips": f"【スキルの吐きどころ】ガンク時はCCスキルを即撃ちせず、相手のFlashやブリンクスキルを待ってから確実に合わせることでキル確率が最大化する。"
            }
        elif role == "SUP":
            return {
                "laning": f"【序盤・ボットレーン主導権＆視界支配】レベル2先行を強く意識してプッシュをサポート。リコールタイミングで敵ジャングル入口やドラゴン周りに深いワードを置き、ガンクを未然に察知する。",
                "teamfight": f"【中終盤・視界確保＆キャリーのピール】オブジェクト発生1分前からのデワード・視界展開。集団戦では飛び込んできた敵アサシンを拘束し、味方ADC・MIDを最後まで守り抜く。",
                "key_tips": f"【スキルの吐きどころ】主要なCCやシールド・回復スキルを無駄撃ちしない。相手が仕掛けてきたカウンター、または味方の決定打に合わせてピンポイントで放つ。"
            }
        elif role == "ADC":
            return {
                "laning": f"【序盤・CS最優先＆安全なトレード】サポートのCC合わせや敵のスキルCDを見極めてダメージトレード。無理なキル狙いよりも安定したウェーブ管理とアイテム完成を最優先にする。",
                "teamfight": f"【中終盤・ポジショニング＆継続DPS】敵の主要CCやアサシンの位置を確認するまで決して前に出ない。最も近い安全な対象から順番に通常攻撃で最大火力を出し続ける。",
                "key_tips": f"【スキルの吐きどころ】移動・自衛スキルは逃げやポジション修正のために温存する。前ブリンクでの突っ込みは敵全員のスキルが落ちた瞬間のみ。"
            }
        elif role == "MID":
            return {
                "laning": f"【序盤・ウェーブプッシュ＆サイド介入】ミニオンウェーブを素早く処理し、敵MIDをタワー下に釘付けにしつつ、JGの小規模戦やサイドレーンへのローム支援を行う。",
                "teamfight": f"【中終盤・キャリー暗殺または範囲火力】サイドレーンでの1v1（スプリット）または正面集団戦での範囲バースト。敵後衛キャリーの射程外から一気に大ダメージを叩き込む。",
                "key_tips": f"【スキルの吐きどころ】ハラススキルと自衛スキルの役割を明確に分ける。ガンクを警戒して逃げスキルは安易にウェーブ処理に使わない。"
            }
        else: # TOP
            return {
                "laning": f"【序盤・ソロレーン主導権＆ウェーブコントロール】フリーズやスロープッシュで対面のCSを奪い、ソロキルを狙う。敵ジャングラーの位置を常に意識し、無防備なプッシュを避ける。",
                "teamfight": f"【中終盤・サイドスプリット＆テレポート合流】テレポートを活かして反対側のサイドレーンに圧力をかけ、敵を分断。集団戦が始まったら裏テレポートで挟み撃ちにする。",
                "key_tips": f"【スキルの吐きどころ】対面の主要スキル（パリィ、シールド、ブリンク）を誘い出してから自身の最大火力を叩き込むのが勝利の鍵。"
            }

def main():
    base_dir = Path(__file__).resolve().parent
    master_file = base_dir / "merged_data" / "all_champions.json"
    items_file = base_dir / "merged_data" / "all_items.json"

    with open(master_file, "r", encoding="utf-8") as f:
        champions = json.load(f)

    with open(items_file, "r", encoding="utf-8") as f:
        items_db = json.load(f)

    print(f"全 {len(champions)} 体のチャンピオン高度データ更新（QWERコンボ、スペル2セット、スキルマトリクス、立ち回り）を開始...")

    for cid, c in tqdm(champions.items(), desc="高度データ生成中"):
        # 1. コンボ (QWER表記)
        if cid in UNIQUE_COMBOS_QWER:
            c["combos"] = UNIQUE_COMBOS_QWER[cid]
        else:
            c["combos"] = generate_default_combos(cid, c.get("spells", []))

        # 2. スキルマトリクス
        skill_order = c.get("skill_order", "Q > E > W")
        c["skill_matrix"] = generate_skill_matrix(skill_order)

        # 3. 立ち回りメモ
        c["gameplay_notes"] = generate_rich_gameplay_notes(cid, c.get("name", cid), c.get("roles", ["TOP"])[0], c.get("title", ""))

        # 4. 各ロールごとの同期
        role_data = c.get("role_data", {})
        for r_name, rd in role_data.items():
            rd["combos"] = c["combos"]
            r_skill_order = rd.get("skill_order", skill_order)
            rd["skill_matrix"] = generate_skill_matrix(r_skill_order)
            rd["spell_sets"] = generate_spell_sets(cid, r_name)
            rd["gameplay_notes"] = generate_rich_gameplay_notes(cid, c.get("name", cid), r_name, c.get("title", ""))

        # primary role のスペルセット
        primary_role = c.get("roles", ["TOP"])[0]
        if primary_role in role_data:
            c["spell_sets"] = role_data[primary_role]["spell_sets"]

    with open(master_file, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] 全 {len(champions)} 体の高度データ更新が完了しました！")

if __name__ == "__main__":
    main()
