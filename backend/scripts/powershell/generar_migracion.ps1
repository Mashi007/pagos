# Script PowerShell para generar migraciones de Alembic
# Uso: .\scripts\powershell\generar_migracion.ps1 "mensaje de migración"

param(
    [Parameter(Mandatory=$true)]
    [string]$Mensaje,
    
    [Parameter(Mandatory=$false)]
    [string]$RevId,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 60
)

# Cambiar al directorio backend
$backendDir = Join-Path $PSScriptRoot "..\.."
Push-Location $backendDir

try {
    Write-Host "[INFO] Generando migración: $Mensaje" -ForegroundColor Cyan
    
    # Construir comando
    $args = @($Mensaje)
    if ($RevId) {
        $args += "--rev-id", $RevId
    }
    if ($Timeout -ne 60) {
        $args += "--timeout", $Timeout
    }
    
    # Ejecutar script de Python
    python scripts\generar_migracion.py $args
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Migración generada exitosamente" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Error al generar migración" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

