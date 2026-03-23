# Ejecuta la verificación Cascada solo después de escribir "fin"
# Uso: .\run_verificar_fifo.ps1
# Requiere: variable de entorno DATABASE_URL o archivo .env en backend/

$palabra = ""
while ($palabra -ne "fin") {
    $palabra = Read-Host "Escriba 'fin' para ejecutar la verificación Cascada"
    $palabra = $palabra.Trim().ToLowerInvariant()
}
Write-Host "Ejecutando verificación Cascada..." -ForegroundColor Green

$backendDir = Join-Path $PSScriptRoot ".." "backend"
$envFile = Join-Path $backendDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}
$dbUrl = $env:DATABASE_URL
if (-not $dbUrl) {
    Write-Host "ERROR: DATABASE_URL no definida. Definala en .env o en el sistema." -ForegroundColor Red
    exit 1
}
$sqlPath = Join-Path $PSScriptRoot "verificar_fifo_cuotas.sql"
& psql $dbUrl -f $sqlPath
exit $LASTEXITCODE
