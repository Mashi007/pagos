# Arrancar el backend FastAPI (ejecutar desde backend o desde la raíz del repo)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
python -m uvicorn app.main:app --reload --port 8000
