# Respaldo completo BD (opción A): pg_dump -Fc
# Requisitos: pg_dump en PATH, DATABASE_URL en entorno o en .env raíz del repo

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OutDir = Join-Path $Root "backups"
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$OutFile = Join-Path $OutDir "backup_antes_regenerar_cuotas_$ts.dump"

$databaseUrl = $env:DATABASE_URL
if (-not $databaseUrl) {
    $envFile = Join-Path $Root ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*DATABASE_URL\s*=\s*(.+)$') {
                $databaseUrl = $Matches[1].Trim().Trim('"').Trim("'")
            }
        }
    }
}

if (-not $databaseUrl) {
    Write-Error "Defina DATABASE_URL o configure DATABASE_URL en .env en la raíz del proyecto."
}

if (-not (Get-Command pg_dump -ErrorAction SilentlyContinue)) {
    Write-Error "pg_dump no está en PATH. Instale PostgreSQL client tools."
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Conexión por URI
& pg_dump @("-d", $databaseUrl, "-Fc", "-f", $OutFile)
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$item = Get-Item $OutFile
$mb = [math]::Round($item.Length / 1MB, 2)
Write-Host "OK: $($item.FullName) ($mb MB)"
