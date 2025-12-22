# ============================================================================
# SCRIPT PRINCIPAL: EJECUTAR TODO EL PROCESO DE RECONCILIACIÓN
# ============================================================================
# Este script ejecuta todo el proceso de diagnóstico y reconciliación
# ============================================================================

param(
    [switch]$Apply = $false,
    [switch]$Help = $false,
    [switch]$SkipDiagnostic = $false
)

# Función para mostrar ayuda
function Show-Help {
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "SCRIPT PRINCIPAL: PROCESO COMPLETO DE RECONCILIACIÓN" -ForegroundColor Yellow
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Este script ejecuta todo el proceso de diagnóstico y reconciliación" -ForegroundColor White
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Green
    Write-Host "  .\EJECUTAR_TODO.ps1                    # Modo DRY RUN completo" -ForegroundColor White
    Write-Host "  .\EJECUTAR_TODO.ps1 -Apply             # Aplicar cambios" -ForegroundColor White
    Write-Host "  .\EJECUTAR_TODO.ps1 -SkipDiagnostic    # Saltar diagnóstico SQL" -ForegroundColor White
    Write-Host "  .\EJECUTAR_TODO.ps1 -Help              # Mostrar esta ayuda" -ForegroundColor White
    Write-Host ""
    Write-Host "Parámetros:" -ForegroundColor Green
    Write-Host "  -Apply           Aplica los cambios en la base de datos" -ForegroundColor White
    Write-Host "  -SkipDiagnostic  Salta la ejecución de queries SQL de diagnóstico" -ForegroundColor White
    Write-Host "  -Help            Muestra esta ayuda" -ForegroundColor White
    Write-Host ""
    Write-Host "Proceso:" -ForegroundColor Green
    Write-Host "  1. Ejecuta diagnóstico SQL (opcional)" -ForegroundColor White
    Write-Host "  2. Ejecuta reconciliación Python (DRY RUN o Apply)" -ForegroundColor White
    Write-Host "  3. Muestra resumen final" -ForegroundColor White
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
Write-Host "PROCESO COMPLETO DE RECONCILIACIÓN DE PAGOS" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "backend\scripts\reconciliar_pagos_cuotas.py")) {
    Write-Host "❌ ERROR: No se encontró el script de reconciliación" -ForegroundColor Red
    Write-Host "   Ruta esperada: backend\scripts\reconciliar_pagos_cuotas.py" -ForegroundColor Red
    Write-Host "   Directorio actual: $ProjectRoot" -ForegroundColor Red
    exit 1
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
} else {
    Write-Host "🟢 MODO: DRY RUN (solo verificación, sin cambios)" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# PASO 1: DIAGNÓSTICO SQL (Opcional)
# ============================================================================

if (-not $SkipDiagnostic) {
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host "PASO 1: DIAGNÓSTICO SQL" -ForegroundColor Yellow
    Write-Host "============================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📊 Para ejecutar el diagnóstico SQL completo:" -ForegroundColor Cyan
    Write-Host "   1. Abre DBeaver" -ForegroundColor White
    Write-Host "   2. Abre el archivo: scripts\sql\EJECUTAR_DIAGNOSTICO_COMPLETO.sql" -ForegroundColor White
    Write-Host "   3. Ejecuta todas las queries" -ForegroundColor White
    Write-Host "   4. Revisa los resultados" -ForegroundColor White
    Write-Host ""
    Write-Host "⚠️  Este paso es opcional pero recomendado" -ForegroundColor Yellow
    Write-Host ""
    
    $continue = Read-Host "¿Deseas continuar con la reconciliación Python? (S/N)"
    if ($continue -ne "S" -and $continue -ne "s") {
        Write-Host "❌ Proceso cancelado por el usuario" -ForegroundColor Red
        exit 0
    }
    Write-Host ""
}

# ============================================================================
# PASO 2: RECONCILIACIÓN PYTHON
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "PASO 2: RECONCILIACIÓN PYTHON" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Intentar activar entorno virtual si existe
$VenvPath = Join-Path $ProjectRoot "venv"
if (Test-Path $VenvPath) {
    Write-Host "📦 Activando entorno virtual..." -ForegroundColor Cyan
    $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        & $ActivateScript
        Write-Host "✅ Entorno virtual activado" -ForegroundColor Green
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
        Write-Host "✅ RECONCILIACIÓN COMPLETADA EXITOSAMENTE" -ForegroundColor Green
        Write-Host "============================================================================" -ForegroundColor Cyan
        Write-Host ""
        
        if ($Apply) {
            Write-Host "📊 Los cambios han sido aplicados en la base de datos" -ForegroundColor Green
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

# ============================================================================
# PASO 3: RESUMEN Y PRÓXIMOS PASOS
# ============================================================================

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "PASO 3: PRÓXIMOS PASOS" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Para verificar los resultados:" -ForegroundColor Cyan
Write-Host "   1. Abre DBeaver" -ForegroundColor White
Write-Host "   2. Ejecuta: scripts\sql\EJECUTAR_DIAGNOSTICO_COMPLETO.sql" -ForegroundColor White
Write-Host "   3. Compara los resultados con los valores iniciales" -ForegroundColor White
Write-Host ""
Write-Host "📋 Para verificación completa:" -ForegroundColor Cyan
Write-Host "   1. Ejecuta: scripts\sql\verificar_vinculacion_pagos_cuotas.sql" -ForegroundColor White
Write-Host "   2. Revisa todas las queries de verificación" -ForegroundColor White
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
