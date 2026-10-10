@echo off
chcp 65001 > nul
title LoLDB Netlify デプロイ準備

echo ========================================================
echo   LoLDB (v1.8.0) Netlify デプロイ準備アシスト
echo ========================================================
echo.
echo 1. Netlify の管理画面（ブラウザ）を自動で開きます...
start https://app.netlify.com

echo 2. アップロード対象の「dist」フォルダを開いて選択します...
explorer.exe /select,"C:\Project\LoLDB\dist"

echo.
echo --------------------------------------------------------
echo 【操作手順】
echo 1. ブラウザに表示された Netlify のサイト画面（Deploysタブ）を開きます。
echo 2. 下部の点線枠（Need to update your site? ...）へ、
echo    今エクスプローラーでハイライトされている「dist」フォルダを
echo    そのままドラッグ＆ドロップしてください。
echo.
echo ※ ドロップ後、数秒で v1.8.0 の全世界公開が完了します！
echo --------------------------------------------------------
echo.
pause
