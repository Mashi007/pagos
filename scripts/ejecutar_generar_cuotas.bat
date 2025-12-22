@echo off
REM ============================================================================
REM Script para generar cuotas de préstamos faltantes
REM ============================================================================
echo Ejecutando generacion de cuotas para prestamos faltantes...
echo.

python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py --yes

echo.
echo Proceso completado.
pause
