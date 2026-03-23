# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "components" / "notificaciones" / "ConfiguracionNotificaciones.tsx"
t = p.read_text(encoding="utf-8")
if "diagnosticoPaquetePrueba" in t:
    print("already")
    raise SystemExit(0)

old = """  type EnvioPruebaPaqueteResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""
new = """  type EnvioPruebaPaqueteResponse,
  type DiagnosticoPaquetePruebaResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'"""
if old not in t:
    raise SystemExit("import not found")
t = t.replace(old, new, 1)

# state for diagnostico
marker = "  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>("
if marker not in t:
    raise SystemExit("tipoPruebaPaquete not found")
t = t.replace(
    marker,
    "  const [diagnosticoPaquete, setDiagnosticoPaquete] =\n    useState<DiagnosticoPaquetePruebaResponse | null>(null)\n\n"
    + marker,
    1,
)

handler = """
  const handleDiagnosticoPaquete = async () => {
    try {
      setEnviandoPruebaIndice(null)
      const d = await notificacionService.diagnosticoPaquetePrueba(tipoPruebaPaquete)
      setDiagnosticoPaquete(d)
      if (d.ok && d.paquete_completo) {
        toast.success(
          'Diagnostico: paquete listo (plantilla + Carta PDF + PDFs fijos). Puede enviar la prueba con confianza.',
          { duration: 8000 }
        )
      } else {
        toast.warning(
          `Diagnostico: no listo (${d.motivo || d.paquete_motivo || 'revisar'}). Revise PDFs en pestanas 2 y 3 y volumen en Render.`,
          { duration: 12000 }
        )
      }
    } catch (e: unknown) {
      const detalle = getErrorDetail(e)
      toast.error(detalle || 'Error al ejecutar diagnostico')
    }
  }

"""

# insert before handleEnviosMasivosPrueba or find const handleEnviosMasivosPrueba
insert = "  const handleEnviosMasivosPrueba = async () => {"
if insert not in t:
    raise SystemExit("handleEnviosMasivosPrueba not found")
t = t.replace(insert, handler + insert, 1)

# add button in JSX - find Prueba envio completo or similar - search for enviarPruebaPaqueteCompleta usage
btn = """            <Button
              type=\"button\"
              variant=\"outline\"
              size=\"sm\"
              onClick={() => void handleDiagnosticoPaquete()}
            >
              Diagnosticar paquete (sin enviar)
            </Button>

"""

needle = "await notificacionService.enviarPruebaPaqueteCompleta"
if needle not in t:
    raise SystemExit("enviarPruebaPaqueteCompleta call not found")
# insert button before the button that calls handleEnvioPrueba - actually add after Select tipo prueba - complex

# Simpler: add button near texto "Prueba de paquete" - search for "tipoPruebaPaquete" and TabsContent
# Find `setTipoPruebaPaquete` and add after Select closing - grep line numbers

idx = t.find("onClick={handleEnviarPruebaPaqueteCompleta}")
if idx < 0:
    # try without braces
    idx = t.find("handleEnviarPruebaPaqueteCompleta")
if idx < 0:
    raise SystemExit("handleEnviarPruebaPaqueteCompleta not found")

# insert btn before the Button that contains handleEnviarPruebaPaqueteCompleta - find line start
start = t.rfind("<Button", 0, idx)
if start < 0:
    raise SystemExit("Button not found")
t = t[:start] + btn + t[start:]

p.write_text(t, encoding="utf-8")
print("ok cfg ui")
