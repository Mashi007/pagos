# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend/src/components/prestamos/CrearPrestamoForm.tsx"
t = p.read_text(encoding="utf-8")
old = """                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Anticipo (USD){' '}
                      <span className="text-green-600">(Automático - 30%)</span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min={
                        valorActivo > 0 ? (valorActivo * 0.3).toFixed(2) : '0'
                      }
                      value={anticipo === 0 ? '' : anticipo.toFixed(2)}
                      onChange={e => {
                        const value = e.target.value

                        const numericValue =
                          value === '' ? 0 : parseFloat(value)

                        if (!isNaN(numericValue) && numericValue >= 0) {
                          setAnticipo(numericValue)
                        }
                      }}
                      onBlur={e => {
                        const value = parseFloat(e.target.value)

                        const anticipoMinimo =
                          valorActivo > 0 ? valorActivo * 0.3 : 0

                        // Si el valor es menor al mínimo, establecer el mínimo

                        if (!isNaN(value) && value < anticipoMinimo) {
                          setAnticipo(anticipoMinimo)

                          toast.warning(
                            `El anticipo mínimo es ${anticipoMinimo.toFixed(2)} USD (30% del valor activo)`
                          )
                        } else if (!isNaN(value) && value >= anticipoMinimo) {
                          setAnticipo(value)
                        }
                      }}
                      disabled={isReadOnly}
                      placeholder="Mínimo 30% del Valor Activo"
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      {valorActivo > 0
                        ? `Mínimo: ${(valorActivo * 0.3).toFixed(2)} USD (30% del Valor Activo)`
                        : '30% del Valor Activo'}
                    </p>
                  </div>"""
new = """                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Anticipo (USD){' '}
                      <span className="text-green-600">
                        (Calculado: Valor Activo - Cuota x Cuotas)
                      </span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={anticipo === 0 ? '' : anticipo.toFixed(2)}
                      readOnly
                      className="bg-gray-100"
                      disabled={isReadOnly}
                      placeholder="Se calcula al ingresar cuota y cuotas"
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      Anticipo = Valor Activo menos (Cuota por periodo x Numero de
                      cuotas). Total financiamiento = cuota x cuotas.
                    </p>
                  </div>"""
if old not in t:
    raise SystemExit("anticipo UI block not found")
t = t.replace(old, new, 1)

old2 = """                    <p className="mt-1 text-xs text-gray-500">
                      Calculado automáticamente (Valor Activo - Anticipo)
                    </p>"""
new2 = """                    <p className="mt-1 text-xs text-gray-500">
                      Cuota por periodo x Numero de cuotas (sincronizado con Anticipo)
                    </p>"""
if old2 not in t:
    raise SystemExit("total helper text not found")
t = t.replace(old2, new2, 1)

old3 = """                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Cuota por Período (USD)
                    </label>

                    <Input
                      value={cuotaPeriodo.toFixed(2)}
                      disabled
                      className="bg-gray-50"
                    />
                  </div>"""
new3 = """                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Cuota por Periodo (USD){' '}
                      <span className="text-red-500">*</span>{' '}
                      <span className="text-blue-600">(Manual)</span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={
                        cuotaPeriodo === 0
                          ? ''
                          : Number.isFinite(cuotaPeriodo)
                            ? cuotaPeriodo
                            : ''
                      }
                      onChange={e => {
                        const raw = e.target.value
                        if (raw === '') {
                          setCuotaPeriodo(0)
                          return
                        }
                        const v = parseFloat(raw)
                        if (!Number.isNaN(v) && v >= 0) setCuotaPeriodo(v)
                      }}
                      disabled={isReadOnly}
                      placeholder="Ingrese la cuota por periodo"
                    />
                  </div>"""
if old3 not in t:
    raise SystemExit("cuota input block not found")
t = t.replace(old3, new3, 1)

p.write_text(t, encoding="utf-8")
print("ok ui")
