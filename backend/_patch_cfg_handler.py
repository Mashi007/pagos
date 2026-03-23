from pathlib import Path

p = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/notificaciones/ConfiguracionNotificaciones.tsx"
)
t = p.read_text(encoding="utf-8")

old_import = """import {
  notificacionService,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""

new_import = """import {
  notificacionService,
  type EnvioPruebaPaqueteResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""

if old_import not in t:
    raise SystemExit("import block not found")
t = t.replace(old_import, new_import, 1)

old_block = """      const resultado = await notificacionService.enviarPruebaPaqueteCompleta({
        tipo: tipoPruebaPaquete,
        destinos,
      })

      const enviados = Number((resultado as Record<string, unknown>)?.enviados ?? 0)
      const fallidos = Number((resultado as Record<string, unknown>)?.fallidos ?? 0)

      if (enviados > 0 && fallidos === 0) {
        toast.success(
          String(
            (resultado as Record<string, unknown>)?.mensaje ||
              `Prueba enviada: plantilla + Carta PDF + PDFs fijos a ${destinos.length} correo(s).`
          )
        )
      } else if (enviados > 0) {
        toast.warning(
          `Enviado con advertencias (fallidos=${fallidos}). Revise SMTP y adjuntos en pestañas 2 y 3.`
        )
      } else {
        toast.error(
          String(
            (resultado as Record<string, unknown>)?.mensaje ||
              'No se pudo enviar la prueba. Revise que exista un cliente en el criterio y que los PDFs esten configurados.'
          )
        )
      }"""

new_block = """      const resultado: EnvioPruebaPaqueteResponse =
        await notificacionService.enviarPruebaPaqueteCompleta({
          tipo: tipoPruebaPaquete,
          destinos,
        })

      const enviados = resultado.enviados ?? 0
      const fallidos = resultado.fallidos ?? 0

      if (enviados > 0 && fallidos === 0) {
        toast.success(
          resultado.mensaje ||
            `Prueba enviada: plantilla + Carta PDF + PDFs fijos a ${destinos.length} correo(s).`
        )
      } else if (enviados > 0) {
        toast.warning(
          `Enviado con advertencias (fallidos=${fallidos}). Revise SMTP y adjuntos en pestañas 2 y 3.`
        )
      } else {
        toast.error(
          resultado.mensaje ||
            'No se pudo enviar la prueba. Revise que exista un cliente en el criterio y que los PDFs esten configurados.'
        )
      }"""

if old_block not in t:
    raise SystemExit("handler block not found")
t = t.replace(old_block, new_block, 1)
p.write_text(t, encoding="utf-8")
print("ok")
