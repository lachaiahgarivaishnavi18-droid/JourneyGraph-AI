param([switch]$Install)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if ($Install) {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv }
    & '.\.venv\Scripts\python.exe' -m pip install -r backend/requirements.lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed' }
    Push-Location frontend
    try {
        pnpm install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed' }
        pnpm build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Run .\scripts\start.ps1 -Install first to build the frontend' }
& '.\.venv\Scripts\python.exe' -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
Write-Host 'Open http://127.0.0.1:8000 . First startup prints your generated local admin password.'
& '.\.venv\Scripts\python.exe' -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
