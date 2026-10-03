"""
build_pwa.py - 統合マスターデータを内包したオフラインPWAアプリケーションの生成
================================================================================
merged_data/all_champions.json をインラインで内包し、
完全オフライン動作可能な単一HTML（dist/index.html）および
Service Worker（dist/sw.js）、PWAマニフェスト（dist/manifest.json）を構築します。
"""

import json
import os
from pathlib import Path

def build():
    base_dir = Path(__file__).resolve().parent
    master_file = base_dir / "merged_data" / "all_champions.json"
    dist_dir = base_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not master_file.exists():
        print(f"エラー: マスターデータファイル {master_file} が見つかりません。")
        return

    print("マスターデータを読み込み中...")
    with open(master_file, "r", encoding="utf-8") as f:
        all_champs = json.load(f)

    print(f"合計 {len(all_champs)} 体のチャンピオンデータを読み込みました。")

    # JSONをコンパクトにシリアライズ
    json_str = json.dumps(all_champs, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>LoLDB - League of Legends 攻略マスターデータベース</title>
  <meta name="theme-color" content="#0f172a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="description" content="全チャンピオンのスキル、推奨ビルド、ルーン、対面相性を完全網羅したオフライン対応攻略アプリ">
  <link rel="icon" type="image/png" href="icon.png">
  <link rel="apple-touch-icon" href="icon.png">
  <link rel="manifest" href="manifest.json">
  <style>
    :root {{
      --bg-base: #0b0f19;
      --bg-surface: #151d30;
      --bg-card: #1c2640;
      --bg-card-hover: #233152;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --accent: #f59e0b;
      --border: #2e3c5d;
      --favorable: #10b981;
      --unfavorable: #f43f5e;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      -webkit-font-smoothing: antialiased;
    }}
    header {{
      background: linear-gradient(180deg, #162035 0%, #0e1626 100%);
      border-bottom: 1px solid var(--border);
      padding: 12px 16px;
      position: sticky;
      top: 0;
      z-index: 40;
      box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    .header-container {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .logo-area {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .logo-badge {{
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      color: #fff;
      font-weight: 900;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 14px;
      letter-spacing: 1px;
    }}
    .app-title {{
      font-size: 18px;
      font-weight: 800;
      letter-spacing: 0.5px;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .patch-badge {{
      font-size: 11px;
      background: #1e293b;
      color: #38bdf8;
      border: 1px solid #334155;
      padding: 2px 8px;
      border-radius: 9999px;
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .search-input {{
      flex: 1;
      min-width: 180px;
      background-color: #0b0f19;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-input:focus {{
      border-color: var(--primary);
    }}
    .role-tabs {{
      display: flex;
      gap: 4px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .role-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }}
    .role-btn:hover {{
      background: #1c2640;
      color: #fff;
    }}
    .role-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }}
    main {{
      max-width: 1200px;
      width: 100%;
      margin: 0 auto;
      padding: 16px;
      flex: 1;
    }}
    .count-status {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 12px;
      font-weight: 500;
    }}
    .grid-container {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 12px;
    }}
    @media (min-width: 640px) {{
      .grid-container {{
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 16px;
      }}
    }}
    .champ-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
      display: flex;
      flex-direction: column;
    }}
    .champ-card:hover {{
      transform: translateY(-3px);
      border-color: var(--primary);
      box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    }}
    .champ-card-img-wrap {{
      width: 100%;
      aspect-ratio: 1;
      background: #0b0f19;
      position: relative;
      overflow: hidden;
    }}
    .champ-card-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .champ-card-img-placeholder {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 32px;
      color: #475569;
      background: #111827;
    }}
    .role-badge-list {{
      position: absolute;
      top: 6px;
      left: 6px;
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }}
    .mini-badge {{
      font-size: 9px;
      font-weight: 800;
      padding: 2px 5px;
      border-radius: 4px;
      text-transform: uppercase;
      color: #fff;
      box-shadow: 0 2px 4px rgba(0,0,0,0.6);
    }}
    .badge-top {{ background-color: #dc2626; }}
    .badge-jug {{ background-color: #16a34a; }}
    .badge-mid {{ background-color: #2563eb; }}
    .badge-adc {{ background-color: #eab308; color: #000; }}
    .badge-sup {{ background-color: #9333ea; }}
    .badge-default {{ background-color: #475569; }}
    .champ-info {{
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}
    .champ-name {{
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .champ-title {{
      font-size: 11px;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    /* モーダル */
    .modal-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.85);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 12px;
    }}
    .modal-overlay.open {{
      display: flex;
    }}
    .modal-content {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      width: 100%;
      max-width: 800px;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 40px rgba(0,0,0,0.7);
      display: flex;
      flex-direction: column;
      animation: modalSlide 0.2s ease-out;
    }}
    @keyframes modalSlide {{
      from {{ transform: scale(0.96) translateY(10px); opacity: 0; }}
      to {{ transform: scale(1) translateY(0); opacity: 1; }}
    }}
    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid var(--border);
      background: #111827;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .modal-title-wrap {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .modal-close-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 24px;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      line-height: 1;
    }}
    .modal-close-btn:hover {{
      color: #fff;
      background: #1f2937;
    }}
    .modal-body {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .detail-section {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
    }}
    .detail-heading {{
      font-size: 14px;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
      gap: 8px;
    }}
    .stat-box {{
      background: #101726;
      border: 1px solid #1e293b;
      padding: 8px;
      border-radius: 6px;
      font-size: 12px;
    }}
    .stat-label {{ color: var(--text-muted); font-size: 10px; margin-bottom: 2px; }}
    .stat-val {{ font-weight: 700; color: #fff; }}
    /* スキル */
    .skill-card {{
      display: flex;
      gap: 12px;
      padding: 10px;
      background: #101726;
      border-radius: 8px;
      margin-bottom: 8px;
      border: 1px solid #1e293b;
      align-items: flex-start;
    }}
    .skill-icon-wrap {{
      position: relative;
      width: 48px;
      height: 48px;
      border-radius: 8px;
      overflow: hidden;
      background: #0b0f19;
      flex-shrink: 0;
      border: 1px solid #334155;
    }}
    .skill-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .skill-slot-badge {{
      position: absolute;
      bottom: 0;
      right: 0;
      background: rgba(15, 23, 42, 0.9);
      color: #38bdf8;
      font-weight: 900;
      font-size: 11px;
      padding: 1px 4px;
      border-top-left-radius: 4px;
      border-left: 1px solid #0284c7;
      border-top: 1px solid #0284c7;
    }}
    .skill-content {{
      flex: 1;
    }}
    .skill-name {{
      font-weight: 700;
      font-size: 13px;
      margin-bottom: 4px;
      color: #fff;
    }}
    .skill-meta {{
      font-size: 11px;
      color: var(--accent);
      margin-bottom: 4px;
      font-weight: 600;
    }}
    .skill-desc {{
      font-size: 12px;
      color: #cbd5e1;
      line-height: 1.4;
    }}
    /* 相性カード */
    .matchups-container {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }}
    @media (min-width: 600px) {{
      .matchups-container {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    .matchup-col {{
      background: #101726;
      padding: 12px;
      border-radius: 8px;
      border: 1px solid #1e293b;
    }}
    .matchup-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid #1e293b;
      font-size: 12px;
    }}
    .matchup-item:last-child {{ border-bottom: none; }}
    .matchup-champ-info {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .matchup-champ-img {{
      width: 28px;
      height: 28px;
      border-radius: 50%;
      object-fit: cover;
      border: 1px solid #334155;
      background: #0b0f19;
      flex-shrink: 0;
    }}
    .matchup-champ-name {{
      font-weight: 600;
      color: #f1f5f9;
    }}
    .badge-fav {{ color: var(--favorable); font-weight: 700; }}
    .badge-unfav {{ color: var(--unfavorable); font-weight: 700; }}
    /* ビルド */
    .build-group {{
      margin-bottom: 12px;
    }}
    .build-group-title {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}
    .item-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .item-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid #1e293b;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      color: #e2e8f0;
      font-weight: 600;
    }}
    .item-img {{
      width: 24px;
      height: 24px;
      border-radius: 4px;
      object-fit: cover;
      flex-shrink: 0;
      border: 1px solid #334155;
    }}
    .item-step {{
      background: #0284c7;
      color: #fff;
      font-size: 10px;
      font-weight: 800;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }}
    .spell-img {{
      width: 20px;
      height: 20px;
      border-radius: 4px;
      object-fit: cover;
      border: 1px solid #334155;
    }}
    /* ルーン */
    .rune-row {{
      font-size: 12px;
      margin-bottom: 6px;
      color: #e2e8f0;
      line-height: 1.4;
    }}
    .rune-title {{
      font-weight: 700;
      color: var(--accent);
      margin-right: 6px;
    }}
    .spells-badge-list {{
      display: flex;
      gap: 8px;
      margin-top: 4px;
      flex-wrap: wrap;
    }}
    .spell-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid #38bdf8;
      color: #38bdf8;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-container">
      <div class="header-top">
        <div class="logo-area">
          <span class="logo-badge">PWA</span>
          <span class="app-title">LoLDB 攻略マスター</span>
          <span class="patch-badge" id="patchBadge">Patch 16.19 (v1.1.1 リッチ画像)</span>
        </div>
      </div>
      <div class="controls">
        <input type="text" id="searchInput" class="search-input" placeholder="チャンピオン名・英語名で検索..." autocomplete="off">
        <div class="role-tabs">
          <button class="role-btn active" data-role="ALL">ALL</button>
          <button class="role-btn" data-role="TOP">TOP</button>
          <button class="role-btn" data-role="JUG">JUG</button>
          <button class="role-btn" data-role="MID">MID</button>
          <button class="role-btn" data-role="ADC">ADC</button>
          <button class="role-btn" data-role="SUP">SUP</button>
        </div>
      </div>
    </div>
  </header>

  <main>
    <div class="count-status" id="countStatus">表示中: 0 体</div>
    <div class="grid-container" id="champGrid"></div>
  </main>

  <!-- 詳細モーダル -->
  <div class="modal-overlay" id="detailModal">
    <div class="modal-content">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 id="modalChampName" style="font-size: 18px; font-weight: 800;">チャンピオン名</h2>
          <span id="modalChampTitle" style="font-size: 12px; color: var(--text-muted);">二つ名</span>
        </div>
        <button class="modal-close-btn" id="modalCloseBtn">&times;</button>
      </div>
      <div class="modal-body" id="modalBody"></div>
    </div>
  </div>

  <script>
    // インライン内包されたマスターデータ
    const CHAMPIONS = {json_str};

    let currentRole = "ALL";
    let searchKeyword = "";

    const gridEl = document.getElementById("champGrid");
    const countStatusEl = document.getElementById("countStatus");
    const searchInput = document.getElementById("searchInput");
    const modalEl = document.getElementById("detailModal");
    const modalCloseBtn = document.getElementById("modalCloseBtn");
    const modalNameEl = document.getElementById("modalChampName");
    const modalTitleEl = document.getElementById("modalChampTitle");
    const modalBodyEl = document.getElementById("modalBody");

    function getRoleBadgeClass(role) {{
      switch(role) {{
        case "TOP": return "badge-top";
        case "JUG": return "badge-jug";
        case "MID": return "badge-mid";
        case "ADC": return "badge-adc";
        case "SUP": return "badge-sup";
        default: return "badge-default";
      }}
    }}

    function renderList() {{
      gridEl.innerHTML = "";
      const query = searchKeyword.trim().toLowerCase();
      let matched = 0;

      Object.values(CHAMPIONS).forEach(champ => {{
        // ロールフィルター
        if (currentRole !== "ALL") {{
          if (!champ.roles || !champ.roles.includes(currentRole)) return;
        }}

        // 検索クエリ
        if (query) {{
          const name = (champ.name || "").toLowerCase();
          const id = (champ.id || "").toLowerCase();
          const title = (champ.title || "").toLowerCase();
          if (!name.includes(query) && !id.includes(query) && !title.includes(query)) return;
        }}

        matched++;

        const card = document.createElement("div");
        card.className = "champ-card";
        card.onclick = () => openDetail(champ.id);

        const rolesHtml = (champ.roles || []).map(r => 
          `<span class="mini-badge ${{getRoleBadgeClass(r)}}">${{r}}</span>`
        ).join("");

        // Data Dragon公式CDNまたはフォールバック
        const patch = champ.patch || "16.19.1";
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{champ.id}}.png`;

        card.innerHTML = `
          <div class="champ-card-img-wrap">
            <img class="champ-card-img" src="${{imgUrl}}" alt="${{champ.name}}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
            <div class="champ-card-img-placeholder" style="display:none;">${{champ.name.charAt(0)}}</div>
            <div class="role-badge-list">${{rolesHtml}}</div>
          </div>
          <div class="champ-info">
            <div class="champ-name">${{champ.name}}</div>
            <div class="champ-title">${{champ.title || ""}}</div>
          </div>
        `;
        gridEl.appendChild(card);
      }});

      countStatusEl.textContent = `表示中: ${{matched}} 体 / 全 ${{Object.keys(CHAMPIONS).length}} 体`;
    }}

    function openDetail(champId) {{
      const c = CHAMPIONS[champId];
      if (!c) return;

      const patch = c.patch || "16.19.1";
      modalNameEl.textContent = c.name;
      modalTitleEl.textContent = `${{c.id}} - ${{c.title || ""}} (Patch ${{patch}})`;

      const SPELL_IMG_MAP = {{
        "フラッシュ": "SummonerFlash.png",
        "イグナイト": "SummonerDot.png",
        "テレポート": "SummonerTeleport.png",
        "スマイト": "SummonerSmite.png",
        "ヒール": "SummonerHeal.png",
        "バリア": "SummonerBarrier.png",
        "イグゾースト": "SummonerExhaust.png",
        "ゴースト": "SummonerHaste.png",
        "クレンズ": "SummonerBoost.png"
      }};

      const spellsBadge = (c.summoner_spells || []).map(s => {{
        const sImg = SPELL_IMG_MAP[s] || "SummonerFlash.png";
        const sUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/spell/${{sImg}}`;
        return `
          <span class="spell-pill">
            <img class="spell-img" src="${{sUrl}}" alt="${{s}}" onerror="this.style.display='none';">
            <span>${{s}}</span>
          </span>
        `;
      }}).join("") || "<span style='color:var(--text-muted); font-size:12px;'>標準スペル</span>";

      // スキル一覧
      let skillsHtml = "";
      if (c.abilities && c.abilities.length > 0) {{
        c.abilities.forEach(a => {{
          const pImg = a.image ? `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/passive/${{a.image}}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${{pImg}}" alt="${{a.name}}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">P</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${{a.name}}</div>
                <div class="skill-desc">${{a.description || ""}}</div>
              </div>
            </div>
          `;
        }});
      }}
      if (c.spells && c.spells.length > 0) {{
        c.spells.forEach(s => {{
          const spImg = s.image ? `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/spell/${{s.image}}` : "";
          skillsHtml += `
            <div class="skill-card">
              <div class="skill-icon-wrap">
                <img class="skill-img" src="${{spImg}}" alt="${{s.name}}" onerror="this.style.display='none';">
                <span class="skill-slot-badge">${{s.slot}}</span>
              </div>
              <div class="skill-content">
                <div class="skill-name">${{s.name}}</div>
                <div class="skill-meta">CD: ${{s.cooldown || "なし"}} | コスト: ${{s.cost || "0"}}</div>
                <div class="skill-desc">${{s.description || ""}}</div>
              </div>
            </div>
          `;
        }});
      }}

      // 相性
      let favHtml = "";
      if (c.matchups && c.matchups.favorable && c.matchups.favorable.length > 0) {{
        favHtml = c.matchups.favorable.map(m => {{
          const oppImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{m.champion_id}}.png`;
          return `
            <div class="matchup-item">
              <div class="matchup-champ-info">
                <img class="matchup-champ-img" src="${{oppImg}}" alt="${{m.name || m.champion_id}}" onerror="this.style.display='none';">
                <span class="matchup-champ-name">${{m.name || m.champion_id}}</span>
              </div>
              <span class="badge-fav">${{m.reason}}</span>
            </div>
          `;
        }}).join("");
      }} else {{
        favHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }}

      let unfavHtml = "";
      if (c.matchups && c.matchups.unfavorable && c.matchups.unfavorable.length > 0) {{
        unfavHtml = c.matchups.unfavorable.map(m => {{
          const oppImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{m.champion_id}}.png`;
          return `
            <div class="matchup-item">
              <div class="matchup-champ-info">
                <img class="matchup-champ-img" src="${{oppImg}}" alt="${{m.name || m.champion_id}}" onerror="this.style.display='none';">
                <span class="matchup-champ-name">${{m.name || m.champion_id}}</span>
              </div>
              <span class="badge-unfav">${{m.reason}}</span>
            </div>
          `;
        }}).join("");
      }} else {{
        unfavHtml = "<div style='color:var(--text-muted); font-size:12px; padding:6px 0;'>統計データなし</div>";
      }}

      // ビルド
      let starterItems = (c.build?.starter || []).map(i => {{
        const itemImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{i.item_id}}.png`;
        return `
          <span class="item-pill">
            <img class="item-img" src="${{itemImg}}" alt="${{i.name}}" onerror="this.style.display='none';">
            <span>${{i.name}}</span>
          </span>
        `;
      }}).join("") || "データなし";

      let bootsItems = (c.build?.boots || []).map(b => {{
        const bImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{b.item_id}}.png`;
        return `
          <span class="item-pill">
            <img class="item-img" src="${{bImg}}" alt="${{b.name}}" onerror="this.style.display='none';">
            <span>${{b.name}}</span>
          </span>
        `;
      }}).join("") || "データなし";

      let coreItems = (c.build?.core || []).map(i => {{
        const cImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{i.item_id}}.png`;
        return `
          <span class="item-pill">
            <span class="item-step">${{i.step}}</span>
            <img class="item-img" src="${{cImg}}" alt="${{i.name}}" onerror="this.style.display='none';">
            <span>${{i.name}}</span>
          </span>
        `;
      }}).join("") || "データなし";

      // ルーン
      const r = c.runes || {{}};
      const priChoices = (r.primary?.choices || []).join(" / ");
      const secChoices = (r.secondary?.choices || []).join(" / ");
      const shards = (r.shards || []).join(" / ");

      // 立ち回りメモ
      const laningNote = c.gameplay_notes?.laning || "相手のスキルクールダウンやミニオンウェーブの位置を注視してトレードを行う。";
      const tfNote = c.gameplay_notes?.teamfight || "集団戦では味方とフォーカスを合わせ、自身の役割を完遂する。";

      modalBodyEl.innerHTML = `
        <!-- 基本情報 & スペル -->
        <div class="detail-section">
          <div class="detail-heading">⚔️ 推奨サモナースペル & 運用レーン</div>
          <div class="spells-badge-list">${{spellsBadge}}</div>
        </div>

        <!-- 対面相性 (有利不利) -->
        <div class="detail-section">
          <div class="detail-heading">⚖️ 対面相性（OP.GG 統計勝率）</div>
          <div class="matchups-container">
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--favorable); margin-bottom:6px;">📈 有利な対面（おすすめ）</div>
              ${{favHtml}}
            </div>
            <div class="matchup-col">
              <div style="font-size:12px; font-weight:700; color:var(--unfavorable); margin-bottom:6px;">📉 不利な対面（警戒）</div>
              ${{unfavHtml}}
            </div>
          </div>
        </div>

        <!-- 推奨ビルド -->
        <div class="detail-section">
          <div class="detail-heading">🛡️ 推奨ビルド構成</div>
          <div class="build-group">
            <div class="build-group-title">スタートアイテム</div>
            <div class="item-tags">${{starterItems}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨靴</div>
            <div class="item-tags">${{bootsItems}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨コアアイテム（進行順）</div>
            <div class="item-tags">${{coreItems}}</div>
          </div>
        </div>

        <!-- ルーン構成 -->
        <div class="detail-section">
          <div class="detail-heading">🔮 推奨ルーン構成</div>
          <div class="rune-row"><span class="rune-title">メインパス [${{r.primary?.path || "精密"}}]:</span><strong>${{r.primary?.keystone_name || "征服者"}}</strong> (${{priChoices}})</div>
          <div class="rune-row"><span class="rune-title">サブパス [${{r.secondary?.path || "不撓"}}]:</span>${{secChoices}}</div>
          <div class="rune-row"><span class="rune-title">シャード:</span>${{shards}}</div>
        </div>

        <!-- 立ち回りメモ -->
        <div class="detail-section">
          <div class="detail-heading">📝 立ち回り概要メモ</div>
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【序盤・レーン戦】</strong> ${{laningNote}}</div>
          <div style="font-size:12px; color:#e2e8f0; line-height:1.5;"><strong>【中終盤・集団戦】</strong> ${{tfNote}}</div>
        </div>

        <!-- 全スキル詳細 -->
        <div class="detail-section">
          <div class="detail-heading">⚡ スキル詳細（Q・W・E・R・パッシブ）</div>
          ${{skillsHtml}}
        </div>
      `;

      modalEl.classList.add("open");
    }}

    modalCloseBtn.onclick = () => modalEl.classList.remove("open");
    modalEl.onclick = (e) => {{
      if (e.target === modalEl) modalEl.classList.remove("open");
    }};

    // 検索入力イベント
    searchInput.addEventListener("input", (e) => {{
      searchKeyword = e.target.value;
      renderList();
    }});

    // ロールタブ切り替え
    document.querySelectorAll(".role-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".role-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentRole = btn.getAttribute("data-role");
        renderList();
      }});
    }});

    // 初期レンダリング
    renderList();

    // Service Worker 登録（更新チェック付き）
    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', () => {{
        navigator.serviceWorker.register('sw.js')
          .then(reg => {{
            console.log('ServiceWorker registered:', reg.scope);
            reg.update();
          }})
          .catch(err => console.log('ServiceWorker registration failed:', err));
      }});
    }}
  </script>
</body>
</html>"""

    index_path = dist_dir / "index.html"
    print(f"単一HTML {index_path} を出力中...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Service Worker (sw.js) の生成
    sw_content = """// LoLDB Service Worker - Offline Cache v2
const CACHE_NAME = 'loldb-cache-v2';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Pre-caching offline assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        if (key !== CACHE_NAME) {
          console.log('[SW] Removing old cache', key);
          return caches.delete(key);
        }
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. メインHTML（ナビゲーション）は Network-First（オンライン時は最新、オフライン時はキャッシュ）
  if (event.request.mode === 'navigate' || url.pathname.endsWith('index.html') || url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match('./index.html') || caches.match('./');
        })
    );
    return;
  }

  // 2. その他の静的アセット（画像等）は Cache-First
  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) {
        return response;
      }
      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      });
    })
  );
});
"""
    sw_path = dist_dir / "sw.js"
    print(f"Service Worker {sw_path} を出力中...")
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)

    # PWA Manifest (manifest.json) の生成
    manifest_content = """{
  "name": "LoLDB - League of Legends 攻略マスター",
  "short_name": "LoLDB",
  "start_url": "./index.html",
  "display": "standalone",
  "background_color": "#0b0f19",
  "theme_color": "#0f172a",
  "orientation": "any",
  "icons": [
    {
      "src": "./icon.png",
      "sizes": "120x120",
      "type": "image/png"
    },
    {
      "src": "./icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
"""
    manifest_path = dist_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    html_size_kb = os.path.getsize(index_path) / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    build()
