# デモ起動スクリプト（API + Next.js）
# 使い方: .\start-demo.ps1

$Root = $PSScriptRoot
$ApiPort = 8000
$WebPort = 3000

Write-Host "=== Decision Intelligence デモ起動 ===" -ForegroundColor Cyan

# 既存プロセス確認
$api = Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $api) {
    Write-Host "[1/2] FastAPI を起動 (port $ApiPort)..." -ForegroundColor Yellow
    $env:NEO4J_PASSWORD = if ($env:NEO4J_PASSWORD) { $env:NEO4J_PASSWORD } else { "recommendation" }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Root'; `$env:NEO4J_PASSWORD='recommendation'; py -m uvicorn api.api_server:app --host 0.0.0.0 --port $ApiPort --reload"
    )
    Start-Sleep -Seconds 3
} else {
    Write-Host "[1/2] API は既に port $ApiPort で稼働中" -ForegroundColor Green
}

$web = Get-NetTCPConnection -LocalPort $WebPort -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $web) {
    Write-Host "[2/2] Next.js を起動 (port $WebPort)..." -ForegroundColor Yellow
    $webDir = Join-Path $Root "demo-web"
    $nextDir = Join-Path $webDir ".next"
    # OneDrive 上では .next 破損で webpack runtime error になりやすいため毎回削除
    if (Test-Path $nextDir) {
        Write-Host "      .next キャッシュを削除中..." -ForegroundColor DarkGray
        Remove-Item -LiteralPath $nextDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path (Join-Path $webDir ".env.local"))) {
        Copy-Item (Join-Path $webDir ".env.example") (Join-Path $webDir ".env.local")
    }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$webDir'; npm run dev"
    )
    Start-Sleep -Seconds 8
} else {
    Write-Host "[2/2] Next.js は既に port $WebPort で稼働中" -ForegroundColor Green
}

$url = "http://localhost:$WebPort/demo/opening"
Write-Host ""
Write-Host "ブラウザで開いてください（Cursor 内蔵プレビューではなく Chrome / Edge 推奨）:" -ForegroundColor Cyan
Write-Host "  $url" -ForegroundColor White
Start-Process $url
