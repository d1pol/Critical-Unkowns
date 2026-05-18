$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$App = Join-Path $ProjectRoot "app.py"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Could not find project Python at $Python"
}

if (-not (Test-Path -LiteralPath $App)) {
    throw "Could not find Streamlit app at $App"
}

Set-Location -LiteralPath $ProjectRoot
& $Python -m streamlit run $App --server.port 8501 --server.headless true --browser.gatherUsageStats false
