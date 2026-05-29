# デモ起動スクリプト（API + Next.js）
# 使い方: .\start-demo.ps1

$Root = $PSScriptRoot
$ApiPort = 8000
$WebPort = 3000

function Wait-ForHttp {
    param(
        [string]$Url,
        [int]$TimeoutSec = 90
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
                return $true
            }
        } catch {
            # 接続待ち
        }
        Start-Sleep -Seconds 2
    }
    return $false
}

Write-Host "=== Decision Intelligence デモ起動 ===" -ForegroundColor Cyan
Write-Host ""

# 既存プロセス確認
$api = Get-NetTCPConnection -LocalPort $ApiPort -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $api) {
    Write-Host "[1/2] FastAPI を起動 (port $ApiPort)..." -ForegroundColor Yellow
    $env:NEO4J_PASSWORD = if ($env:NEO4J_PASSWORD) { $env:NEO4J_PASSWORD } else { "recommendation" }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Root'; `$env:NEO4J_PASSWORD='recommendation'; py -m uvicorn api.api_server:app --host 0.0.0.0 --port $ApiPort --reload --reload-exclude 'data/demo/sessions.json' --reload-exclude 'data/demo/*.json'"
    )
} else {
    Write-Host "[1/2] API は既に port $ApiPort で稼働中" -ForegroundColor Green
}

$web = Get-NetTCPConnection -LocalPort $WebPort -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $web) {
    Write-Host "[2/2] Next.js を起動 (port $WebPort)..." -ForegroundColor Yellow
    $webDir = Join-Path $Root "demo-web"
    # ビルドキャッシュは TEMP（next.config distDir）。OneDrive 上の古い .next は削除
    $nextDir = Join-Path $webDir ".next"
    if (Test-Path $nextDir) {
        Write-Host "      古い .next を削除中..." -ForegroundColor DarkGray
        Remove-Item -LiteralPath $nextDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path (Join-Path $webDir ".env.local"))) {
        if (Test-Path (Join-Path $webDir ".env.example")) {
            Copy-Item (Join-Path $webDir ".env.example") (Join-Path $webDir ".env.local")
        }
    }
    if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
        Write-Host "      npm install を実行中（初回のみ）..." -ForegroundColor DarkGray
        Push-Location $webDir
        npm install
        Pop-Location
    }
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$webDir'; npm run dev"
    )
} else {
    Write-Host "[2/2] Next.js は既に port $WebPort で稼働中" -ForegroundColor Green
}

Write-Host ""
Write-Host "起動待ち（最大90秒）..." -ForegroundColor DarkGray
$apiOk = Wait-ForHttp "http://127.0.0.1:$ApiPort/health" 60
$webOk = Wait-ForHttp "http://127.0.0.1:$WebPort/demo/opening" 90

if (-not $apiOk) {
    Write-Host "[警告] API が応答しません。別ウィンドウのエラーを確認してください。" -ForegroundColor Red
    Write-Host "  手動: http://127.0.0.1:$ApiPort/docs" -ForegroundColor DarkGray
}
if (-not $webOk) {
    Write-Host "[警告] Next.js が応答しません。demo-web ウィンドウで Ready になるまで待ってください。" -ForegroundColor Red
}

$url = "http://127.0.0.1:$WebPort/demo/opening"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " デモ URL（Chrome / Edge の通常タブで開く）" -ForegroundColor Cyan
Write-Host "  $url" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "重要:" -ForegroundColor Yellow
Write-Host "  × Cursor 内蔵ブラウザ / Simple Browser では開かないでください" -ForegroundColor Yellow
Write-Host "  ○ Chrome または Edge に上記 URL をコピー＆ペースト" -ForegroundColor Yellow
Write-Host ""

if ($webOk) {
    & (Join-Path $Root "open-demo-browser.ps1")
} else {
    Write-Host "ブラウザは自動起動しませんでした。" -ForegroundColor Yellow
    Write-Host "  demo-web ウィンドウで Ready 表示後:" -ForegroundColor Yellow
    Write-Host "  .\open-demo-browser.ps1" -ForegroundColor White
}
