# Script PowerShell robusto para ejecutar comandos de Alembic
# Usa el script Python alembic_robust.py que evita congelamientos con timeouts

param(
    [Parameter(Position=0)]
    [string]$Comando = "current",
    
    [Parameter(Position=1)]
    [string[]]$Argumentos = @(),
    
    [int]$Timeout = 30
)

# Guardar el directorio actual
$originalLocation = Get-Location

try {
    # Cambiar al directorio backend
    $backendPath = Join-Path $PSScriptRoot ".." ".." "backend"
    $backendPath = Resolve-Path $backendPath -ErrorAction Stop
    Set-Location $backendPath
    Write-Host "📁 Directorio: $backendPath" -ForegroundColor Green
    Write-Host ""
    
    # Construir comando Python
    $scriptPath = Join-Path $backendPath "scripts" "alembic_robust.py"
    
    if (-not (Test-Path $scriptPath)) {
        Write-Host "❌ Error: No se encontró alembic_robust.py en $scriptPath" -ForegroundColor Red
        exit 1
    }
    
    # Construir argumentos
    $pythonArgs = @($Comando) + $Argumentos
    if ($Timeout -ne 30) {
        $pythonArgs += "--timeout", $Timeout
    }
    
    Write-Host "🚀 Ejecutando: python scripts\alembic_robust.py $($pythonArgs -join ' ')" -ForegroundColor Cyan
    Write-Host ""
    
    # Ejecutar script Python
    $result = python $scriptPath $pythonArgs 2>&1
    
    # Mostrar resultado
    $result | ForEach-Object {
        if ($_ -match "\[ERROR\]") {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "\[WARNING\]") {
            Write-Host $_ -ForegroundColor Yellow
        } elseif ($_ -match "\[SUCCESS\]|\[INFO\]") {
            Write-Host $_ -ForegroundColor Green
        } else {
            Write-Host $_
        }
    }
    
    exit $LASTEXITCODE
}
catch {
    Write-Host ""
    Write-Host "❌ Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Volver al directorio original
    Set-Location $originalLocation
}

