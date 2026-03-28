# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("frontend/src/components/prestamos/CrearPrestamoForm.tsx")
text = p.read_text(encoding="utf-8")

marker = """              <CardContent className="space-y-4">
                {/* Nuevos campos: Valor Activo y Anticipo */}"""

insert = """              <CardContent className="space-y-4">
                {prestamo ? (
                  <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50/90 p-4 shadow-sm">
                    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-indigo-900">
                          Estado del préstamo
                        </p>
                        <p className="mt-0.5 text-xs text-indigo-800/90">
                          Elija el nuevo estado y confirme con el botón Actualizar
                          préstamo al final del formulario.
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className="w-fit shrink-0 border-indigo-300 bg-white text-indigo-900"
                      >
                        {String(formData.estado ?? prestamo.estado ?? 'DRAFT')}
                      </Badge>
                    </div>
                    <Select
                      value={String(
                        formData.estado ?? prestamo.estado ?? 'DRAFT'
                      )}
                      onValueChange={value =>
                        setFormData({
                          ...formData,
                          estado: value as Prestamo['estado'],
                        })
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="h-11 border-indigo-200 bg-white">
                        <SelectValue placeholder="Estado" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="DRAFT">Borrador</SelectItem>
                        <SelectItem value="EN_REVISION">En revisión</SelectItem>
                        <SelectItem value="EVALUADO">Evaluado</SelectItem>
                        <SelectItem value="APROBADO">Aprobado</SelectItem>
                        <SelectItem value="LIQUIDADO">Liquidado</SelectItem>
                        <SelectItem value="DESISTIMIENTO">Desistimiento</SelectItem>
                        <SelectItem value="RECHAZADO">Rechazado</SelectItem>
                      </SelectContent>
                    </Select>
                    <p className="mt-2 text-xs text-indigo-800/80">
                      Al guardar se persistirá el estado en la base de datos. Revise
                      coherencia con cuotas y pagos.
                    </p>
                    {prestamo?.fecha_desistimiento ? (
                      <p className="mt-2 text-xs text-slate-700">
                        Fecha de desistimiento registrada:{' '}
                        {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : formData.estado === 'DESISTIMIENTO' ? (
                      <p className="mt-2 text-xs text-amber-800">
                        Al guardará se registrará la fecha de desistimiento en la base
                        de datos.
                      </p>
                    ) : null}
                  </div>
                ) : null}
                {/* Nuevos campos: Valor Activo y Anticipo */}"""

# Fix typo guardará -> guardar se registrará
insert = insert.replace("Al guardará se registrará", "Al guardar se registrará")

if marker not in text:
    raise SystemExit("marker not found")

if "border-indigo-200 bg-indigo-50/90" not in text:
    text = text.replace(marker, insert, 1)

old = """                {prestamo ? (
                  <div className="mt-4">
                    <label className="mb-1 block text-sm font-medium">
                      Estado del préstamo
                    </label>

                    <Select
                      value={String(
                        formData.estado ?? prestamo.estado ?? 'DRAFT'
                      )}
                      onValueChange={value =>
                        setFormData({
                          ...formData,

                          estado: value as Prestamo['estado'],
                        })
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Estado" />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectItem value="DRAFT">Borrador</SelectItem>

                        <SelectItem value="EN_REVISION">En revisión</SelectItem>

                        <SelectItem value="EVALUADO">Evaluado</SelectItem>

                        <SelectItem value="APROBADO">Aprobado</SelectItem>

                        <SelectItem value="LIQUIDADO">Liquidado</SelectItem>

                        <SelectItem value="DESISTIMIENTO">
                          Desistimiento
                        </SelectItem>

                        <SelectItem value="RECHAZADO">Rechazado</SelectItem>
                      </SelectContent>
                    </Select>

                    <p className="mt-1 text-xs text-gray-500">
                      Al guardar se persistirá el estado en la base de datos.
                      Revise coherencia con cuotas y pagos.
                    </p>
                    {prestamo?.fecha_desistimiento ? (
                      <p className="mt-2 text-xs text-slate-600">
                        Fecha de desistimiento registrada:{' '}
                        {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : formData.estado === 'DESISTIMIENTO' ? (
                      <p className="mt-2 text-xs text-amber-700">
                        Al guardar se registrará la fecha de desistimiento en la
                        base de datos.
                      </p>
                    ) : null}
                  </div>
                ) : null}"""

if old in text:
    text = text.replace(old, "", 1)

p.write_text(text, encoding="utf-8")
print("OK")
