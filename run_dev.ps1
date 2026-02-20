# Stop any process listening on 8000
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Ensure UTF-8 output for correct accent display in PowerShell
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# CORS config (adjust origins as needed)
$env:CORS_ALLOW_ALL="true"
$env:CORS_ORIGINS=""

# Load Gemini key from user env if not present (setx writes to user scope)
if (-not $env:GEMINI_API_KEY) {
  $key = [System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
  if ($key) {
    $env:GEMINI_API_KEY = $key
  }
}

# Start server (bind to LAN)
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
