from pathlib import Path

p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
t = p.read_text(encoding="utf-8")

old1 = """    fecha_requerimiento: prestamo?.fecha_requerimiento || getCurrentDate(), // Fecha actual por defecto para nuevos prAcstamos
    producto: prestamo?.producto || '',"""
new1 = """    fecha_requerimiento: prestamo?.fecha_requerimiento || getCurrentDate(), // Fecha actual por defecto para nuevos prAcstamos
    fecha_aprobacion: prestamo?.fecha_aprobacion
      ? String(prestamo.fecha_aprobacion).slice(0, 10)
      : undefined,
    producto: prestamo?.producto || '',"""
if old1 not in t:
    raise SystemExit("block1 not found")
t = t.replace(old1, new1, 1)

old2 = """        cuota_periodo: cuotaPeriodo,
        fecha_base_calculo: formData.fecha_base_calculo,
        usuario_autoriza: !prestamo && justificacionAutorizacion ? user?.email : undefined,"""
new2 = """        cuota_periodo: cuotaPeriodo,
        fecha_base_calculo: formData.fecha_base_calculo,
        ...(prestamo &&
        formData.fecha_aprobacion &&
        String(formData.fecha_aprobacion).trim() !== ""
          ? { fecha_aprobacion: String(formData.fecha_aprobacion).trim() + "T00:00:00" }
          : {}),
        usuario_autoriza: !prestamo && justificacionAutorizacion ? user?.email : undefined,"""
if old2 not in t:
    raise SystemExit("block2 not found")
t = t.replace(old2, new2, 1)

old3 = """                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Fecha de Requerimiento <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={formData.fecha_requerimiento}
                      onChange={(e) => setFormData({
                        ...formData,
                        fecha_requerimiento: e.target.value
                      })}
                      disabled={isReadOnly}
                    />
                  </div>
                </div>"""
new3 = """                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Fecha de Requerimiento <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={formData.fecha_requerimiento}
                      onChange={(e) => setFormData({
                        ...formData,
                        fecha_requerimiento: e.target.value
                      })}
                      disabled={isReadOnly}
                    />
                  </div>
                  {prestamo ? (
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Fecha de aprobación
                      </label>
                      <Input
                        type="date"
                        value={formData.fecha_aprobacion || ""}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            fecha_aprobacion: e.target.value || undefined,
                          })
                        }
                        disabled={isReadOnly}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Se guarda en BD al confirmar. Debe ser igual o posterior a la fecha de requerimiento.
                      </p>
                    </div>
                  ) : null}
                </div>"""
if old3 not in t:
    raise SystemExit("block3 not found")
t = t.replace(old3, new3, 1)

p.write_text(t, encoding="utf-8")
print("ok")
