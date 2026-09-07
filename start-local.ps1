# ローカル開発環境 起動スクリプト
# 使い方: PowerShell でこのファイルのあるフォルダに移動して .\start-local.ps1 を実行

$projectRoot = $PSScriptRoot

# FastAPI バックエンド（別ウィンドウで起動）
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectRoot'; " +
    "`$env:DISABLE_NEO4J='true'; " +
    "`$env:NEO4J_URI='bolt://localhost:7687'; " +
    "`$env:NEO4J_USER='neo4j'; " +
    "`$env:NEO4J_PASSWORD='recommendation'; " +
    "Write-Host 'FastAPI を起動しています (port 8000)...' -ForegroundColor Cyan; " +
    "py -m uvicorn api.api_server:app --host 0.0.0.0 --port 8000 --reload --reload-dir api --reload-dir engine"
)

# Next.js フロントエンド（別ウィンドウで起動）
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$projectRoot\demo-web'; " +
    "Write-Host 'Next.js を起動しています (port 3000)...' -ForegroundColor Green; " +
    "npm run dev"
)

Write-Host ""
Write-Host "=== ローカル環境を起動しました ===" -ForegroundColor Yellow
Write-Host "  バックエンド : http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  フロントエンド: http://127.0.0.1:3000" -ForegroundColor Green
Write-Host ""
Write-Host "起動完了まで 20〜30 秒お待ちください。" -ForegroundColor Yellow
Write-Host "ブラウザで http://127.0.0.1:3000 を開いてください。" -ForegroundColor Yellow
