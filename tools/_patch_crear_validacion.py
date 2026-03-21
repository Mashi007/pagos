# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/prestamos/CrearPrestamoForm.tsx"
t = p.read_text(encoding="utf-8")
old = """    // Validar Anticipo - debe ser al menos el 30% del valor activo

    const anticipoMinimo = valorActivo > 0 ? valorActivo * 0.3 : 0

    if (anticipo < anticipoMinimo) {
      errors.push(
        `El Anticipo debe ser al menos el 30% del Valor Activo (mínimo: ${anticipoMinimo.toFixed(2)} USD)`
      )
    }

    if (anticipo < 0) {
      errors.push('El Anticipo no puede ser negativo')
    }

    // Validar Número de Cuotas"""
new = """    // Cuota por periodo: manual; total = cuota x cuotas no puede superar el valor del activo

    if (!cuotaPeriodo || cuotaPeriodo <= 0) {
      errors.push('Ingrese la Cuota por Periodo (USD) mayor a 0')
    }

    const totalCuotas =
      Number.isFinite(cuotaPeriodo) && Number.isFinite(numeroCuotas)
        ? Math.round(cuotaPeriodo * numeroCuotas * 100) / 100
        : 0

    if (
      valorActivo > 0 &&
      totalCuotas > 0 &&
      totalCuotas > valorActivo + 0.01
    ) {
      errors.push(
        'Cuota por periodo x numero de cuotas no puede superar el Valor Activo (el anticipo quedaria negativo)'
      )
    }

    // Validar Numero de Cuotas"""
if old not in t:
    raise SystemExit("validation block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
