# ============================================================================
# VERIFICAR PROGRESO DE IMPORTACIÓN DESDE POWERSHELL
# ============================================================================
# Ejecuta este script para ver el progreso de la importación en tiempo real
# ============================================================================

# Configuración de conexión (ajusta según tu configuración)
$env:DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$env:DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$env:DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "pagos_db_zjer" }
$env:DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$env:DB_PASSWORD = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "" }

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE PROGRESO DE IMPORTACIÓN" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Intentar usar psql si está disponible
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue

if ($psqlPath) {
    Write-Host "Usando psql para verificar progreso..." -ForegroundColor Green
    Write-Host ""
    
    # Construir comando psql
    $psqlCmd = "psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -c"
    
    # Query para verificar progreso
    $query = @"
SELECT 
    COUNT(*) AS filas_importadas,
    ROUND(COUNT(*) * 100.0 / 4800, 1) AS porcentaje_completado,
    CASE 
        WHEN COUNT(*) = 0 THEN '⏳ Esperando inicio...'
        WHEN COUNT(*) < 4800 THEN CONCAT('⏳ En progreso: ', COUNT(*)::text, ' de 4,800 (', ROUND(COUNT(*) * 100.0 / 4800, 1)::text, '%)')
        WHEN COUNT(*) = 4800 THEN '✅ IMPORTACIÓN COMPLETA'
        ELSE CONCAT('⚠️ ', COUNT(*)::text, ' filas (más de lo esperado)')
    END AS estado
FROM tabla_comparacion_externa;
"@
    
    # Ejecutar con contraseña si está configurada
    if ($env:DB_PASSWORD) {
        $env:PGPASSWORD = $env:DB_PASSWORD
    }
    
    Write-Host "Ejecutando verificación..." -ForegroundColor Yellow
    Write-Host ""
    
    # Ejecutar query
    $result = & psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -t -A -c $query
    
    Write-Host $result
    Write-Host ""
    
} else {
    # Alternativa usando Python si psql no está disponible
    Write-Host "psql no encontrado. Usando Python..." -ForegroundColor Yellow
    Write-Host ""
    
    $pythonScript = @"
import sys
import os
from pathlib import Path

# Agregar ruta del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    resultado = db.execute(text("""
        SELECT 
            COUNT(*) AS filas_importadas,
            ROUND(COUNT(*) * 100.0 / 4800.0, 1) AS porcentaje_completado,
            CASE 
                WHEN COUNT(*) = 0 THEN '⏳ Esperando inicio...'
                WHEN COUNT(*) < 4800 THEN CONCAT('⏳ En progreso: ', COUNT(*)::text, ' de 4,800 (', ROUND(COUNT(*) * 100.0 / 4800.0, 1)::text, '%)')
                WHEN COUNT(*) = 4800 THEN '✅ IMPORTACIÓN COMPLETA'
                ELSE CONCAT('⚠️ ', COUNT(*)::text, ' filas (más de lo esperado)')
            END AS estado
        FROM tabla_comparacion_externa
    """))
    
    row = resultado.fetchone()
    filas, porcentaje, estado = row
    
    print("=" * 70)
    print("PROGRESO DE IMPORTACIÓN")
    print("=" * 70)
    print(f"Filas importadas: {filas:,}")
    print(f"Porcentaje completado: {porcentaje}%")
    print(f"Estado: {estado}")
    print("=" * 70)
    
    # Verificación adicional
    resultado2 = db.execute(text("""
        SELECT 
            COUNT(*) AS total_filas,
            COUNT(DISTINCT cedula) AS cedulas_unicas,
            MAX(abonos) AS max_abonos,
            SUM(abonos) AS total_abonos_sum
        FROM tabla_comparacion_externa
    """))
    
    row2 = resultado2.fetchone()
    total, cedulas, max_abonos, total_abonos = row2
    
    print("")
    print("VERIFICACIÓN ADICIONAL:")
    print(f"  Total filas: {total:,}")
    print(f"  Cédulas únicas: {cedulas:,}")
    print(f"  Máximo abonos: {max_abonos:,}" if max_abonos else "  Máximo abonos: NULL")
    print(f"  Total abonos: {total_abonos:,}" if total_abonos else "  Total abonos: NULL")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
"@
    
    # Guardar script temporal
    $tempScript = Join-Path $env:TEMP "verificar_progreso_temp.py"
    $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8
    
    # Ejecutar Python
    $pythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonPath) {
        $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
    }
    
    if ($pythonPath) {
        Write-Host "Ejecutando verificación con Python..." -ForegroundColor Yellow
        Write-Host ""
        python $tempScript
        Remove-Item $tempScript -ErrorAction SilentlyContinue
    } else {
        Write-Host "Error: No se encontró Python ni psql instalado." -ForegroundColor Red
        Write-Host ""
        Write-Host "Opciones:" -ForegroundColor Yellow
        Write-Host "1. Instalar PostgreSQL client tools (psql)" -ForegroundColor White
        Write-Host "2. Usar Python para ejecutar el script" -ForegroundColor White
        Write-Host "3. Verificar directamente en DBeaver con SQL:" -ForegroundColor White
        Write-Host ""
        Write-Host "SELECT COUNT(*) AS filas_importadas FROM tabla_comparacion_externa;" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Para verificar en tiempo real, ejecuta este script cada 30 segundos" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
