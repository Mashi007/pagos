# ============================================================================
# SCRIPT DE RECONCILIACIÓN DE PAGOS - AUTOMATIZADO
# ============================================================================
# Este script automatiza la ejecución del proceso de reconciliación
# ============================================================================

param(
    [switch]$Apply = $false,
    [switch]$Help = $false
)

# Función para mostrar ayuda
function Show-Help {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "SCRIPT DE RECONCILIACIÓN DE PAGOS" -ForegroundColor Yellow
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Green
    Write-Host "  .\Ejecutar_Reconciliacion.ps1              # Modo DRY RUN (sin cambios)" -ForegroundColor White
    Write-Host "  .\Ejecutar_Reconciliacion.ps1 -Apply        # Aplicar cambios" -ForegroundColor White
    Write-Host "  .\Ejecutar_Reconciliacion.ps1 -Help         # Mostrar esta ayuda" -ForegroundColor White
    Write-Host ""
    Write-Host "Parámetros:" -ForegroundColor Green
    Write-Host "  -Apply    Aplica los cambios en la base de datos (sin esto es DRY RUN)" -ForegroundColor White
    Write-Host "  -Help     Muestra esta ayuda" -ForegroundColor White
    Write-Host ""
    Write-Host "Ejemplos:" -ForegroundColor Green
    Write-Host "  .\Ejecutar_Reconciliacion.ps1               # Ver qué haría" -ForegroundColor White
    Write-Host "  .\Ejecutar_Reconciliacion.ps1 -Apply       # Aplicar cambios" -ForegroundColor White
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

# Mostrar ayuda si se solicita
if ($Help) {
    Show-Help
    exit 0
}

# Obtener el directorio del script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Cambiar al directorio raíz del proyecto
Set-Location $ProjectRoot

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "RECONCILIACIÓN DE PAGOS CON CUOTAS" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "backend\scripts\reconciliar_pagos_cuotas.py")) {
    Write-Host "❌ ERROR: No se encontró el script de reconciliación" -ForegroundColor Red
    Write-Host "   Ruta esperada: backend\scripts\reconciliar_pagos_cuotas.py" -ForegroundColor Red
    Write-Host "   Directorio actual: $ProjectRoot" -ForegroundColor Red
    exit 1
}

# Verificar variables de entorno
$DatabaseUrl = $env:DATABASE_URL
if (-not $DatabaseUrl) {
    Write-Host "⚠️  ADVERTENCIA: DATABASE_URL no está configurada" -ForegroundColor Yellow
    Write-Host "   El script puede fallar si no está configurada" -ForegroundColor Yellow
    Write-Host ""
}

# Determinar modo de ejecución
if ($Apply) {
    Write-Host "🔴 MODO: APLICAR CAMBIOS (NO ES DRY RUN)" -ForegroundColor Red
    Write-Host ""
    Write-Host "⚠️  ADVERTENCIA: Se aplicarán cambios en la base de datos" -ForegroundColor Yellow
    Write-Host "   Asegúrate de haber hecho backup antes de continuar" -ForegroundColor Yellow
    Write-Host ""
    
    $confirmation = Read-Host "¿Deseas continuar? (escribe 'SI' para confirmar)"
    if ($confirmation -ne "SI") {
        Write-Host "❌ Operación cancelada por el usuario" -ForegroundColor Red
        exit 0
    }
    
    $Mode = "APLICAR"
} else {
    Write-Host "🟢 MODO: DRY RUN (solo verificación, sin cambios)" -ForegroundColor Green
    Write-Host ""
    $Mode = "DRY RUN"
}

# Intentar activar entorno virtual si existe
$VenvPath = Join-Path $ProjectRoot "venv"
if (Test-Path $VenvPath) {
    Write-Host "📦 Activando entorno virtual..." -ForegroundColor Cyan
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        Write-Host "✅ Entorno virtual activado" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No se encontró el script de activación del entorno virtual" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Determinar comando de Python
$PythonCmd = $null
$PythonCommands = @("python", "py", "python3")

foreach ($cmd in $PythonCommands) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $PythonCmd = $cmd
            Write-Host "✅ Python encontrado: $cmd" -ForegroundColor Green
            Write-Host "   Versión: $version" -ForegroundColor Gray
            break
        }
    } catch {
        continue
    }
}

if (-not $PythonCmd) {
    Write-Host "❌ ERROR: No se encontró Python instalado" -ForegroundColor Red
    Write-Host "   Por favor, instala Python o verifica que esté en el PATH" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Construir comando
$ScriptPath = Join-Path $ProjectRoot "backend\scripts\reconciliar_pagos_cuotas.py"
$Arguments = @()

if ($Apply) {
    $Arguments += "--apply"
}

Write-Host "🚀 Ejecutando script de reconciliación..." -ForegroundColor Cyan
Write-Host "   Comando: $PythonCmd $ScriptPath $($Arguments -join ' ')" -ForegroundColor Gray
Write-Host ""

# Ejecutar script
try {
    & $PythonCmd $ScriptPath $Arguments
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "============================================================================" -ForegroundColor Cyan
        Write-Host "✅ PROCESO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
        Write-Host "============================================================================" -ForegroundColor Cyan
        Write-Host ""
        
        if ($Apply) {
            Write-Host "📊 Los cambios han sido aplicados en la base de datos" -ForegroundColor Green
            Write-Host "   Ejecuta las queries de verificación en DBeaver para confirmar" -ForegroundColor Yellow
        } else {
            Write-Host "📊 Revisa los resultados del DRY RUN arriba" -ForegroundColor Yellow
            Write-Host "   Si los resultados son correctos, ejecuta con -Apply para aplicar cambios" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "============================================================================" -ForegroundColor Cyan
        Write-Host "❌ ERROR: El script falló con código de salida $LASTEXITCODE" -ForegroundColor Red
        Write-Host "============================================================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Revisa los mensajes de error arriba para más detalles" -ForegroundColor Yellow
        exit $LASTEXITCODE
    }
} catch {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "❌ ERROR: No se pudo ejecutar el script" -ForegroundColor Red
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
