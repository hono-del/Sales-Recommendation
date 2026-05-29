$Host.UI.RawUI.WindowTitle = "DI-PoC API Server (port 8000)"
$ROOT = $PSScriptRoot
Set-Location $ROOT

# .env 読み込み
foreach ($line in Get-Content "$ROOT\.env") {
    if ($line -match '^\s*#' -or $line -notmatch '=') { continue }
    $key, $val = $line -split '=', 2
    [System.Environment]::SetEnvironmentVariable($key.Trim(), $val.Trim(), "Process")
}

& "$ROOT\.venv\Scripts\Activate.ps1"
Write-Host "▶ API Server starting on http://0.0.0.0:8000" -ForegroundColor Cyan
Write-Host "  Swagger UI: http://localhost:8000/docs" -ForegroundColor DarkGray
Write-Host ""
uvicorn api.api_server:app --host 0.0.0.0 --port 8000 --reload --reload-exclude "data/demo/sessions.json" --reload-exclude "data/demo/*.json"
