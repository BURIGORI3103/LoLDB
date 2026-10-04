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
    items_file = base_dir / "merged_data" / "all_items.json"
    dist_dir = base_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    if not master_file.exists():
        print(f"エラー: マスターデータファイル {master_file} が見つかりません。")
        return

    print("マスターデータを読み込み中...")
    with open(master_file, "r", encoding="utf-8") as f:
        all_champs = json.load(f)

    all_items = {}
    if items_file.exists():
        print("アイテムデータを読み込み中...")
        with open(items_file, "r", encoding="utf-8") as f:
            all_items = json.load(f)
        print(f"合計 {len(all_items)} 件のアイテムデータを読み込みました。")

    print(f"合計 {len(all_champs)} 体のチャンピオンデータを読み込みました。")

    # JSONをコンパクトにシリアライズ
    json_str = json.dumps(all_champs, ensure_ascii=False)
    items_json_str = json.dumps(all_items, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>LoLDB</title>
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
      padding: 3px 10px;
      border-radius: 9999px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
    }}
    .patch-badge:hover {{
      background: #0284c7;
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
    }}
    .main-nav {{
      display: flex;
      gap: 8px;
      border-bottom: 1px solid #1e293b;
      padding-bottom: 8px;
    }}
    .nav-tab {{
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .nav-tab:hover {{
      color: #fff;
      background: rgba(255, 255, 255, 0.05);
    }}
    .nav-tab.active {{
      background: #1e293b;
      color: var(--primary);
      border-color: #334155;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
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
    /* リリースノートスタイル */
    .changelog-list {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .changelog-item {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .changelog-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      padding-bottom: 6px;
    }}
    .changelog-ver {{
      font-weight: 800;
      font-size: 14px;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .changelog-date {{
      font-size: 11px;
      color: var(--text-muted);
    }}
    .changelog-ul {{
      list-style-type: disc;
      padding-left: 20px;
      font-size: 12.5px;
      color: #cbd5e1;
      line-height: 1.6;
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
      flex-direction: column;
      gap: 6px;
      padding: 10px 0;
      border-bottom: 1px solid #1e293b;
    }}
    .matchup-item:last-child {{ border-bottom: none; }}
    .matchup-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
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
      font-weight: 700;
      font-size: 13px;
      color: #f1f5f9;
    }}
    .badge-fav {{
      color: var(--favorable);
      font-weight: 800;
      font-size: 12px;
      background: rgba(16, 185, 129, 0.12);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }}
    .badge-unfav {{
      color: var(--unfavorable);
      font-weight: 800;
      font-size: 12px;
      background: rgba(244, 63, 94, 0.12);
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid rgba(244, 63, 94, 0.3);
    }}
    .matchup-reason {{
      font-size: 11.5px;
      color: #cbd5e1;
      line-height: 1.45;
      background: #0b0f19;
      padding: 6px 10px;
      border-radius: 6px;
      border-left: 3px solid #38bdf8;
    }}
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
      cursor: pointer;
      transition: all 0.2s;
    }}
    .item-pill:hover {{
      border-color: var(--primary);
      background: #1e293b;
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.2);
    }}
    .item-img {{
      width: 24px;
      height: 24px;
      border-radius: 4px;
      object-fit: cover;
      flex-shrink: 0;
      border: 1px solid #334155;
    }}
    /* アイテム図鑑スタイル */
    .item-controls {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .item-controls-row {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .item-search-input {{
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
    .item-search-input:focus {{
      border-color: var(--primary);
    }}
    .item-sort-select {{
      background: #151d30;
      border: 1px solid var(--border);
      color: #fff;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      outline: none;
      cursor: pointer;
    }}
    .item-category-tabs {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 4px;
    }}
    .item-cat-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }}
    .item-cat-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .item-cat-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }}
    .items-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 12px;
    }}
    @media (min-width: 600px) {{
      .items-grid {{
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      }}
    }}
    .item-grid-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px 8px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
      text-align: center;
    }}
    .item-grid-card:hover {{
      transform: translateY(-3px);
      border-color: var(--primary);
      box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    }}
    .item-card-icon {{
      width: 48px;
      height: 48px;
      border-radius: 8px;
      object-fit: cover;
      border: 1px solid #334155;
      background: #0b0f19;
    }}
    .item-card-name {{
      font-size: 12px;
      font-weight: 700;
      color: #f1f5f9;
      line-height: 1.3;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 30px;
    }}
    .item-card-price {{
      font-size: 11px;
      font-weight: 800;
      color: var(--accent);
      background: rgba(245, 158, 11, 0.12);
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid rgba(245, 158, 11, 0.3);
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }}
    /* アイテム詳細モーダル */
    .item-detail-header-wrap {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .item-detail-big-icon {{
      width: 56px;
      height: 56px;
      border-radius: 10px;
      border: 2px solid var(--primary);
      object-fit: cover;
      background: #0b0f19;
      flex-shrink: 0;
    }}
    .recipe-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 6px;
    }}
    .recipe-item-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: #101726;
      border: 1px solid var(--border);
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 12px;
      color: #f1f5f9;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .recipe-item-pill:hover {{
      border-color: var(--primary);
      background: #1e293b;
    }}
    .recipe-item-pill img {{
      width: 20px;
      height: 20px;
      border-radius: 4px;
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
          <span class="app-title">LoLDB</span>
          <span class="patch-badge" id="patchBadge" title="タップして更新履歴を表示">Patch 16.19 / v1.5.0 ℹ️</span>
        </div>
      </div>
      <nav class="main-nav">
        <button class="nav-tab active" data-tab="champions">👑 チャンピオン</button>
        <button class="nav-tab" data-tab="items">🛡️ アイテム図鑑</button>
        <button class="nav-tab" data-tab="simulator">⚔️ 対面シミュレーター</button>
      </nav>
      <div class="controls" id="champControls">
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
    <!-- チャンピオン一覧ビュー -->
    <div id="viewChampions">
      <div class="count-status" id="countStatus">表示中: 0 体</div>
      <div class="grid-container" id="champGrid"></div>
    </div>

    <!-- アイテム図鑑ビュー (Phase 2 実装) -->
    <div id="viewItems" style="display: none;">
      <div class="item-controls">
        <div class="item-controls-row">
          <input type="text" id="itemSearchInput" class="item-search-input" placeholder="アイテム名・通称（例: bc, 帽子, 時計）で検索..." autocomplete="off">
          <select id="itemSortSelect" class="item-sort-select">
            <option value="price_desc">価格が高い順</option>
            <option value="price_asc">価格が安い順</option>
            <option value="name_asc">名前順</option>
          </select>
        </div>
        <div class="item-category-tabs">
          <button class="item-cat-btn active" data-cat="ALL">ALL</button>
          <button class="item-cat-btn" data-cat="AD">⚔️ 攻撃力(AD)</button>
          <button class="item-cat-btn" data-cat="AP">🔮 魔力(AP)</button>
          <button class="item-cat-btn" data-cat="TANK">🛡️ 防具・タンク</button>
          <button class="item-cat-btn" data-cat="BOOTS">👟 靴</button>
          <button class="item-cat-btn" data-cat="SUPPORT">💚 サポート</button>
          <button class="item-cat-btn" data-cat="CONSUMABLE">🧪 消耗品/その他</button>
        </div>
      </div>
      <div class="count-status" id="itemCountStatus">表示中: 0 個</div>
      <div class="items-grid" id="itemsGrid"></div>
    </div>

    <!-- 対面シミュレータービュー (Phase 4で本格実装) -->
    <div id="viewSimulator" style="display: none; padding: 40px 16px; text-align: center; color: var(--text-muted);">
      <div style="font-size: 48px; margin-bottom: 12px;">⚔️</div>
      <h3 style="font-size: 18px; color: #fff; margin-bottom: 8px;">対面対策シミュレーター準備中</h3>
      <p style="font-size: 13px; max-width: 450px; margin: 0 auto; line-height: 1.6;">
        自分と相手のチャンピオンを選択するだけで、レーン戦の注意点、警戒スキル、対策アイテムをリアルタイム表示する機能をPhase 4にて実装予定です！
      </p>
    </div>
  </main>

  <!-- アップデート履歴（リリースノート）モーダル -->
  <div class="modal-overlay" id="changelogModal">
    <div class="modal-content" style="max-width: 650px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 style="font-size: 17px; font-weight: 800; color: #fff;">📜 LoLDB アップデート履歴</h2>
        </div>
        <button class="modal-close-btn" id="changelogCloseBtn">&times;</button>
      </div>
      <div class="modal-body">
        <div class="changelog-list">
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">🛡️ v1.5.0</span>
              <span class="changelog-date">2026-10-04</span>
            </div>
            <ul class="changelog-ul">
              <li>【アイテム図鑑】サモナーズリフト現役全254アイテムのマスターデータベースを新設</li>
              <li>アイテム名・通称・効果検索、価格昇降順・名前順ソート、カテゴリ絞り込み（AD/AP/Tank/靴/サポート/消耗品）に対応</li>
              <li>アイテム詳細モーダル新設（価格・売却額・基本ステータス・パッシブ/アクティブ効果・素材/派生先ツリー完備）</li>
              <li>【アイテム詳細ジャンプ】チャンピオン詳細画面のアイテム（スタート・靴・コア）をタップすると、直接アイテム詳細へジャンプ可能に</li>
              <li>アイテム詳細モーダル内での素材・派生先タップによるスムーズなアイテム間ジャンプに対応</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">🚀 v1.4.0</span>
              <span class="changelog-date">2026-10-04</span>
            </div>
            <ul class="changelog-ul">
              <li>タイトルのシンプル化（「LoLDB」へ改名）とバージョンバッジの最適化</li>
              <li>メインナビゲーション（チャンピオン／アイテム図鑑／対面シミュレーター）の設置</li>
              <li>スマホのスワイプ戻るジェスチャーでアプリが終了せずトップに戻る History API 対応</li>
              <li>チャンピオン詳細を開いた際、必ず最上部からスクロール開始するよう修正</li>
              <li>本リリースノート（バージョン履歴）モーダル機能の新設</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">🛡️ v1.3.0</span>
              <span class="changelog-date">2026-10-03</span>
            </div>
            <ul class="changelog-ul">
              <li>全173チャンピオンのOP.GG最新統計データを総ざらい再スクレイピング</li>
              <li>モルデカイザー(TOP)、アジール(MID)、カリスタ(ADC)、スレッシュ(SUP)等のロール誤認（ハルシネーション）完全根絶</li>
              <li>全件自動監査スクリプトによるロール整合性100%検証</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">⚔️ v1.2.0</span>
              <span class="changelog-date">2026-10-03</span>
            </div>
            <ul class="changelog-ul">
              <li>全173チャンピオンの対面有利不利に「1行戦術理由（勝率％＋立ち回り）」を自動生成・付与</li>
              <li>セラフィーンの担当ロール是正（SUP/ADC）およびサポート推奨ビルドへの更新</li>
              <li>対面相性カードをスマホで読みやすい2段組デザインへUI刷新</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">🎨 v1.1.0</span>
              <span class="changelog-date">2026-10-03</span>
            </div>
            <ul class="changelog-ul">
              <li>Riot公式Data Dragon CDN連携による全スキル・アイテム・スペルのアイコン画像表示対応</li>
              <li>PWA Service Workerをオンライン時最新優先（Network-First）へ強化</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">✨ v1.0.0</span>
              <span class="changelog-date">2026-10-03</span>
            </div>
            <ul class="changelog-ul">
              <li>LoLDB 初回正式リリース</li>
              <li>公式Data Dragon基礎データ ＋ OP.GG攻略統計 ＋ 日本語wiki立ち回り統合PWA</li>
              <li>完全オフライン動作対応（Service Worker + 単一HTML内包アーキテクチャ）</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>

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

  <!-- アイテム詳細モーダル -->
  <div class="modal-overlay" id="itemDetailModal" style="z-index: 120;">
    <div class="modal-content" style="max-width: 620px;">
      <div class="modal-header">
        <div class="item-detail-header-wrap">
          <img id="itemDetailIcon" class="item-detail-big-icon" src="" alt="" onerror="this.style.display='none';">
          <div>
            <h2 id="itemDetailName" style="font-size: 17px; font-weight: 800; color: #fff;">アイテム名</h2>
            <div id="itemDetailPrices" style="margin-top: 4px;"></div>
          </div>
        </div>
        <button class="modal-close-btn" id="itemDetailCloseBtn">&times;</button>
      </div>
      <div class="modal-body" id="itemDetailBody">
        <!-- 基本ステータス -->
        <div class="detail-section" id="itemDetailStatsSec">
          <div class="detail-heading">📊 基本ステータス</div>
          <div id="itemDetailStatsText" style="font-size: 13px; color: #e2e8f0; line-height: 1.6; font-weight: 600;"></div>
        </div>
        <!-- 効果説明 -->
        <div class="detail-section" id="itemDetailDescSec">
          <div class="detail-heading">✨ 特殊効果（パッシブ / アクティブ）</div>
          <div id="itemDetailDescText" style="font-size: 12.5px; color: #cbd5e1; line-height: 1.6; white-space: pre-line;"></div>
        </div>
        <!-- レシピツリー -->
        <div class="detail-section" id="itemDetailRecipeSec">
          <div class="detail-heading">🔨 レシピ（素材 / 派生先）</div>
          <div class="recipe-tree-wrap">
            <div id="itemRecipeFromBox">
              <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px;">素材アイテム (Builds From):</div>
              <div id="itemRecipeFromList" class="recipe-row"></div>
            </div>
            <div id="itemRecipeIntoBox" style="margin-top: 8px;">
              <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px;">派生先アイテム (Builds Into):</div>
              <div id="itemRecipeIntoList" class="recipe-row"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // インライン内包されたマスターデータ
    const CHAMPIONS = {json_str};
    const ITEMS = {items_json_str};

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
          const parts = (m.reason || "").split(" | ");
          const winrate = parts[0] || "勝率 有利";
          const reasonText = parts.length > 1 ? parts.slice(1).join(" | ") : "";
          return `
            <div class="matchup-item">
              <div class="matchup-header">
                <div class="matchup-champ-info">
                  <img class="matchup-champ-img" src="${{oppImg}}" alt="${{m.name || m.champion_id}}" onerror="this.style.display='none';">
                  <span class="matchup-champ-name">${{m.name || m.champion_id}}</span>
                </div>
                <span class="badge-fav">${{winrate}}</span>
              </div>
              ${{reasonText ? `<div class="matchup-reason">${{reasonText}}</div>` : ""}}
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
          const parts = (m.reason || "").split(" | ");
          const winrate = parts[0] || "勝率 不利";
          const reasonText = parts.length > 1 ? parts.slice(1).join(" | ") : "";
          return `
            <div class="matchup-item">
              <div class="matchup-header">
                <div class="matchup-champ-info">
                  <img class="matchup-champ-img" src="${{oppImg}}" alt="${{m.name || m.champion_id}}" onerror="this.style.display='none';">
                  <span class="matchup-champ-name">${{m.name || m.champion_id}}</span>
                </div>
                <span class="badge-unfav">${{winrate}}</span>
              </div>
              ${{reasonText ? `<div class="matchup-reason">${{reasonText}}</div>` : ""}}
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
          <span class="item-pill clickable-item" data-item-id="${{i.item_id}}" title="タップしてアイテム詳細を表示">
            <img class="item-img" src="${{itemImg}}" alt="${{i.name}}" onerror="this.style.display='none';">
            <span>${{i.name}}</span>
          </span>
        `;
      }}).join("") || "データなし";

      let bootsItems = (c.build?.boots || []).map(b => {{
        const bImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{b.item_id}}.png`;
        return `
          <span class="item-pill clickable-item" data-item-id="${{b.item_id}}" title="タップしてアイテム詳細を表示">
            <img class="item-img" src="${{bImg}}" alt="${{b.name}}" onerror="this.style.display='none';">
            <span>${{b.name}}</span>
          </span>
        `;
      }}).join("") || "データなし";

      let coreItems = (c.build?.core || []).map(i => {{
        const cImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{i.item_id}}.png`;
        return `
          <span class="item-pill clickable-item" data-item-id="${{i.item_id}}" title="タップしてアイテム詳細を表示">
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

      // アイテムクリックイベントの登録（アイテム詳細モーダルへジャンプ）
      modalBodyEl.querySelectorAll(".clickable-item").forEach(el => {{
        el.onclick = (e) => {{
          e.stopPropagation();
          const itemId = el.getAttribute("data-item-id");
          if (itemId && ITEMS[itemId]) {{
            openItemDetail(itemId);
          }}
        }};
      }});

      modalEl.classList.add("open");

      // スクロール位置を必ず一番上（最上部）にリセット
      const mContent = modalEl.querySelector(".modal-content");
      if (mContent) mContent.scrollTop = 0;
      modalBodyEl.scrollTop = 0;

      // スマホの戻るスワイプ対応: History APIにモーダル状態を追加
      if (!history.state || history.state.modal !== 'champion_detail') {{
        history.pushState({{ modal: 'champion_detail', champId: champId }}, '');
      }}
    }}

    function closeDetailModal() {{
      modalEl.classList.remove("open");
    }}

    modalCloseBtn.onclick = () => {{
      if (history.state && history.state.modal === 'champion_detail') {{
        history.back();
      }} else {{
        closeDetailModal();
      }}
    }};

    modalEl.onclick = (e) => {{
      if (e.target === modalEl) {{
        if (history.state && history.state.modal === 'champion_detail') {{
          history.back();
        }} else {{
          closeDetailModal();
        }}
      }}
    }};

    // リリースノート（アプデ履歴）モーダル制御
    const changelogModalEl = document.getElementById("changelogModal");
    const changelogCloseBtn = document.getElementById("changelogCloseBtn");
    const patchBadgeEl = document.getElementById("patchBadge");

    function openChangelogModal() {{
      changelogModalEl.classList.add("open");
      const cContent = changelogModalEl.querySelector(".modal-content");
      if (cContent) cContent.scrollTop = 0;
      if (!history.state || history.state.modal !== 'changelog') {{
        history.pushState({{ modal: 'changelog' }}, '');
      }}
    }}

    function closeChangelogModal() {{
      changelogModalEl.classList.remove("open");
    }}

    if (patchBadgeEl) {{
      patchBadgeEl.onclick = () => openChangelogModal();
    }}

    if (changelogCloseBtn) {{
      changelogCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'changelog') {{
          history.back();
        }} else {{
          closeChangelogModal();
        }}
      }};
    }}

    if (changelogModalEl) {{
      changelogModalEl.onclick = (e) => {{
        if (e.target === changelogModalEl) {{
          if (history.state && history.state.modal === 'changelog') {{
            history.back();
          }} else {{
            closeChangelogModal();
          }}
        }}
      }};
    }}

    // ==========================================
    // アイテム詳細モーダル制御 (Phase 2)
    // ==========================================
    const itemDetailModalEl = document.getElementById("itemDetailModal");
    const itemDetailCloseBtn = document.getElementById("itemDetailCloseBtn");
    const itemDetailIcon = document.getElementById("itemDetailIcon");
    const itemDetailName = document.getElementById("itemDetailName");
    const itemDetailPrices = document.getElementById("itemDetailPrices");
    const itemDetailStatsSec = document.getElementById("itemDetailStatsSec");
    const itemDetailStatsText = document.getElementById("itemDetailStatsText");
    const itemDetailDescSec = document.getElementById("itemDetailDescSec");
    const itemDetailDescText = document.getElementById("itemDetailDescText");
    const itemDetailRecipeSec = document.getElementById("itemDetailRecipeSec");
    const itemRecipeFromBox = document.getElementById("itemRecipeFromBox");
    const itemRecipeFromList = document.getElementById("itemRecipeFromList");
    const itemRecipeIntoBox = document.getElementById("itemRecipeIntoBox");
    const itemRecipeIntoList = document.getElementById("itemRecipeIntoList");

    function openItemDetail(itemId) {{
      const item = ITEMS[itemId];
      if (!item) return;

      const patch = "16.19.1";
      itemDetailIcon.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{item.id}}.png`;
      itemDetailIcon.style.display = "block";
      itemDetailName.textContent = item.name;

      // 価格
      const totalGold = item.gold?.total || 0;
      const sellGold = item.gold?.sell || 0;
      itemDetailPrices.innerHTML = `
        <span class="item-card-price">💰 価格: ${{totalGold}} G</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">(売却: ${{sellGold}} G)</span>
      `;

      // ステータス整形
      const statsObj = item.stats || {{}};
      const statEntries = Object.entries(statsObj);
      if (statEntries.length > 0) {{
        itemDetailStatsSec.style.display = "block";
        const statsHtml = statEntries.map(([k, v]) => {{
          let label = k;
          let val = v;
          if (k === "FlatPhysicalDamageMod") label = "⚔️ 攻撃力(AD)";
          else if (k === "FlatMagicDamageMod") label = "🔮 魔力(AP)";
          else if (k === "FlatHPPoolMod") label = "❤️ 体力(HP)";
          else if (k === "FlatArmorMod") label = "🛡️ 物理防御(AR)";
          else if (k === "FlatSpellBlockMod") label = "🌀 魔法防御(MR)";
          else if (k === "PercentAttackSpeedMod") {{ label = "⚡ 攻撃速度"; val = `+${{Math.round(val * 100)}}%`; }}
          else if (k === "FlatMovementSpeedMod") label = "👟 移動速度";
          else if (k === "PercentMovementSpeedMod") {{ label = "👟 移動速度%"; val = `+${{Math.round(val * 100)}}%`; }}
          else if (k === "FlatCritChanceMod") {{ label = "🎯 クリティカル率"; val = `+${{Math.round(val * 100)}}%`; }}
          else if (k === "FlatMPPoolMod") label = "💧 マナ";
          else if (k === "PercentLifeStealMod") {{ label = "🩸 ライフスティール"; val = `+${{Math.round(val * 100)}}%`; }}
          else if (k === "PercentOmnivampMod") {{ label = "🩸 オムニヴァンプ"; val = `+${{Math.round(val * 100)}}%`; }}
          else if (k === "PercentTenacityMod") {{ label = "⛓️ 行動妨害耐性"; val = `+${{Math.round(val * 100)}}%`; }}

          if (typeof val === "number" && !val.toString().startsWith("+") && val > 0) {{
            val = `+${{val}}`;
          }}
          return `<div style="display:inline-block; margin-right: 14px; margin-bottom: 4px;"><strong>${{label}}:</strong> ${{val}}</div>`;
        }}).join("");
        itemDetailStatsText.innerHTML = statsHtml;
      }} else {{
        itemDetailStatsSec.style.display = "none";
      }}

      // 説明文整形
      let cleanDesc = item.description || item.plaintext || "効果情報なし";
      cleanDesc = cleanDesc.replace(/<br\\s*\\/?>/gi, "\\n")
                           .replace(/<\\/p>/gi, "\\n")
                           .replace(/<li>/gi, "• ")
                           .replace(/<\\/li>/gi, "\\n")
                           .replace(/<[^>]+>/g, "")
                           .trim();
      itemDetailDescText.textContent = cleanDesc;

      // 素材ツリー (Builds from)
      const fromIds = item.from || [];
      if (fromIds.length > 0) {{
        itemRecipeFromBox.style.display = "block";
        itemRecipeFromList.innerHTML = fromIds.map(fid => {{
          const fItem = ITEMS[fid];
          const fName = fItem ? fItem.name : `ID:${{fid}}`;
          const fPrice = fItem ? `${{fItem.gold?.total || 0}}G` : "";
          const fImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{fid}}.png`;
          return `
            <span class="recipe-item-pill" data-recipe-id="${{fid}}" title="タップして詳細を表示">
              <img src="${{fImg}}" alt="${{fName}}" onerror="this.src='icon.png';">
              <span>${{fName}}</span>
              <span style="color:var(--accent); font-size:11px;">${{fPrice}}</span>
            </span>
          `;
        }}).join("");
      }} else {{
        itemRecipeFromBox.style.display = "none";
      }}

      // 派生先ツリー (Builds into)
      const intoIds = item.into || [];
      if (intoIds.length > 0) {{
        itemRecipeIntoBox.style.display = "block";
        itemRecipeIntoList.innerHTML = intoIds.map(iid => {{
          const iItem = ITEMS[iid];
          const iName = iItem ? iItem.name : `ID:${{iid}}`;
          const iPrice = iItem ? `${{iItem.gold?.total || 0}}G` : "";
          const iImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{iid}}.png`;
          return `
            <span class="recipe-item-pill" data-recipe-id="${{iid}}" title="タップして詳細を表示">
              <img src="${{iImg}}" alt="${{iName}}" onerror="this.src='icon.png';">
              <span>${{iName}}</span>
              <span style="color:var(--accent); font-size:11px;">${{iPrice}}</span>
            </span>
          `;
        }}).join("");
      }} else {{
        itemRecipeIntoBox.style.display = "none";
      }}

      if (fromIds.length === 0 && intoIds.length === 0) {{
        itemDetailRecipeSec.style.display = "none";
      }} else {{
        itemDetailRecipeSec.style.display = "block";
      }}

      // レシピアイテムのクリックイベント（素材・派生先アイテム詳細へジャンプ）
      itemDetailModalEl.querySelectorAll(".recipe-item-pill").forEach(pill => {{
        pill.onclick = (e) => {{
          e.stopPropagation();
          const nextId = pill.getAttribute("data-recipe-id");
          if (nextId) openItemDetail(nextId);
        }};
      }});

      itemDetailModalEl.classList.add("open");
      const iContent = itemDetailModalEl.querySelector(".modal-content");
      if (iContent) iContent.scrollTop = 0;
      const iBody = itemDetailModalEl.querySelector(".modal-body");
      if (iBody) iBody.scrollTop = 0;

      // History API
      if (!history.state || history.state.modal !== 'item_detail') {{
        history.pushState({{ modal: 'item_detail', itemId: itemId }}, '');
      }}
    }}

    function closeItemDetailModal() {{
      itemDetailModalEl.classList.remove("open");
    }}

    if (itemDetailCloseBtn) {{
      itemDetailCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'item_detail') {{
          history.back();
        }} else {{
          closeItemDetailModal();
        }}
      }};
    }}

    if (itemDetailModalEl) {{
      itemDetailModalEl.onclick = (e) => {{
        if (e.target === itemDetailModalEl) {{
          if (history.state && history.state.modal === 'item_detail') {{
            history.back();
          }} else {{
            closeItemDetailModal();
          }}
        }}
      }};
    }}

    // ==========================================
    // アイテム図鑑の制御・検索・ソート (Phase 2)
    // ==========================================
    const itemsGridEl = document.getElementById("itemsGrid");
    const itemCountStatusEl = document.getElementById("itemCountStatus");
    const itemSearchInput = document.getElementById("itemSearchInput");
    const itemSortSelect = document.getElementById("itemSortSelect");
    let currentItemCat = "ALL";
    let itemSearchKeyword = "";
    let currentItemSort = "price_desc";

    function renderItemsList() {{
      if (!itemsGridEl) return;
      itemsGridEl.innerHTML = "";
      const query = itemSearchKeyword.trim().toLowerCase();

      let itemsList = Object.values(ITEMS);

      // カテゴリフィルター
      if (currentItemCat !== "ALL") {{
        itemsList = itemsList.filter(item => {{
          return item.categories && item.categories.includes(currentItemCat);
        }});
      }}

      // 検索フィルター
      if (query) {{
        itemsList = itemsList.filter(item => {{
          const name = (item.name || "").toLowerCase();
          const colloq = (item.colloq || "").toLowerCase();
          const plain = (item.plaintext || "").toLowerCase();
          return name.includes(query) || colloq.includes(query) || plain.includes(query);
        }});
      }}

      // ソート
      itemsList.sort((a, b) => {{
        if (currentItemSort === "price_desc") {{
          return (b.gold?.total || 0) - (a.gold?.total || 0);
        }} else if (currentItemSort === "price_asc") {{
          return (a.gold?.total || 0) - (b.gold?.total || 0);
        }} else if (currentItemSort === "name_asc") {{
          return (a.name || "").localeCompare(b.name || "", "ja");
        }}
        return 0;
      }});

      itemsList.forEach(item => {{
        const card = document.createElement("div");
        card.className = "item-grid-card";
        card.onclick = () => openItemDetail(item.id);

        const patch = "16.19.1";
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{item.id}}.png`;
        const price = item.gold?.total ? `${{item.gold.total}} G` : "無料";

        card.innerHTML = `
          <img class="item-card-icon" src="${{imgUrl}}" alt="${{item.name}}" loading="lazy" onerror="this.src='icon.png';">
          <div class="item-card-name" title="${{item.name}}">${{item.name}}</div>
          <div class="item-card-price">💰 ${{price}}</div>
        `;
        itemsGridEl.appendChild(card);
      }});

      if (itemCountStatusEl) {{
        itemCountStatusEl.textContent = `表示中: ${{itemsList.length}} 個 / 全 ${{Object.keys(ITEMS).length}} 個`;
      }}
    }}

    if (itemSearchInput) {{
      itemSearchInput.addEventListener("input", (e) => {{
        itemSearchKeyword = e.target.value;
        renderItemsList();
      }});
    }}

    if (itemSortSelect) {{
      itemSortSelect.addEventListener("change", (e) => {{
        currentItemSort = e.target.value;
        renderItemsList();
      }});
    }}

    document.querySelectorAll(".item-cat-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".item-cat-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentItemCat = btn.getAttribute("data-cat");
        renderItemsList();
      }});
    }});

    // スマホのジェスチャースワイプ「戻る」イベント対応（アプリ終了防止・モーダル多重スタック制御）
    window.addEventListener("popstate", (e) => {{
      if (itemDetailModalEl && itemDetailModalEl.classList.contains("open")) {{
        closeItemDetailModal();
        return;
      }}
      if (modalEl && modalEl.classList.contains("open")) {{
        closeDetailModal();
        return;
      }}
      if (changelogModalEl && changelogModalEl.classList.contains("open")) {{
        closeChangelogModal();
        return;
      }}
    }});

    // ESCキー対応（モーダル多重スタック制御）
    window.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") {{
        if (itemDetailModalEl && itemDetailModalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'item_detail') history.back();
          else closeItemDetailModal();
          return;
        }}
        if (modalEl && modalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'champion_detail') history.back();
          else closeDetailModal();
          return;
        }}
        if (changelogModalEl && changelogModalEl.classList.contains("open")) {{
          if (history.state && history.state.modal === 'changelog') history.back();
          else closeChangelogModal();
          return;
        }}
      }}
    }});

    // メインナビゲーションタブ切り替え
    const champControlsEl = document.getElementById("champControls");
    const viewChampsEl = document.getElementById("viewChampions");
    const viewItemsEl = document.getElementById("viewItems");
    const viewSimEl = document.getElementById("viewSimulator");

    document.querySelectorAll(".nav-tab").forEach(tab => {{
      tab.addEventListener("click", () => {{
        document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const target = tab.getAttribute("data-tab");

        if (target === "champions") {{
          viewChampsEl.style.display = "block";
          viewItemsEl.style.display = "none";
          viewSimEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "flex";
        }} else if (target === "items") {{
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "block";
          viewSimEl.style.display = "none";
          if (champControlsEl) champControlsEl.style.display = "none";
          renderItemsList();
        }} else if (target === "simulator") {{
          viewChampsEl.style.display = "none";
          viewItemsEl.style.display = "none";
          viewSimEl.style.display = "block";
          if (champControlsEl) champControlsEl.style.display = "none";
        }}
      }});
    }});

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
    renderItemsList();

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
    root_index_path = base_dir / "index.html"
    print(f"単一HTML {index_path} および {root_index_path} を出力中...")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(root_index_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Service Worker (sw.js) の生成
    sw_content = """// LoLDB Service Worker - Offline Cache v6
const CACHE_NAME = 'loldb-cache-v6';
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
    root_sw_path = base_dir / "sw.js"
    print(f"Service Worker {sw_path} を出力中...")
    with open(sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)
    with open(root_sw_path, "w", encoding="utf-8") as f:
        f.write(sw_content)

    # PWA Manifest (manifest.json) の生成
    manifest_content = """{
  "name": "LoLDB",
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
    root_manifest_path = base_dir / "manifest.json"
    print(f"Manifest {manifest_path} を出力中...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)
    with open(root_manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    html_size_kb = os.path.getsize(index_path) / 1024
    print("[SUCCESS] PWA build completed successfully!")
    print(f"出力ファイル: {index_path} ({html_size_kb:.2f} KB)")
    print(f"Service Worker: {sw_path}")
    print(f"Manifest: {manifest_path}")

if __name__ == "__main__":
    build()
