# one-off: patch PrestamoDetalleModal - run from repo root: python backend/_edit_modal_patch.py
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "frontend/src/components/prestamos/PrestamoDetalleModal.tsx"
t = p.read_text(encoding="utf-8")

old = """                    {/* Orden lógico: Requerimiento (solicitud) → Aprobación. La tabla de amortización usa fecha de aprobación (o fecha_base_calculo) como base. */}
                    <div className="min-w-0">
                      <label className="text-sm text-gray-600">Fecha de Requerimiento</label>
                      <p className="font-medium">{prestamoData.fecha_requerimiento ? formatDate(prestamoData.fecha_requerimiento) : '-'}</p>
                    </div>
                    {prestamoData.fecha_aprobacion && (
                      <div className="min-w-0">
                        <label className="text-sm text-gray-600">Fecha de Aprobación</label>
                        <p className="font-medium">{formatDate(prestamoData.fecha_aprobacion)}</p>
                        <p className="text-xs text-gray-500 mt-0.5">Base para vencimientos de la tabla de amortización</p>
                      </div>
                    )}
                    {prestamoData.fecha_base_calculo && (
                      <div className="min-w-0">
                        <label className="text-sm text-gray-600">Fecha Base de Cálculo</label>
                        <p className="font-medium">{formatDate(prestamoData.fecha_base_calculo)}</p>
                        <p className="text-xs text-gray-500 mt-0.5">Solo informativa; la tabla de amortización usa únicamente la Fecha de Aprobación.</p>
                      </div>
                    )}
                    {/* Aviso solo para datos legacy: aprobación anterior a requerimiento (desde ahora el sistema exige coherencia) */}
                    {prestamoData.fecha_requerimiento && prestamoData.fecha_aprobacion && (() => {
                      const req = new Date(prestamoData.fecha_requerimiento).getTime()
                      const apr = new Date(prestamoData.fecha_aprobacion).getTime()
                      if (apr < req) {
                        return (
                          <div className="col-span-2 mt-2 p-3 rounded-md bg-amber-50 border border-amber-200 flex items-start gap-2">
                            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                            <p className="text-sm text-amber-800">
                              La fecha de aprobación es anterior a la de requerimiento. Corrija en Revisión Manual o edición del préstamo.
                            </p>
                          </div>
                        )
                      }
                      return null
                    })()}"""

new = """                    <div className="min-w-0">
                      <label className="text-sm text-gray-600">Fecha de Aprobación</label>
                      <p className="font-medium">
                        {prestamoData.fecha_aprobacion ? formatDate(prestamoData.fecha_aprobacion) : '-'}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">Base para vencimientos de la tabla de amortización</p>
                    </div>"""

if old not in t:
    # try mojibake version from file on disk
    old_b = old.replace("ó", "A3").replace("í", "A-").replace("ú", "A").replace("ñ", "A")
    # file might have prA3stamo etc - read raw snippet
    raise SystemExit("EXACT_BLOCK_NOT_FOUND")

t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("patched utf8")
