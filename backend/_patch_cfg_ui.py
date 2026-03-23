from pathlib import Path

p = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/notificaciones/ConfiguracionNotificaciones.tsx"
)
t = p.read_text(encoding="utf-8")

old = """                <p className="text-sm text-gray-600">
                  Envía un correo de ejemplo con la{' '}
                  <strong>plantilla predeterminada</strong> a los correos de
                  pruebas 1 y 2.
                </p>

                <Button"""

new = """                <p className="text-sm text-gray-600">
                  Prueba con el mismo contenido que producción: cuerpo desde la
                  plantilla vinculada en la tabla (pestaña 1),{' '}
                  <strong>Carta_Cobranza.pdf</strong> (pestaña 2) y PDF(s) fijos
                  (pestaña 3). Elija el criterio de caso:
                </p>

                <div className="flex max-w-md flex-col gap-1">
                  <label className="text-xs font-medium text-gray-600">
                    Criterio (tipo de envío)
                  </label>
                  <Select
                    value={tipoPruebaPaquete}
                    onValueChange={v => setTipoPruebaPaquete(v)}
                  >
                    <SelectTrigger className="border-gray-200 bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CRITERIOS_ENVIO_PANEL.map(({ tipo, label }) => (
                        <SelectItem key={tipo} value={tipo}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button"""

if old not in t:
    raise SystemExit("old UI block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
