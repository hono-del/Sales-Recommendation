# 外部ブラウザでデモを開く（Cursor 内蔵ブラウザは使わない）
# 使い方: .\open-demo-browser.ps1

$Url = "http://127.0.0.1:3000/demo/opening"
$deadline = (Get-Date).AddSeconds(90)

Write-Host "Next.js (port 3000) の起動を待っています..." -ForegroundColor Cyan
$ok = $false
while ((Get-Date) -lt $deadline) {
    $listen = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($listen) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) {
                $ok = $true
                break
            }
        } catch {
            # コンパイル中
        }
    }
    Start-Sleep -Seconds 2
}

if (-not $ok) {
    Write-Host ""
    Write-Host "[エラー] Next.js が起動していません。" -ForegroundColor Red
    Write-Host "  先に別ウィンドウで実行してください:" -ForegroundColor Yellow
    Write-Host '  cd demo-web; npm run dev' -ForegroundColor White
    Write-Host "  または: .\start-demo.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  ※ Cursor のプレビュー/内蔵ブラウザでは開けません。" -ForegroundColor Yellow
    exit 1
}

Write-Host "OK: デモに接続できました" -ForegroundColor Green
Write-Host "外部ブラウザで開きます: $Url" -ForegroundColor Cyan

# 既定ブラウザを cmd start で起動（Cursor 内 iframe を避ける）
Start-Process cmd.exe -ArgumentList @("/c", "start", "", $Url)
