import json
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MERGED_JSON = BASE_DIR / "merged_data" / "all_champions.json"

# 全173チャンピオンの精密属性定義マスター
AP_MAGES = {
    'Ahri', 'Akali', 'Anivia', 'Annie', 'AurelionSol', 'Aurora', 'Azir', 'Brand', 'Cassiopeia',
    'Diana', 'Ekko', 'Elise', 'Evelynn', 'Fiddlesticks', 'Fizz', 'Galio', 'Gragas', 'Gwen',
    'Heimerdinger', 'Hwei', 'Karthus', 'Kassadin', 'Kennen', 'Leblanc', 'Lillia', 'Lissandra', 'Lux',
    'Malzahar', 'Mel', 'Mordekaiser', 'Morgana', 'Neeko', 'Nidalee', 'Orianna', 'Rumble', 'Ryze',
    'Singed', 'Swain', 'Sylas', 'Syndra', 'Taliyah', 'Teemo', 'TwistedFate', 'Veigar', 'Velkoz',
    'Vex', 'Viktor', 'Vladimir', 'Xerath', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
}

TANK_AP = {
    'Alistar', 'Amumu', 'Blitzcrank', 'Braum', 'Chogath', 'Leona', 'Malphite', 'Maokai', 'Nautilus',
    'Nunu', 'Ornn', 'Rakan', 'Rammus', 'Rell', 'Sejuani', 'Shen', 'TahmKench', 'Thresh', 'Zac'
}

TANK_AD = {
    'DrMundo', 'KSante', 'Poppy', 'Sion', 'Skarner'
}

ENCHANTER_SUPPORT = {
    'Bard', 'Ivern', 'Janna', 'Karma', 'Lulu', 'Milio', 'Nami', 'Renata', 'Seraphine', 'Sona', 'Soraka', 'Taric', 'Yuumi'
}

# AD/AP 両刀または複数ビルド型（重要チャンピオン個別解説付き）
DUAL_BUILD_MAP = {
    'Malphite': {
        'desc': '主流は【タンク型】（主魔法ダメージ）だが、【フルAPバースト型】も強力。対面がADならAR、APならMRを積む。',
        'has_dual': True
    },
    'Katarina': {
        'desc': '【フルAPバースト型】と【オンヒットADファイター型】（ボットRK/クラーケン）の2種が存在。相手の初手アイテムで防御選択を分ける。',
        'has_dual': True
    },
    'Varus': {
        'desc': '【AD脅威/オンヒット型】と【フルAP割合バースト型】（ナッシャー/リフトメーカー）が存在。AP型はWスタック破裂の魔法割合が超強力。',
        'has_dual': True
    },
    'Kayle': {
        'desc': '【APオンヒット型】が主流だが【ADクリティカル型】も存在。AP型はMR+HP、AD型はARで対策する。',
        'has_dual': True
    },
    'Twitch': {
        'desc': '【ADクリティカル型】が主流だが【AP毒バースト型】（クラウン/ラバドン）も存在。毒は確定ダメージだがスキルは魔法寄り。',
        'has_dual': True
    },
    'Volibear': {
        'desc': '【ADファイター/タンク型】と【APリフトメーカー・ナッシャー型】の2大ビルド。スキル自体のダメージも物理・魔法が混在。',
        'has_dual': True
    },
    'KogMaw': {
        'desc': '【ADオンヒットADC型】と【APポーク型(MID)】が存在。どちらの型でもWの最大HP割合魔法ダメージが強烈なためMRも有効。',
        'has_dual': True
    },
    'Shaco': {
        'desc': '【ADアサシン型】と【APトラップ・分身爆破型】が存在。AD型はAR、AP型はMR+オラクルレンズでボックス対策。',
        'has_dual': True
    },
    'Shyvana': {
        'desc': '【APブレス砲撃型】（超高火力魔法）と【ADオンヒットファイター型】が存在。AP型相手はMRが最優先。',
        'has_dual': True
    },
    'Udyr': {
        'desc': '【AP不死鳥タンク型】（主魔法）と【AD虎爪脅威型】（主物理）が存在。相手がR上げならMR、Q上げならARを積む。',
        'has_dual': True
    },
    'Kaisa': {
        'desc': '【ADオンヒット/クリティカル型】と【APポーク進化型】が存在。パッシブ破裂ダメージは魔法属性。',
        'has_dual': True
    },
    'Jax': {
        'desc': '【ADファイター】が主流だが、WとRパッシブの追加打撃は強烈な魔法ダメージ。AP特化バースト型も一部存在。',
        'has_dual': True
    },
    'Corki': {
        'desc': '通常攻撃は物理だがパッシブやスキルで確定ダメージ・魔法ダメージが複合。防御はARとMRのバランスが重要。',
        'has_dual': True
    },
    'Warwick': {
        'desc': 'ビルドはAD/タンクだが、Qとパッシブの吸血追加ダメージは魔法属性。ブランブル（重傷）に加えてMRも刺さる。',
        'has_dual': True
    },
    'Ezreal': {
        'desc': '基本はADポークだが、W/E/Rは高APスケール。物理と魔法の複合ポークに対処が必要。',
        'has_dual': True
    },
    'Chogath': {
        'desc': '【タンク型】と【フルAPバースト型】が存在。スキルダメージはすべて魔法で、Rは確定ダメージ。',
        'has_dual': True
    },
    'Yone': {
        'desc': 'AD主軸だが、パッシブでAA2打目が魔法ダメージ、E再発動が確定ダメージのハイブリッド。防具はARを軸にHPを積む。',
        'has_dual': True
    },
    'Smolder': {
        'desc': 'ADスケールだがスキルダメージは物理・魔法・処刑確定ダメージが複合。',
        'has_dual': True
    },
    'Zaahen': {
        'desc': 'AD/AP両方のアイテム適性を持つハイブリッドファイター。',
        'has_dual': True
    },
    'Yunara': {
        'desc': 'AD/AP適性を併せ持つ柔軟なビルドパターン対応チャンピオン。',
        'has_dual': True
    }
}

def get_damage_profile(champ_id, champ_data):
    # 1. 両刀・複数ビルド持ち判定
    if champ_id in DUAL_BUILD_MAP:
        info = DUAL_BUILD_MAP[champ_id]
        if champ_id == 'Malphite':
            primary = 'TANK'
            label = 'タンク (主魔法) / AP両型あり'
            badge_text = 'TANK / AP'
            badge_class = 'badge-hybrid'
            counter_def = 'MR (魔法耐性) または AR (対面がADなら)'
        elif champ_id in ['Volibear', 'Udyr']:
            primary = 'HYBRID'
            label = 'ハイブリッド (AD/AP/タンク両型)'
            badge_text = 'AD / AP'
            badge_class = 'badge-hybrid'
            counter_def = '相手の初手ビルドに応じてAR/MRを選択'
        elif champ_id in ['Warwick', 'Jax', 'Corki', 'Yone', 'Smolder', 'Ezreal']:
            primary = 'HYBRID'
            label = 'ハイブリッド (複合ダメージ)'
            badge_text = 'AD / AP'
            badge_class = 'badge-hybrid'
            counter_def = 'ARとMRの両立 ＆ 体力(HP)'
        else:
            primary = 'HYBRID'
            label = 'ハイブリッド (AD/AP両型あり)'
            badge_text = 'AD / AP'
            badge_class = 'badge-hybrid'
            counter_def = '相手の初手アイテムでARかMRを判断'

        return {
            'primary_type': primary,
            'label': label,
            'badge_text': badge_text,
            'badge_class': badge_class,
            'counter_defense': counter_def,
            'has_dual_build': True,
            'dual_build_desc': info['desc']
        }

    # 2. 純APメイジ/アサシン
    if champ_id in AP_MAGES:
        return {
            'primary_type': 'AP',
            'label': '魔法 (AP)',
            'badge_text': 'AP',
            'badge_class': 'badge-ap',
            'counter_defense': 'MR (魔法耐性) を積む',
            'has_dual_build': False,
            'dual_build_desc': ''
        }

    # 3. タンク（主魔法）
    if champ_id in TANK_AP:
        return {
            'primary_type': 'TANK',
            'label': 'タンク (主魔法ダメージ)',
            'badge_text': 'TANK',
            'badge_class': 'badge-tank',
            'counter_defense': 'MR (魔法耐性) ＆ 割合ダメージ/貫通',
            'has_dual_build': False,
            'dual_build_desc': ''
        }

    # 4. タンク（主物理）
    if champ_id in TANK_AD:
        return {
            'primary_type': 'TANK',
            'label': 'タンク (主物理ダメージ)',
            'badge_text': 'TANK',
            'badge_class': 'badge-tank',
            'counter_defense': 'AR (物理防御) ＆ 割合ダメージ/貫通',
            'has_dual_build': False,
            'dual_build_desc': ''
        }

    # 5. エンチャンターサポート
    if champ_id in ENCHANTER_SUPPORT:
        return {
            'primary_type': 'AP',
            'label': 'サポート (AP/支援)',
            'badge_text': 'AP',
            'badge_class': 'badge-ap',
            'counter_defense': 'MR (魔法耐性) を積む',
            'has_dual_build': False,
            'dual_build_desc': ''
        }

    # 6. 純AD
    return {
        'primary_type': 'AD',
        'label': '物理 (AD)',
        'badge_text': 'AD',
        'badge_class': 'badge-ad',
        'counter_defense': 'AR (物理防御) を積む',
        'has_dual_build': False,
        'dual_build_desc': ''
    }

def main():
    print("チャンピオンマスターデータ読み込み中...")
    with open(MERGED_JSON, "r", encoding="utf-8") as f:
        champions = json.load(f)

    print(f"全 {len(champions)} チャンピオンにダメージ属性と両刀プロファイルを適用中...")
    for cid, cdata in tqdm(champions.items(), desc="ダメージ属性更新"):
        profile = get_damage_profile(cid, cdata)
        cdata['damage_profile'] = profile

        # ビルドパターンの名称に [AD] / [AP] / [TANK] の接頭辞を美しく付与
        patterns = cdata.get('build_patterns', [])
        for bp in patterns:
            name = bp.get('name', '')
            # 既存の接頭辞を整理
            if not any(tag in name for tag in ['[AD]', '[AP]', '[TANK]', '[HYBRID]']):
                core_str = " ".join(bp.get('core', []))
                if profile['primary_type'] == 'AP' or '魔力' in name or 'AP' in name:
                    bp['name'] = f"[AP] {name}"
                elif profile['primary_type'] == 'TANK' or 'タンク' in name or '耐久' in name:
                    bp['name'] = f"[TANK] {name}"
                elif profile['primary_type'] == 'HYBRID' and ('AP' in name or '魔力' in name):
                    bp['name'] = f"[AP] {name}"
                elif profile['primary_type'] == 'HYBRID' and ('タンク' in name or '耐久' in name):
                    bp['name'] = f"[TANK] {name}"
                else:
                    bp['name'] = f"[AD] {name}"

    with open(MERGED_JSON, "w", encoding="utf-8") as f:
        json.dump(champions, f, ensure_ascii=False, indent=2)

    print(f"[SUCCESS] {len(champions)} 体のチャンピオンデータを更新しました: {MERGED_JSON}")

if __name__ == "__main__":
    main()
