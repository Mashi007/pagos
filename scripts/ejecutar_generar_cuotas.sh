#!/bin/bash
# ============================================================================
# Script Bash para generar cuotas de préstamos faltantes
# ============================================================================

echo "Ejecutando generación de cuotas para préstamos faltantes..."
echo ""

export PYTHONUNBUFFERED=1
python scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py --yes

echo ""
echo "Proceso completado."
