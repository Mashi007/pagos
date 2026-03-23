# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "notificaciones" / "ConfiguracionNotificaciones.tsx"
t = p.read_text(encoding="utf-8")
if "handleDiagnosticoPaquete" in t:
    print("already patched cfg")
    raise SystemExit(0)

old_imp = """  type EnvioPruebaPaqueteResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""
new_imp = """  type EnvioPruebaPaqueteResponse,
  type DiagnosticoPaquetePruebaResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""
if old_imp not in t:
    raise SystemExit("import block missing")
t = t.replace(old_imp, new_imp, 1)

old_state = """  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>(
    CRITERIOS_ENVIO_PANEL[0].tipo
  )"""
new_state = """  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>(
    CRITERIOS_ENVIO_PANEL[0].tipo
  )

  const [diagnosticoPaquete, setDiagnosticoPaquete] =
    useState<DiagnosticoPaquetePruebaResponse | null>(null)"""
if old_state not in t:
    raise SystemExit("state block missing")
t = t.replace(old_state, new_state, 1)

handler = """
  const handleDiagnosticoPaquete = async () => {
    try {
      const d = await notificacionService.diagnosticoPaquetePrueba(tipoPruebaPaquete)
      setDiagnosticoPaquete(d)
      if (d.ok && d.paquete_completo) {
        toast.success(
          'Diagnostico: paquete listo (plantilla + Carta PDF + PDFs fijos). Puede enviar la prueba con confianza.',
          { duration: 8000 }
        )
      } else {
        toast.warning(
          `Diagnostico: no listo (${d.motivo || d.paquete_motivo || 'revisar'}). Revise PDFs en pestanas 2 y 3 y volumen en Render. Opcional: NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO=true solo para prueba forzada.`,
          { duration: 14000 }
        )
      }
    } catch (e: unknown) {
      const detalle = getErrorDetail(e)
      toast.error(detalle || 'Error al ejecutar diagnostico')
    }
  }

"""

# insert before handleEnviosMasivosPrueba
needle = "  const handleEnviosMasivosPrueba = async () => {"
if needle not in t:
    raise SystemExit("handleEnviosMasivosPrueba missing")
t = t.replace(needle, handler + needle, 1)

btn_block = """                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleDiagnosticoPaquete()}
                  className="flex h-auto w-full items-center justify-center gap-2 rounded-lg py-2"
                >
                  Diagnosticar paquete (sin enviar correo)
                </Button>

                """

needle2 = """                <Button
                  onClick={handleEnviarNotificacionesPrueba}"""
if needle2 not in t:
    raise SystemExit("green button missing")
t = t.replace(needle2, btn_block + needle2, 1)

p.write_text(t, encoding="utf-8")
print("ok cfg2")
