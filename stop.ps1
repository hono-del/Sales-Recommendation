# =============================================================================
# stop.ps1 - Decision Intelligence PoC 停止スクリプト
# =============================================================================
Write-Host ""
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host "  Decision Intelligence PoC -- 停止スクリプト     " -ForegroundColor Yellow
Write-Host "===================================================" -ForegroundColor Yellow
Write-Host ""

$sl = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
if ($sl) {
    $sl | Stop-Process -Force
    Write-Host "  OK: Streamlit を停止しました" -ForegroundColor Green
} else {
    Write-Host "  -- Streamlit は起動していません" -ForegroundColor DarkGray
}

$uv = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uv) {
    $uv | Stop-Process -Force
    Write-Host "  OK: API サーバー (uvicorn) を停止しました" -ForegroundColor Green
} else {
    Write-Host "  -- API サーバーは起動していません" -ForegroundColor DarkGray
}

Write-Host "  Neo4j コンテナを停止中..." -ForegroundColor Yellow
docker stop neo4j-poc
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Neo4j コンテナを停止しました" -ForegroundColor Green
} else {
    Write-Host "  [警告] Neo4j 停止に失敗しました" -ForegroundColor Red
}

Write-Host ""
Write-Host "  全サービスを停止しました。" -ForegroundColor Cyan
Write-Host "  再起動するには .\start.ps1 を実行してください。" -ForegroundColor DarkGray
Write-Host ""