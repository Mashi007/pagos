# ============================================================================
# VERIFICACIÓN SIMPLE DE PROGRESO - POWERSHELL
# ============================================================================
# Ejecuta este script para ver cuántas filas se han importado
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE PROGRESO DE IMPORTACIÓN" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Intentar usar Python (más confiable si ya lo tienes configurado)
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
}

if ($pythonPath) {
    Write-Host "Verificando progreso con Python..." -ForegroundColor Green
    Write-Host ""
    
    # Script Python inline
    $pythonCode = @"
import sys
from pathlib import Path

project_root = Path(r'$PSScriptRoot').parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'backend'))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    resultado = db.execute(text('SELECT COUNT(*) FROM tabla_comparacion_externa'))
    filas = resultado.fetchone()[0]
    
    porcentaje = round(filas * 100.0 / 4800, 1) if filas > 0 else 0
    
    print(f'Filas importadas: {filas:,}')
    print(f'Porcentaje: {porcentaje}%')
    print(f'Faltan: {4800 - filas:,} filas')
    
    if filas == 4800:
        print('')
        print('✅ IMPORTACIÓN COMPLETA')
    elif filas > 0:
        print('')
        print('⏳ IMPORTACIÓN EN PROGRESO...')
    else:
        print('')
        print('⏳ Esperando inicio de importación...')
        
finally:
    db.close()
"@
    
    # Ejecutar
    $pythonCode | python
    
} else {
    Write-Host "Python no encontrado. Usando método alternativo..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para verificar el progreso, ejecuta en DBeaver:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "SELECT COUNT(*) AS filas_importadas FROM tabla_comparacion_externa;" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Ejecuta este script cada 30 segundos para ver el progreso" -ForegroundColor Yellow
Write-Host "============================================================================" -ForegroundColor Cyan
