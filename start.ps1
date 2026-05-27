# =============================================================================
# start.ps1 - Decision Intelligence PoC 一発起動スクリプト
# =============================================================================
#  実行方法:
#    cd <プロジェクトフォルダ>
#    .\start.ps1
#
#  前提条件:
#    - .env ファイルが存在すること（.env.example をコピーして作成）
#    - Docker Desktop が起動していること
# =============================================================================

$ROOT = $PSScriptRoot
Set-Location $ROOT

# --- .env 読み込み ------------------------------------------------------------
$envFile = "$ROOT\.env"
if (-not (Test-Path $envFile)) {
    Write-Host "[エラー] .env ファイルが見つかりません。" -ForegroundColor Red
    Write-Host "         .env.example をコピーして .env を作成し、各値を設定してください。" -ForegroundColor Red
    exit 1
}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $key, $val = $line -split '=', 2
    [System.Environment]::SetEnvironmentVariable($key.Trim(), $val.Trim(), "Process")
}

# --- LAN IP 取得 --------------------------------------------------------------
$lanIP = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Sort-Object InterfaceIndex |
    Select-Object -First 1
).IPAddress
if (-not $lanIP) { $lanIP = "localhost" }

# --- ヘッダー -----------------------------------------------------------------
Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  Decision Intelligence PoC -- 起動スクリプト     " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# --- Step 1: Neo4j コンテナ起動 ----------------------------------------------
Write-Host ""
Write-Host "[1/4] Neo4j コンテナを起動中..." -ForegroundColor Yellow
docker compose up -d neo4j
if ($LASTEXITCODE -eq 0) {
    Write-Host "      OK: neo4j-poc 起動しました" -ForegroundColor Green
} else {
    Write-Host "      [警告] Neo4j 起動失敗。docker compose logs neo4j で確認してください" -ForegroundColor Red
}

# --- Step 2: Neo4j 起動待機 --------------------------------------------------
Write-Host ""
Write-Host "[2/4] Neo4j の起動を待機中（最大 60 秒）..." -ForegroundColor Yellow
$maxWait = 60
$waited  = 0
$neo4jReady = $false
do {
    Start-Sleep -Seconds 3
    $waited += 3
    docker exec neo4j-poc cypher-shell -u neo4j -p $env:NEO4J_PASSWORD "RETURN 1" > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $neo4jReady = $true
    } else {
        Write-Host "      ... 待機中 ($waited 秒)" -ForegroundColor DarkGray
    }
} until ($neo4jReady -or $waited -ge $maxWait)

if ($neo4jReady) {
    Write-Host "      OK: Neo4j 起動完了" -ForegroundColor Green
} else {
    Write-Host "      [警告] タイムアウト -- 接続できない可能性があります" -ForegroundColor Red
}

# --- Step 3: API サーバーを別ウィンドウで起動 ---------------------------------
Write-Host ""
Write-Host "[3/4] API サーバーを起動中（別ウィンドウ）..." -ForegroundColor Yellow
Start-Process powershell.exe -ArgumentList "-NoExit", "-File", "$ROOT\_start_api.ps1"

Write-Host "      API 起動確認中（最大 60 秒）..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
$apiReady = $false
for ($i = 0; $i -lt 27; $i++) {
    $tcp = $null
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", 8000)
        if ($tcp.Connected) { $apiReady = $true; break }
    } catch {
    } finally {
        if ($tcp) { $tcp.Dispose() }
    }
    $elapsed = 5 + $i * 2
    Write-Host "      ... 待機中 ($elapsed 秒)" -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
}

if ($apiReady) {
    Write-Host "      OK: API サーバー起動完了 (port 8000)" -ForegroundColor Green
} else {
    Write-Host "      [警告] API 起動確認タイムアウト -- http://localhost:8000/docs で確認してください" -ForegroundColor Red
}

# --- 完了メッセージ -----------------------------------------------------------
Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  全サービス起動完了！" -ForegroundColor Green
Write-Host ""
Write-Host "  [このPC からアクセス]" -ForegroundColor White
Write-Host "    Streamlit UI : http://localhost:8501" -ForegroundColor White
Write-Host "    API Docs     : http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host "    Neo4j Browser: http://localhost:7474" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  [他のPC からアクセス]" -ForegroundColor White
Write-Host "    Streamlit UI : http://${lanIP}:8501" -ForegroundColor Cyan
Write-Host "    API Docs     : http://${lanIP}:8000/docs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  全サービスを停止するには .\stop.ps1 を実行してください" -ForegroundColor DarkGray
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 4: Streamlit をこのウィンドウで起動（フォアグラウンド） -----------
Write-Host "[4/4] Streamlit UI を起動中..." -ForegroundColor Yellow
Write-Host ""

& "$ROOT\.venv\Scripts\Activate.ps1"
streamlit run ui/sales_app.py --server.address 0.0.0.0 --server.port 8501
