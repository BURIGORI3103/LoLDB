import shutil
import zipfile
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent
MIGRATION_DIR = BASE_DIR / "dist_old_url_migration"
DIST_DIR = BASE_DIR / "dist"
DESKTOP_DIR = Path(r"C:\Users\gorir\Desktop")

NEW_URL = "https://burigori3103.github.io/LoLDB/"

def build_migration_package():
    print(f"旧URL専用移転パッケージフォルダを作成中: {MIGRATION_DIR}")
    if MIGRATION_DIR.exists():
        shutil.rmtree(MIGRATION_DIR)
    MIGRATION_DIR.mkdir(parents=True, exist_ok=True)

    # 1. index.html の作成 (クリーンアップ＆リダイレクトUI)
    index_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>LoLDB は移転しました — 新URLへ移動します</title>
  <link rel="icon" href="icon.png" type="image/png">
  <style>
    :root {{
      --bg-main: #090e17;
      --bg-card: #111a2e;
      --border-color: #1e293b;
      --primary: #c89b3c;
      --primary-light: #f0e6d2;
      --accent-blue: #0ea5e9;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    body {{
      background: radial-gradient(circle at 50% 20%, #172554 0%, var(--bg-main) 70%);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .container {{
      max-width: 520px;
      width: 100%;
      background: var(--bg-card);
      border: 1px solid rgba(200, 155, 60, 0.35);
      border-radius: 16px;
      padding: 32px 24px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6), 0 0 25px rgba(200, 155, 60, 0.15);
      text-align: center;
      animation: fadeIn 0.4s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(12px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .badge {{
      display: inline-block;
      padding: 5px 12px;
      background: rgba(200, 155, 60, 0.15);
      border: 1px solid var(--primary);
      border-radius: 9999px;
      color: var(--primary-light);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.05em;
      margin-bottom: 16px;
    }}
    .title {{
      font-size: 22px;
      font-weight: 800;
      color: #fff;
      line-height: 1.4;
      margin-bottom: 12px;
    }}
    .desc {{
      font-size: 14px;
      color: var(--text-muted);
      line-height: 1.6;
      margin-bottom: 24px;
    }}
    .url-box {{
      background: rgba(15, 23, 42, 0.7);
      border: 1px dashed rgba(200, 155, 60, 0.4);
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 24px;
      word-break: break-all;
    }}
    .url-box-label {{
      font-size: 11px;
      font-weight: 600;
      color: var(--primary);
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .url-box-link {{
      color: var(--accent-blue);
      font-size: 14px;
      font-weight: 600;
      text-decoration: none;
    }}
    .url-box-link:hover {{
      text-decoration: underline;
    }}
    .btn-main {{
      display: block;
      width: 100%;
      padding: 14px 20px;
      background: linear-gradient(135deg, #c89b3c 0%, #785a28 100%);
      color: #fff;
      font-size: 16px;
      font-weight: 800;
      text-decoration: none;
      border-radius: 10px;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(200, 155, 60, 0.35);
      transition: all 0.2s ease;
      margin-bottom: 16px;
    }}
    .btn-main:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(200, 155, 60, 0.5);
    }}
    .countdown {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 20px;
    }}
    .countdown span {{
      color: var(--primary-light);
      font-weight: bold;
      font-size: 15px;
    }}
    .notice-card {{
      background: rgba(14, 165, 233, 0.08);
      border-left: 3px solid var(--accent-blue);
      border-radius: 6px;
      padding: 12px;
      font-size: 12px;
      color: #cbd5e1;
      text-align: left;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">📢 サーバー移転のお知らせ</div>
    <h1 class="title">本アプリ（LoLDB）は<br>新しいURLへ移動しました</h1>
    <p class="desc">
      LoLDB は安定したサービス配信とオフラインPWA自動更新のため、公式配信基盤（GitHub Pages）へ完全移行いたしました。
    </p>

    <div class="url-box">
      <div class="url-box-label">新URL（ブックマークの登録をお願いします）</div>
      <a href="{NEW_URL}" class="url-box-link" id="newUrlLink">{NEW_URL}</a>
    </div>

    <a href="{NEW_URL}" class="btn-main" id="jumpBtn">🚀 今すぐ新しいサイトへ移動する</a>

    <div class="countdown">
      <span id="timer">5</span> 秒後に自動的に移動します...
    </div>

    <div class="notice-card">
      💡 <strong>スマートフォンのホーム画面に追加されている方へ：</strong><br>
      旧URL側のアイコンは削除し、新URLを開いた後に改めてブラウザの「ホーム画面に追加」を行ってください。古いキャッシュは自動的にクリーンアップされます。
    </div>
  </div>

  <script>
    // 1. 旧PWAの古いキャッシュとServiceWorkerを完全にクリア
    if ('caches' in window) {{
      caches.keys().then(keys => {{
        keys.forEach(k => caches.delete(k));
      }});
    }}
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.getRegistrations().then(regs => {{
        regs.forEach(reg => reg.unregister());
      }});
    }}

    // 2. カウントダウン＆自動リダイレクト
    let timeLeft = 5;
    const timerEl = document.getElementById("timer");
    const interval = setInterval(() => {{
      timeLeft--;
      if (timerEl) timerEl.textContent = timeLeft;
      if (timeLeft <= 0) {{
        clearInterval(interval);
        window.location.replace("{NEW_URL}");
      }}
    }}, 1000);
  </script>
</body>
</html>
"""
    (MIGRATION_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # 2. sw.js の作成 (旧Service Workerを即座にアンインストール・自滅させる)
    sw_code = f"""// Old URL Cleaner Service Worker
self.addEventListener('install', event => {{
  self.skipWaiting();
}});
self.addEventListener('activate', event => {{
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll())
      .then(clients => {{
        clients.forEach(client => client.navigate('{NEW_URL}'));
      }})
  );
}});
"""
    (MIGRATION_DIR / "sw.js").write_text(sw_code, encoding="utf-8")

    # 3. アイコン・マニフェスト類のコピー（Netlifyで404にならないよう）
    for item in ["icon.png", "og-image.png", "manifest.json"]:
        src = DIST_DIR / item
        if src.exists():
            shutil.copy(src, MIGRATION_DIR / item)

    print(f"移転パッケージファイル配置完了: {len(list(MIGRATION_DIR.glob('*')))} ファイル")

    # 4. ZIPアーカイブの作成 (プロジェクト直下のみ)
    zip_proj = BASE_DIR / "LoLDB_old_url_migration.zip"

    files_to_zip = list(MIGRATION_DIR.glob("**/*"))
    print("ZIP圧縮中...")

    with zipfile.ZipFile(zip_proj, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in tqdm(files_to_zip, desc="Project ZIP"):
            if f.is_file():
                zf.write(f, arcname=f.relative_to(MIGRATION_DIR))

    print(f"[SUCCESS] 旧URL用移転配布パッケージ完成:")
    print(f"  - フォルダ: {MIGRATION_DIR}")
    print(f"  - ZIP (プロジェクト直下): {zip_proj}")

if __name__ == "__main__":
    build_migration_package()
