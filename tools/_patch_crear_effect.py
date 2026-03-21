# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/prestamos/CrearPrestamoForm.tsx"
t = p.read_text(encoding="utf-8")
old = """  useEffect(() => {
    const cuota = Number.isFinite(cuotaPeriodo) ? Math.max(0, cuotaPeriodo) : 0
    const n =
      Number.isFinite(numeroCuotas) && numeroCuotas > 0 ? numeroCuotas : 0
    const totalFin = n > 0 ? Math.round(cuota * n * 100) / 100 : 0
    const va = Number.isFinite(valorActivo) ? Math.max(0, valorActivo) : 0
    const ant = Math.round(Math.max(0, va - totalFin) * 100) / 100
    setAnticipo(ant)
    setFormData(prev => ({
      ...prev,
      total_financiamiento: totalFin,
    }))
  }, [cuotaPeriodo, numeroCuotas, valorActivo])"""
new = """  useEffect(() => {
    const cuota = Number.isFinite(cuotaPeriodo) ? Math.max(0, cuotaPeriodo) : 0
    const n =
      Number.isFinite(numeroCuotas) && numeroCuotas > 0 ? numeroCuotas : 0
    const va = Number.isFinite(valorActivo) ? Math.max(0, valorActivo) : 0
    if (cuota <= 0 || n <= 0) {
      setAnticipo(0)
      setFormData(prev => ({
        ...prev,
        total_financiamiento: 0,
      }))
      return
    }
    const totalFin = Math.round(cuota * n * 100) / 100
    const ant = Math.round(Math.max(0, va - totalFin) * 100) / 100
    setAnticipo(ant)
    setFormData(prev => ({
      ...prev,
      total_financiamiento: totalFin,
    }))
  }, [cuotaPeriodo, numeroCuotas, valorActivo])"""
if old not in t:
    raise SystemExit("effect block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok effect")
