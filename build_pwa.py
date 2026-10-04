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
    /* 複数ロール切り替えサブタブ */
    .modal-role-tabs {{
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .modal-role-btn {{
      background: #101726;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s;
    }}
    .modal-role-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .modal-role-btn.active {{
      background: #0284c7;
      border-color: var(--primary);
      color: #fff;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.4);
    }}
    /* サステイン & スキル上げ優先度バッジ */
    .champ-highlight-badges {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 10px;
    }}
    .badge-sustain {{
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.4);
      color: #fb7185;
      font-weight: 800;
      font-size: 11.5px;
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .badge-skill-order {{
      background: rgba(56, 189, 248, 0.15);
      border: 1px solid rgba(56, 189, 248, 0.4);
      color: #38bdf8;
      font-weight: 800;
      font-size: 11.5px;
      padding: 4px 10px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .sustain-reason-box {{
      font-size: 11.5px;
      color: #cbd5e1;
      background: rgba(244, 63, 94, 0.08);
      border-left: 3px solid #f43f5e;
      padding: 6px 10px;
      border-radius: 6px;
      margin-bottom: 14px;
      line-height: 1.45;
    }}
    /* 特徴・強み・弱み */
    .overview-text {{
      font-size: 12.5px;
      color: #e2e8f0;
      line-height: 1.6;
      margin-bottom: 10px;
    }}
    .pros-cons-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }}
    @media (min-width: 600px) {{
      .pros-cons-grid {{
        grid-template-columns: 1fr 1fr;
      }}
    }}
    .pros-box {{
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      border-radius: 8px;
      padding: 10px;
    }}
    .cons-box {{
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: 8px;
      padding: 10px;
    }}
    .pros-cons-title {{
      font-size: 12px;
      font-weight: 800;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .pros-title {{ color: var(--favorable); }}
    .cons-title {{ color: var(--accent); }}
    .pros-cons-ul {{
      list-style: none;
      font-size: 11.5px;
      color: #cbd5e1;
      line-height: 1.5;
    }}
    .pros-cons-ul li {{
      margin-bottom: 4px;
      position: relative;
      padding-left: 14px;
    }}
    .pros-box li::before {{
      content: "✓";
      color: var(--favorable);
      position: absolute;
      left: 0;
      font-weight: bold;
    }}
    .cons-box li::before {{
      content: "!";
      color: var(--accent);
      position: absolute;
      left: 0;
      font-weight: bold;
    }}
    /* 実戦コンボ */
    .combo-grid {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .combo-card {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
    }}
    .combo-name {{
      font-size: 12.5px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 4px;
    }}
    .combo-recipe {{
      font-size: 12px;
      font-weight: 700;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid rgba(56, 189, 248, 0.2);
      margin-bottom: 6px;
      word-break: break-all;
    }}
    .combo-desc {{
      font-size: 11.5px;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    /* 複数アイテムビルドタブ */
    .build-pat-tabs {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      margin-bottom: 10px;
      padding-bottom: 2px;
    }}
    .build-pat-btn {{
      background: #101726;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }}
    .build-pat-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .build-pat-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
    }}
    .build-pat-desc {{
      font-size: 12px;
      color: #cbd5e1;
      background: #0b0f19;
      border-left: 3px solid var(--accent);
      padding: 6px 10px;
      border-radius: 6px;
      margin-bottom: 10px;
      line-height: 1.4;
    }}
    /* 対面対策シミュレーター スタイル (Phase 4) */
    .sim-container {{
      max-width: 800px;
      margin: 0 auto;
      padding: 10px 0 40px;
    }}
    .sim-slots-wrap {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin-bottom: 20px;
    }}
    .sim-slot {{
      flex: 1;
    }}
    .sim-slot-label {{
      font-size: 12px;
      font-weight: 800;
      color: var(--text-muted);
      margin-bottom: 6px;
    }}
    .sim-slot-card {{
      background: var(--bg-card);
      border: 2px dashed var(--border);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      transition: all 0.2s;
      min-height: 68px;
    }}
    .sim-slot-card:hover {{
      border-color: var(--primary);
      background: var(--bg-card-hover);
      transform: translateY(-2px);
    }}
    .sim-slot-card.selected {{
      border-style: solid;
      border-color: var(--primary);
      background: #151d30;
      box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    }}
    .sim-slot-icon-wrap {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      background: #0b0f19;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      flex-shrink: 0;
      border: 1px solid var(--border);
    }}
    .sim-slot-plus {{
      font-size: 24px;
      font-weight: 300;
      color: var(--text-muted);
    }}
    .sim-slot-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .sim-slot-info {{
      flex: 1;
      overflow: hidden;
    }}
    .sim-slot-name {{
      font-size: 13.5px;
      font-weight: 800;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .sim-slot-sub {{
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }}
    .sim-vs-wrap {{
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .sim-vs-badge {{
      background: #0b0f19;
      border: 2px solid var(--border);
      color: var(--accent);
      font-size: 12px;
      font-weight: 900;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(0,0,0,0.5);
    }}
    .sim-result-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 14px;
    }}
    .sim-result-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .sim-result-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: #fff;
    }}
    .sim-adv-badge {{
      font-size: 12px;
      font-weight: 800;
      padding: 4px 10px;
      border-radius: 6px;
    }}
    .sim-adv-fav {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: var(--favorable);
    }}
    .sim-adv-unfav {{
      background: rgba(244, 63, 94, 0.15);
      border: 1px solid rgba(244, 63, 94, 0.4);
      color: var(--unfavorable);
    }}
    .sim-adv-even {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.4);
      color: var(--accent);
    }}
    .sim-picker-controls {{
      margin-bottom: 12px;
    }}
    .sim-role-btn {{
      background: #151d30;
      color: var(--text-muted);
      border: 1px solid var(--border);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .sim-role-btn:hover {{
      color: #fff;
      border-color: var(--primary);
    }}
    .sim-role-btn.active {{
      background: #0284c7;
      color: #fff;
      border-color: var(--primary);
    }}
    .sim-picker-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
      gap: 8px;
      max-height: 50vh;
      overflow-y: auto;
      padding-right: 4px;
    }}
    .sim-picker-item {{
      background: #101726;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 4px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      cursor: pointer;
      transition: all 0.2s;
      text-align: center;
    }}
    .sim-picker-item:hover {{
      border-color: var(--primary);
      background: #1e293b;
      transform: translateY(-2px);
    }}
    .sim-picker-img {{
      width: 44px;
      height: 44px;
      border-radius: 8px;
      object-fit: cover;
    }}
    .sim-picker-name {{
      font-size: 11px;
      font-weight: 700;
      color: #f1f5f9;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
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
          <span class="patch-badge" id="patchBadge" title="タップして更新履歴を表示">Patch 16.19 / v1.7.0 ℹ️</span>
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

    <!-- 対面シミュレータービュー (Phase 4 実装) -->
    <div id="viewSimulator" style="display: none;">
      <div class="sim-container">
        <!-- ピッカーエリア (自分 vs 相手) -->
        <div class="sim-slots-wrap">
          <!-- 自分のチャンピオン -->
          <div class="sim-slot" id="simSlotMe">
            <div class="sim-slot-label">👑 あなたのピック</div>
            <div class="sim-slot-card empty" id="simCardMe" onclick="openSimPicker('me')">
              <div class="sim-slot-icon-wrap">
                <div class="sim-slot-plus">+</div>
                <img id="simImgMe" class="sim-slot-img" src="" alt="" style="display: none;">
              </div>
              <div class="sim-slot-info">
                <div class="sim-slot-name" id="simNameMe">チャンピオンを選択</div>
                <div class="sim-slot-sub" id="simRoleMe">タップして選択</div>
              </div>
            </div>
          </div>

          <div class="sim-vs-wrap">
            <div class="sim-vs-badge">VS</div>
          </div>

          <!-- 対面の相手チャンピオン -->
          <div class="sim-slot" id="simSlotOpp">
            <div class="sim-slot-label">👿 対面の相手ピック</div>
            <div class="sim-slot-card empty" id="simCardOpp" onclick="openSimPicker('opp')">
              <div class="sim-slot-icon-wrap">
                <div class="sim-slot-plus">+</div>
                <img id="simImgOpp" class="sim-slot-img" src="" alt="" style="display: none;">
              </div>
              <div class="sim-slot-info">
                <div class="sim-slot-name" id="simNameOpp">チャンピオンを選択</div>
                <div class="sim-slot-sub" id="simRoleOpp">タップして選択</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分析結果表示エリア -->
        <div id="simEmptyPrompt" style="padding: 40px 16px; text-align: center; color: var(--text-muted);">
          <div style="font-size: 40px; margin-bottom: 10px;">⚔️</div>
          <div style="font-size: 14px; font-weight: 700; color: #fff;">自分と相手のチャンピオンを選択してください</div>
          <div style="font-size: 12px; margin-top: 4px;">相性・統計勝率・警戒スキル・対策アイテムを瞬時に分析します。</div>
        </div>

        <div id="simResultArea" style="display: none;">
          <!-- 1. 相性・勝率メーター -->
          <div class="sim-result-card" id="simAdvantageCard">
            <div class="sim-result-header">
              <span class="sim-result-title">⚖️ 対面相性 ＆ 推定勝率</span>
              <span id="simAdvantageBadge" class="sim-adv-badge">判定中</span>
            </div>
            <div id="simAdvantageDesc" style="font-size: 13px; color: #e2e8f0; line-height: 1.5; margin-top: 6px;"></div>
          </div>

          <!-- 2. レーン戦の注意点 ＆ 相手の警戒スキル -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">⚠️ レーン戦の注意点 ＆ 警戒スキル</span>
            </div>
            <div id="simSustainWarning" style="display: none;" class="sustain-reason-box"></div>
            <div id="simLaningTips" style="font-size: 12.5px; color: #cbd5e1; line-height: 1.6; margin-top: 6px;"></div>
          </div>

          <!-- 3. 積むべき対策アイテムリスト -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">🛡️ 積むべき対策おすすめアイテム（タップで詳細）</span>
            </div>
            <div id="simItemList" class="item-tags" style="margin-top: 8px;"></div>
          </div>

          <!-- 4. 狙い目コンボ ＆ 仕掛けどころ -->
          <div class="sim-result-card">
            <div class="sim-result-header">
              <span class="sim-result-title">🥊 有効なショートトレード ＆ 仕掛けどころ</span>
            </div>
            <div id="simCombosArea" class="combo-grid" style="margin-top: 8px;"></div>
          </div>
        </div>
      </div>
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
              <span class="changelog-ver">⚔️ v1.7.0</span>
              <span class="changelog-date">2026-10-04</span>
            </div>
            <ul class="changelog-ul">
              <li>【対面対策シミュレーター】自分と相手のチャンピオンを選択する対面リアルタイム分析エンジンを新設</li>
              <li>【ロール別絞り込み】ピッカーで自分・相手ともにレーン別（ALL/TOP/JUG/MID/ADC/SUP）にサクッと絞り込み可能</li>
              <li>【リアルタイム対策分析】対面勝率判定、相手のサステイン警告＆警戒スキル、積むべき対策アイテム、狙い目コンボを即座に提示</li>
              <li>【対策アイテムジャンプ】シミュレーター内の対策アイテムをタップすると即座にアイテム詳細モーダルへジャンプ可能</li>
            </ul>
          </div>
          <div class="changelog-item">
            <div class="changelog-header">
              <span class="changelog-ver">⚡ v1.6.0</span>
              <span class="changelog-date">2026-10-04</span>
            </div>
            <ul class="changelog-ul">
              <li>【スキル上げ順】全173体の最大化優先度（例: Q > E > W）をバッジ明記</li>
              <li>【サステイン＆重傷判定】強力な回復スキル所持者への「🩸 サステイン所持（対面時: 重傷推奨）」警告バッジと理由を新設</li>
              <li>【キャラ概要】全チャンピオンの特徴・強み3選（Strengths）・弱み3選（Weaknesses）を完全網羅</li>
              <li>【立ち回り＆スキル吐きどころ】定型文を一新し、レーン戦・集団戦・重要スキルの温存/吐きどころの極意を徹底解説</li>
              <li>【実戦コンボ】基本ショートトレード・オールイン・Flash併用テクニック（Q3+FlashやEQベイブレード等）を体系化</li>
              <li>【複数ビルドパターン】サイオン（対AD/対AP/脅威）をはじめとする状況別・対面別の複数アイテム構成切り替えに対応</li>
              <li>【複数ロールタブ】複数レーン適応チャンピオンのレーン別タブ切り替え（推奨スペル・役割・ビルド）を新設</li>
            </ul>
          </div>
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

  <!-- チャンピオン選択ピッカーモーダル (ロール絞り込み付き) -->
  <div class="modal-overlay" id="simPickerModal" style="z-index: 150;">
    <div class="modal-content" style="max-width: 650px;">
      <div class="modal-header">
        <div class="modal-title-wrap">
          <h2 id="simPickerTitle" style="font-size: 16px; font-weight: 800; color: #fff;">チャンピオンを選択</h2>
        </div>
        <button class="modal-close-btn" id="simPickerCloseBtn">&times;</button>
      </div>
      <div class="modal-body" style="padding: 12px;">
        <!-- 検索 ＆ ロール絞り込みタブ (濱田くんの重要指定！) -->
        <div class="sim-picker-controls">
          <input type="text" id="simSearchInput" class="item-search-input" placeholder="名前・英語名で検索..." autocomplete="off">
          <div class="role-tabs" style="margin-top: 8px;">
            <button class="sim-role-btn active" data-sim-role="ALL">ALL</button>
            <button class="sim-role-btn" data-sim-role="TOP">TOP</button>
            <button class="sim-role-btn" data-sim-role="JUG">JUG</button>
            <button class="sim-role-btn" data-sim-role="MID">MID</button>
            <button class="sim-role-btn" data-sim-role="ADC">ADC</button>
            <button class="sim-role-btn" data-sim-role="SUP">SUP</button>
          </div>
        </div>
        <div class="sim-picker-grid" id="simPickerGrid"></div>
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

    function openDetail(champId, activeRole = null) {{
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

      // 選択中ロール（未指定時は第1ロール）
      const currentSelectedRole = activeRole || (c.roles && c.roles.length > 0 ? c.roles[0] : "TOP");
      const roleSpecificData = (c.role_data && c.role_data[currentSelectedRole]) ? c.role_data[currentSelectedRole] : {{}};
      const currentSpells = roleSpecificData.spells || c.summoner_spells || ["フラッシュ", "テレポート"];

      // 複数ロール切り替えサブタブ
      let roleTabsHtml = "";
      if (c.roles && c.roles.length > 1) {{
        roleTabsHtml = `
          <div class="modal-role-tabs">
            ${{c.roles.map(r => `
              <button class="modal-role-btn ${{r === currentSelectedRole ? "active" : ""}}" data-modal-role="${{r}}">
                <span class="mini-badge ${{getRoleBadgeClass(r)}}">${{r}}</span>
                <span>${{r}} レーン</span>
              </button>
            `).join("")}}
          </div>
        `;
      }}

      // サステイン & スキル上げ優先度バッジ
      const sustainInfo = c.sustain_info || {{}};
      let sustainBadgeHtml = "";
      let sustainReasonHtml = "";
      if (sustainInfo.has_sustain) {{
        sustainBadgeHtml = `<span class="badge-sustain">🩸 サステイン所持 (重傷推奨)</span>`;
        sustainReasonHtml = `<div class="sustain-reason-box">⚠️ <strong>【対面注意・重傷推奨】</strong> ${{sustainInfo.reason}}</div>`;
      }}

      const skillOrder = roleSpecificData.skill_order || c.skill_order || "Q > E > W";
      const skillOrderBadgeHtml = `<span class="badge-skill-order">⚡ スキル上げ順: ${{skillOrder}}</span>`;

      // スペル一覧HTML
      const spellsBadge = currentSpells.map(s => {{
        const sImg = SPELL_IMG_MAP[s] || "SummonerFlash.png";
        const sUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/spell/${{sImg}}`;
        return `
          <span class="spell-pill">
            <img class="spell-img" src="${{sUrl}}" alt="${{s}}" onerror="this.style.display='none';">
            <span>${{s}}</span>
          </span>
        `;
      }}).join("") || "<span style='color:var(--text-muted); font-size:12px;'>標準スペル</span>";

      // 特徴・強み・弱み
      const ov = c.overview || {{}};
      const strengthsHtml = (ov.strengths || []).map(s => `<li>${{s}}</li>`).join("");
      const weaknessesHtml = (ov.weaknesses || []).map(w => `<li>${{w}}</li>`).join("");

      // 立ち回りメモ
      const gn = c.gameplay_notes || {{}};
      const roleNoteHtml = roleSpecificData.role_note ? `<div style="font-size:12px; margin-bottom:8px; color:#38bdf8; line-height:1.5;"><strong>【${{currentSelectedRole}}ロールの主務】</strong> ${{roleSpecificData.role_note}}</div>` : "";
      const laningNote = gn.laning || "相手のスキルクールダウンやミニオンウェーブの位置を注視してトレードを行う。";
      const tfNote = gn.teamfight || "集団戦では味方とフォーカスを合わせ、自身の役割を完遂する。";
      const tipNote = gn.key_tips || "";

      // 実戦コンボ
      const combos = c.combos || [];
      const combosHtml = combos.map(cb => `
        <div class="combo-card">
          <div class="combo-name">🥊 ${{cb.name}}</div>
          <div class="combo-recipe">${{cb.recipe}}</div>
          <div class="combo-desc">${{cb.desc}}</div>
        </div>
      `).join("");

      // 複数ビルドパターン
      const buildPatterns = roleSpecificData.build_patterns || c.build_patterns || [];
      let buildTabsHtml = "";
      let buildContentHtml = "";

      function renderBuildPatternInner(bp) {{
        const pCoreHtml = (bp.core_items || []).map((ci, sIdx) => {{
          const cImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{ci.item_id}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{ci.item_id}}" title="タップして詳細を表示">
              <span class="item-step">${{sIdx + 1}}</span>
              <img class="item-img" src="${{cImg}}" alt="${{ci.name}}" onerror="this.src='icon.png';">
              <span>${{ci.name}}</span>
            </span>
          `;
        }}).join("");

        const pStarterHtml = (bp.starter || []).map(sName => {{
          const sItem = Object.values(ITEMS).find(it => it.name === sName);
          const sId = sItem ? sItem.id : "1055";
          const sImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{sId}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{sId}}" title="タップして詳細を表示">
              <img class="item-img" src="${{sImg}}" alt="${{sName}}" onerror="this.src='icon.png';">
              <span>${{sName}}</span>
            </span>
          `;
        }}).join("");

        const bootName = bp.boots || "プレート スチールキャップ";
        const bootItem = Object.values(ITEMS).find(it => it.name === bootName);
        const bootId = bootItem ? bootItem.id : "3047";
        const bootImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{bootId}}.png`;
        const pBootsHtml = `
          <span class="item-pill clickable-item" data-item-id="${{bootId}}" title="タップして詳細を表示">
            <img class="item-img" src="${{bootImg}}" alt="${{bootName}}" onerror="this.src='icon.png';">
            <span>${{bootName}}</span>
          </span>
        `;

        const pSitHtml = (bp.situational || []).map(sitName => {{
          const sitItem = Object.values(ITEMS).find(it => it.name === sitName);
          const sitId = sitItem ? sitItem.id : "1001";
          const sitImg = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/item/${{sitId}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{sitId}}" title="タップして詳細を表示">
              <img class="item-img" src="${{sitImg}}" alt="${{sitName}}" onerror="this.src='icon.png';">
              <span>${{sitName}}</span>
            </span>
          `;
        }}).join("");

        return `
          <div class="build-pat-desc">💡 ${{bp.desc}}</div>
          <div class="build-group">
            <div class="build-group-title">スタートアイテム</div>
            <div class="item-tags">${{pStarterHtml}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨靴</div>
            <div class="item-tags">${{pBootsHtml}}</div>
          </div>
          <div class="build-group">
            <div class="build-group-title">推奨コアアイテム（進行順）</div>
            <div class="item-tags">${{pCoreHtml}}</div>
          </div>
          ${{pSitHtml ? `
            <div class="build-group">
              <div class="build-group-title">状況別・後半選択アイテム</div>
              <div class="item-tags">${{pSitHtml}}</div>
            </div>
          ` : ""}}
        `;
      }}

      if (buildPatterns.length > 0) {{
        buildTabsHtml = `
          <div class="build-pat-tabs">
            ${{buildPatterns.map((bp, idx) => `
              <button class="build-pat-btn ${{idx === 0 ? "active" : ""}}" data-build-idx="${{idx}}">${{bp.name}}</button>
            `).join("")}}
          </div>
        `;
        buildContentHtml = `<div id="buildPatternContent">${{renderBuildPatternInner(buildPatterns[0])}}</div>`;
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

      // ルーン
      const r = c.runes || {{}};
      const priChoices = (r.primary?.choices || []).join(" / ");
      const secChoices = (r.secondary?.choices || []).join(" / ");
      const shards = (r.shards || []).join(" / ");

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

      modalBodyEl.innerHTML = `
        ${{roleTabsHtml}}

        <!-- ハイライトバッジ群 -->
        <div class="champ-highlight-badges">
          ${{sustainBadgeHtml}}
          ${{skillOrderBadgeHtml}}
        </div>
        ${{sustainReasonHtml}}

        <!-- チャンピオン概要 (特徴・強み・弱み) -->
        <div class="detail-section">
          <div class="detail-heading">📖 チャンピオン概要（特徴・強み・弱み）</div>
          <div class="overview-text">${{ov.summary || ""}}</div>
          <div class="pros-cons-grid">
            <div class="pros-box">
              <div class="pros-cons-title pros-title">💪 強み (Strengths)</div>
              <ul class="pros-cons-ul">${{strengthsHtml}}</ul>
            </div>
            <div class="cons-box">
              <div class="pros-cons-title cons-title">⚠️ 弱み (Weaknesses)</div>
              <ul class="pros-cons-ul">${{weaknessesHtml}}</ul>
            </div>
          </div>
        </div>

        <!-- 立ち回りメモ & スキル吐きどころ -->
        <div class="detail-section">
          <div class="detail-heading">📝 立ち回り概要メモ & スキルの吐きどころ</div>
          ${{roleNoteHtml}}
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【序盤・レーン戦】</strong> ${{laningNote}}</div>
          <div style="font-size:12px; margin-bottom:6px; color:#e2e8f0; line-height:1.5;"><strong>【中終盤・集団戦】</strong> ${{tfNote}}</div>
          ${{tipNote ? `<div style="font-size:12px; color:#f59e0b; line-height:1.5;"><strong>【極意】</strong> ${{tipNote}}</div>` : ""}}
        </div>

        <!-- 実戦コンボ -->
        <div class="detail-section">
          <div class="detail-heading">🥊 実戦コンボ・スキル回し（Flash併用含む）</div>
          <div class="combo-grid">${{combosHtml}}</div>
        </div>

        <!-- 推奨スペル -->
        <div class="detail-section">
          <div class="detail-heading">⚔️ 推奨サモナースペル（${{currentSelectedRole}}運用）</div>
          <div class="spells-badge-list">${{spellsBadge}}</div>
        </div>

        <!-- 推奨ビルド (複数パターン切り替え) -->
        <div class="detail-section">
          <div class="detail-heading">🛡️ 推奨ビルド構成（複数パターン対応）</div>
          ${{buildTabsHtml}}
          ${{buildContentHtml}}
        </div>

        <!-- 対面相性 -->
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

        <!-- ルーン構成 -->
        <div class="detail-section">
          <div class="detail-heading">🔮 推奨ルーン構成</div>
          <div class="rune-row"><span class="rune-title">メインパス [${{r.primary?.path || "精密"}}]:</span><strong>${{r.primary?.keystone_name || "征服者"}}</strong> (${{priChoices}})</div>
          <div class="rune-row"><span class="rune-title">サブパス [${{r.secondary?.path || "不撓"}}]:</span>${{secChoices}}</div>
          <div class="rune-row"><span class="rune-title">シャード:</span>${{shards}}</div>
        </div>

        <!-- 全スキル詳細 -->
        <div class="detail-section">
          <div class="detail-heading">⚡ スキル詳細（Q・W・E・R・パッシブ）</div>
          ${{skillsHtml}}
        </div>
      `;

      // ロールサブタブのイベント登録
      modalBodyEl.querySelectorAll(".modal-role-btn").forEach(btn => {{
        btn.onclick = (e) => {{
          e.stopPropagation();
          const targetRole = btn.getAttribute("data-modal-role");
          openDetail(champId, targetRole);
        }};
      }});

      // ビルドパターン切り替えタブのイベント登録
      modalBodyEl.querySelectorAll(".build-pat-btn").forEach(btn => {{
        btn.onclick = (e) => {{
          e.stopPropagation();
          modalBodyEl.querySelectorAll(".build-pat-btn").forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const idx = parseInt(btn.getAttribute("data-build-idx"), 10);
          const bp = buildPatterns[idx];
          const contentBox = document.getElementById("buildPatternContent");
          if (contentBox && bp) {{
            contentBox.innerHTML = renderBuildPatternInner(bp);
            bindClickableItems(contentBox);
          }}
        }};
      }});

      // アイテムクリックイベントの登録関数
      function bindClickableItems(parentEl) {{
        parentEl.querySelectorAll(".clickable-item").forEach(el => {{
          el.onclick = (e) => {{
            e.stopPropagation();
            const itemId = el.getAttribute("data-item-id");
            if (itemId && ITEMS[itemId]) {{
              openItemDetail(itemId);
            }}
          }};
        }});
      }}
      bindClickableItems(modalBodyEl);

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

    // ==========================================
    // 対面対策シミュレーター制御 (Phase 4)
    // ==========================================
    let simMyChampId = null;
    let simOppChampId = null;
    let simCurrentPickingTarget = null; // 'me' or 'opp'
    let simPickerRole = "ALL";
    let simPickerSearch = "";

    const simCardMe = document.getElementById("simCardMe");
    const simCardOpp = document.getElementById("simCardOpp");
    const simImgMe = document.getElementById("simImgMe");
    const simImgOpp = document.getElementById("simImgOpp");
    const simNameMe = document.getElementById("simNameMe");
    const simNameOpp = document.getElementById("simNameOpp");
    const simRoleMe = document.getElementById("simRoleMe");
    const simRoleOpp = document.getElementById("simRoleOpp");

    const simEmptyPrompt = document.getElementById("simEmptyPrompt");
    const simResultArea = document.getElementById("simResultArea");
    const simAdvantageBadge = document.getElementById("simAdvantageBadge");
    const simAdvantageDesc = document.getElementById("simAdvantageDesc");
    const simSustainWarning = document.getElementById("simSustainWarning");
    const simLaningTips = document.getElementById("simLaningTips");
    const simItemList = document.getElementById("simItemList");
    const simCombosArea = document.getElementById("simCombosArea");

    const simPickerModal = document.getElementById("simPickerModal");
    const simPickerCloseBtn = document.getElementById("simPickerCloseBtn");
    const simPickerTitle = document.getElementById("simPickerTitle");
    const simSearchInput = document.getElementById("simSearchInput");
    const simPickerGrid = document.getElementById("simPickerGrid");

    function openSimPicker(target) {{
      simCurrentPickingTarget = target;
      if (simPickerTitle) {{
        simPickerTitle.textContent = target === 'me' ? '👑 あなたのチャンピオンを選択' : '👿 対面の相手チャンピオンを選択';
      }}
      if (simSearchInput) simSearchInput.value = "";
      simPickerSearch = "";
      if (simPickerModal) simPickerModal.classList.add("open");
      renderSimPickerGrid();
      if (!history.state || history.state.modal !== 'sim_picker') {{
        history.pushState({{ modal: 'sim_picker' }}, '');
      }}
    }}

    function closeSimPicker() {{
      if (simPickerModal) simPickerModal.classList.remove("open");
    }}

    if (simPickerCloseBtn) {{
      simPickerCloseBtn.onclick = () => {{
        if (history.state && history.state.modal === 'sim_picker') history.back();
        else closeSimPicker();
      }};
    }}

    if (simPickerModal) {{
      simPickerModal.onclick = (e) => {{
        if (e.target === simPickerModal) {{
          if (history.state && history.state.modal === 'sim_picker') history.back();
          else closeSimPicker();
        }}
      }};
    }}

    function renderSimPickerGrid() {{
      if (!simPickerGrid) return;
      simPickerGrid.innerHTML = "";
      const q = simPickerSearch.trim().toLowerCase();

      Object.values(CHAMPIONS).forEach(champ => {{
        // ロール絞り込み (濱田くんの重要指定！)
        if (simPickerRole !== "ALL") {{
          if (!champ.roles || !champ.roles.includes(simPickerRole)) return;
        }}

        // 検索クエリ
        if (q) {{
          const n = (champ.name || "").toLowerCase();
          const cid = (champ.id || "").toLowerCase();
          if (!n.includes(q) && !cid.includes(q)) return;
        }}

        const item = document.createElement("div");
        item.className = "sim-picker-item";
        const patch = champ.patch || "16.19.1";
        const imgUrl = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{champ.id}}.png`;

        item.innerHTML = `
          <img class="sim-picker-img" src="${{imgUrl}}" alt="${{champ.name}}" loading="lazy" onerror="this.src='icon.png';">
          <div class="sim-picker-name">${{champ.name}}</div>
        `;
        item.onclick = () => selectSimChamp(champ.id);
        simPickerGrid.appendChild(item);
      }});
    }}

    function selectSimChamp(champId) {{
      const c = CHAMPIONS[champId];
      if (!c) return;
      const patch = c.patch || "16.19.1";

      if (simCurrentPickingTarget === 'me') {{
        simMyChampId = champId;
        if (simCardMe) {{
          simCardMe.classList.remove("empty");
          simCardMe.classList.add("selected");
          const plusEl = simCardMe.querySelector(".sim-slot-plus");
          if (plusEl) plusEl.style.display = "none";
        }}
        if (simImgMe) {{
          simImgMe.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{c.id}}.png`;
          simImgMe.style.display = "block";
        }}
        if (simNameMe) simNameMe.textContent = c.name;
        if (simRoleMe) simRoleMe.textContent = c.roles ? c.roles.join(" / ") : "";
      }} else {{
        simOppChampId = champId;
        if (simCardOpp) {{
          simCardOpp.classList.remove("empty");
          simCardOpp.classList.add("selected");
          const plusEl = simCardOpp.querySelector(".sim-slot-plus");
          if (plusEl) plusEl.style.display = "none";
        }}
        if (simImgOpp) {{
          simImgOpp.src = `https://ddragon.leagueoflegends.com/cdn/${{patch}}/img/champion/${{c.id}}.png`;
          simImgOpp.style.display = "block";
        }}
        if (simNameOpp) simNameOpp.textContent = c.name;
        if (simRoleOpp) simRoleOpp.textContent = c.roles ? c.roles.join(" / ") : "";
      }}

      if (history.state && history.state.modal === 'sim_picker') history.back();
      else closeSimPicker();

      updateSimAnalysis();
    }}

    if (simSearchInput) {{
      simSearchInput.addEventListener("input", (e) => {{
        simPickerSearch = e.target.value;
        renderSimPickerGrid();
      }});
    }}

    document.querySelectorAll(".sim-role-btn").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".sim-role-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        simPickerRole = btn.getAttribute("data-sim-role");
        renderSimPickerGrid();
      }});
    }});

    function updateSimAnalysis() {{
      if (!simMyChampId || !simOppChampId) {{
        if (simEmptyPrompt) simEmptyPrompt.style.display = "block";
        if (simResultArea) simResultArea.style.display = "none";
        return;
      }}

      if (simEmptyPrompt) simEmptyPrompt.style.display = "none";
      if (simResultArea) simResultArea.style.display = "block";

      const me = CHAMPIONS[simMyChampId];
      const opp = CHAMPIONS[simOppChampId];

      // 1. 相性・勝率判定
      let advClass = "sim-adv-even";
      let advText = "五分（技量勝負）";
      let advReason = `${{me.name}} と ${{opp.name}} のマッチアップ。お互いのスキル命中精度とウェーブコントロールが勝敗を分けます。`;

      const favMatch = (me.matchups?.favorable || []).find(m => m.champion_id === opp.id || m.name === opp.name);
      const unfavMatch = (me.matchups?.unfavorable || []).find(m => m.champion_id === opp.id || m.name === opp.name);

      if (favMatch) {{
        advClass = "sim-adv-fav";
        advText = `有利（${{favMatch.reason ? favMatch.reason.split(" | ")[0] : "統計有利"}}）`;
        advReason = favMatch.reason || `統計的に ${{me.name}} が有利なマッチアップです。主導権を握ってアグレッシブに攻めましょう。`;
      }} else if (unfavMatch) {{
        advClass = "sim-adv-unfav";
        advText = `警戒・不利（${{unfavMatch.reason ? unfavMatch.reason.split(" | ")[0] : "統計不利"}}）`;
        advReason = unfavMatch.reason || `統計的に ${{opp.name}} が得意とする不利なマッチアップです。無理な仕掛けを避け、ガンクを待つ立ち回りが賢明です。`;
      }}

      if (simAdvantageBadge) {{
        simAdvantageBadge.className = `sim-adv-badge ${{advClass}}`;
        simAdvantageBadge.textContent = advText;
      }}
      if (simAdvantageDesc) simAdvantageDesc.textContent = advReason;

      // 2. 相手のサステイン警告
      if (simSustainWarning) {{
        if (opp.sustain_info && opp.sustain_info.has_sustain) {{
          simSustainWarning.style.display = "block";
          simSustainWarning.innerHTML = `🩸 <strong>【相手は高回復・サステイン持ち！】</strong> ${{opp.name}} は強力な回復能力を誇ります。${{opp.sustain_info.reason}} 早期リコール時に必ず「重傷アイテム（回復阻害）」を購入してください。`;
        }} else {{
          simSustainWarning.style.display = "none";
        }}
      }}

      // レーン戦注意点
      if (simLaningTips) {{
        const oppWeaknesses = (opp.overview?.weaknesses || []).join("、");
        simLaningTips.innerHTML = `
          <div style="margin-bottom: 6px;"><strong>【相手の弱み・突くべき隙】</strong> ${{oppWeaknesses || "主要スキルのクールダウン中が最大の仕掛けどころです。"}}</div>
          <div><strong>【あなたの立ち回り指針】</strong> ${{me.gameplay_notes?.laning || "相手のスキルを躱してからトレードに入りましょう。"}}</div>
        `;
      }}

      // 3. 対策アイテムの自動選定
      if (simItemList) {{
        const counterItems = [];
        const oppRoles = opp.roles || [];
        const oppResource = opp.resource || "";

        if (opp.sustain_info?.has_sustain) {{
          counterItems.push({{ name: "ブランブル ベスト", id: "3076", reason: "対面回復阻害(AR)" }});
          counterItems.push({{ name: "エクスキューショナー コーリング", id: "3123", reason: "対面回復阻害(AD)" }});
          counterItems.push({{ name: "忘却のオーブ", id: "3916", reason: "対面回復阻害(AP)" }});
        }}

        if (oppRoles.includes("Mage") || (oppResource.includes("マナ") && !oppRoles.includes("Marksman"))) {{
          counterItems.push({{ name: "マーキュリー ブーツ", id: "3111", reason: "魔法耐性 ＆ 行動妨害低減" }});
          counterItems.push({{ name: "ケイニック ルーコン", id: "6664", reason: "対AP最強シールド防具" }});
        }} else {{
          counterItems.push({{ name: "プレート スチールキャップ", id: "3047", reason: "通常攻撃被ダメージ低減" }});
        }}

        if (oppRoles.includes("Tank") || ["Sion", "Malphite", "ChoGath", "Ornn", "DrMundo"].includes(opp.id)) {{
          counterItems.push({{ name: "ブラック クリーバー", id: "3071", reason: "対タンク物理防御破壊" }});
          counterItems.push({{ name: "ドミニク リガード", id: "3036", reason: "対タンク割合貫通" }});
        }}

        simItemList.innerHTML = counterItems.map(it => {{
          const itemImg = `https://ddragon.leagueoflegends.com/cdn/16.19.1/img/item/${{it.id}}.png`;
          return `
            <span class="item-pill clickable-item" data-item-id="${{it.id}}" title="タップして詳細を表示">
              <img class="item-img" src="${{itemImg}}" alt="${{it.name}}" onerror="this.src='icon.png';">
              <span>${{it.name}}</span>
              <span style="font-size:10px; color:var(--accent); margin-left:2px;">(${{it.reason}})</span>
            </span>
          `;
        }}).join("");

        simItemList.querySelectorAll(".clickable-item").forEach(el => {{
          el.onclick = (e) => {{
            e.stopPropagation();
            const iid = el.getAttribute("data-item-id");
            if (iid && ITEMS[iid]) openItemDetail(iid);
          }};
        }});
      }}

      // 4. 狙い目コンボ
      if (simCombosArea) {{
        const combos = me.combos || [];
        simCombosArea.innerHTML = combos.map(cb => `
          <div class="combo-card">
            <div class="combo-name">🥊 ${{cb.name}}</div>
            <div class="combo-recipe">${{cb.recipe}}</div>
            <div class="combo-desc">${{cb.desc}}</div>
          </div>
        `).join("");
      }}
    }}

    // スマホのジェスチャースワイプ「戻る」イベント対応（アプリ終了防止・モーダル多重スタック制御）
    window.addEventListener("popstate", (e) => {{
      if (simPickerModal && simPickerModal.classList.contains("open")) {{
        closeSimPicker();
        return;
      }}
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
        if (simPickerModal && simPickerModal.classList.contains("open")) {{
          if (history.state && history.state.modal === 'sim_picker') history.back();
          else closeSimPicker();
          return;
        }}
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
    sw_content = """// LoLDB Service Worker - Offline Cache v8
const CACHE_NAME = 'loldb-cache-v8';
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
