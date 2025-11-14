# Script para ejecutar migraciones de Alembic
# Este script evita el error de serialización de Cursor ejecutando las migraciones directamente

param(
    [string]$Action = "upgrade",
    [string]$Target = "head",
    [switch]$Check,
    [switch]$History,
    [switch]$Current,
    [switch]$SQL,
    [switch]$Status,
    [switch]$VerYMigrar
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GESTOR DE MIGRACIONES ALEMBIC" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Guardar el directorio actual
$originalLocation = Get-Location

try {
    # Cambiar al directorio backend
    $backendPath = Join-Path $PSScriptRoot ".." ".." "backend"
    $backendPath = Resolve-Path $backendPath -ErrorAction Stop
    Set-Location $backendPath
    Write-Host "📁 Directorio: $backendPath" -ForegroundColor Green
    Write-Host ""

    # Verificar que alembic.ini existe
    if (-not (Test-Path "alembic.ini")) {
        Write-Host "❌ Error: alembic.ini no encontrado en $backendPath" -ForegroundColor Red
        exit 1
    }

    # Verificar que existe el directorio de migraciones
    if (-not (Test-Path "alembic\versions")) {
        Write-Host "❌ Error: Directorio alembic\versions no encontrado" -ForegroundColor Red
        exit 1
    }

    # Determinar qué comando ejecutar
    if ($VerYMigrar) {
        # Mostrar estado completo y luego migrar
        Write-Host "📊 ESTADO ACTUAL DE MIGRACIONES" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        
        # Migración actual
        Write-Host "📍 Migración actual aplicada:" -ForegroundColor Yellow
        py -m alembic current
        Write-Host ""
        
        # Heads (migraciones disponibles)
        Write-Host "🎯 Migraciones disponibles (heads):" -ForegroundColor Yellow
        py -m alembic heads
        Write-Host ""
        
        # Historial reciente
        Write-Host "📜 Últimas 5 migraciones del historial:" -ForegroundColor Yellow
        py -m alembic history --verbose | Select-Object -First 10
        Write-Host ""
        
        # Preguntar si quiere continuar
        Write-Host "========================================" -ForegroundColor Cyan
        $respuesta = Read-Host "¿Deseas ejecutar las migraciones pendientes? (S/N)"
        
        if ($respuesta -eq "S" -or $respuesta -eq "s" -or $respuesta -eq "Y" -or $respuesta -eq "y") {
            Write-Host ""
            Write-Host "⬆️  Ejecutando migraciones..." -ForegroundColor Yellow
            Write-Host ""
            py -m alembic upgrade head
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ Migraciones ejecutadas exitosamente" -ForegroundColor Green
                Write-Host ""
                Write-Host "Estado final:" -ForegroundColor Cyan
                py -m alembic current
            } else {
                Write-Host ""
                Write-Host "❌ Error ejecutando migraciones" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host ""
            Write-Host "⏸️  Migraciones canceladas por el usuario" -ForegroundColor Yellow
        }
        exit 0
    }
    elseif ($Status) {
        # Mostrar solo el estado
        Write-Host "📊 ESTADO DE MIGRACIONES" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "📍 Migración actual:" -ForegroundColor Yellow
        py -m alembic current
        Write-Host ""
        
        Write-Host "🎯 Migraciones disponibles (heads):" -ForegroundColor Yellow
        py -m alembic heads
        Write-Host ""
        
        Write-Host "📜 Historial completo:" -ForegroundColor Yellow
        py -m alembic history
        exit 0
    }
    elseif ($Check) {
        Write-Host "🔍 Verificando migraciones..." -ForegroundColor Yellow
        Write-Host ""
        python check_migrations.py
        exit $LASTEXITCODE
    }
    elseif ($History) {
        Write-Host "📜 Historial de migraciones:" -ForegroundColor Yellow
        Write-Host ""
        py -m alembic history
        exit $LASTEXITCODE
    }
    elseif ($Current) {
        Write-Host "📍 Migración actual:" -ForegroundColor Yellow
        Write-Host ""
        py -m alembic current
        exit $LASTEXITCODE
    }
    elseif ($SQL) {
        Write-Host "📝 Generando SQL (sin ejecutar):" -ForegroundColor Yellow
        Write-Host ""
        py -m alembic upgrade $Target --sql
        exit $LASTEXITCODE
    }
    elseif ($Action -eq "upgrade") {
        Write-Host "⬆️  Ejecutando migraciones hacia: $Target" -ForegroundColor Yellow
        Write-Host ""
        
        # Mostrar estado actual primero
        Write-Host "Estado actual:" -ForegroundColor Cyan
        py -m alembic current
        Write-Host ""
        
        # Ejecutar migraciones
        if ($Target -eq "head") {
            Write-Host "Ejecutando todas las migraciones pendientes..." -ForegroundColor Yellow
        } else {
            Write-Host "Ejecutando migraciones hasta: $Target" -ForegroundColor Yellow
        }
        Write-Host ""
        
        py -m alembic upgrade $Target
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "✅ Migraciones ejecutadas exitosamente" -ForegroundColor Green
            Write-Host ""
            Write-Host "Estado final:" -ForegroundColor Cyan
            py -m alembic current
        } else {
            Write-Host ""
            Write-Host "❌ Error ejecutando migraciones" -ForegroundColor Red
            exit 1
        }
    }
    elseif ($Action -eq "downgrade") {
        Write-Host "⬇️  Revirtiendo migraciones hacia: $Target" -ForegroundColor Yellow
        Write-Host ""
        py -m alembic downgrade $Target
        exit $LASTEXITCODE
    }
    else {
        Write-Host "❌ Acción no reconocida: $Action" -ForegroundColor Red
        Write-Host ""
        Write-Host "Uso:" -ForegroundColor Yellow
        Write-Host "  .\ejecutar_migraciones_alembic.ps1                    # Ejecutar todas las migraciones"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -VerYMigrar        # Ver estado y luego migrar (RECOMENDADO)"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -Status             # Ver solo el estado"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -Check             # Verificar migraciones"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -History           # Ver historial"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -Current            # Ver migración actual"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -SQL               # Ver SQL sin ejecutar"
        Write-Host "  .\ejecutar_migraciones_alembic.ps1 -Action downgrade -Target -1  # Revertir última"
        exit 1
    }
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

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "COMPLETADO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

