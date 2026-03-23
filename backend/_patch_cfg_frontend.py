from pathlib import Path

p = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/notificaciones/ConfiguracionNotificaciones.tsx"
)
lines = p.read_text(encoding="utf-8").splitlines()

# insert state after enviandoMasivo line
idx = None
for i, line in enumerate(lines):
    if line.strip() == "const [enviandoMasivo, setEnviandoMasivo] = useState(false)":
        idx = i
        break
if idx is None:
    raise SystemExit("enviandoMasivo line not found")

insert = [
    "",
    "  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>(",
    "    CRITERIOS_ENVIO_PANEL[0].tipo",
    "  )",
    "",
]
lines = lines[: idx + 1] + insert + lines[idx + 1 :]

start = None
end = None
for i, line in enumerate(lines):
    if line.strip().startswith("const ASUNTO_PLANTILLA_PREDETERMINADA"):
        start = i
    if line.strip().startswith("const handleEnviosMasivosPrueba"):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"markers start={start} end={end}")

new_handler = """  const handleEnviarNotificacionesPrueba = async () => {
    const destinos = [
      emailsPruebas[0]?.trim(),
      emailsPruebas[1]?.trim(),
    ].filter(Boolean) as string[]

    if (!modoPruebas || destinos.length === 0) {
      toast.error('Configura al menos un correo de pruebas para enviar.')

      return
    }

    const invalidos = destinos.filter(e => !esEmailValido(e))

    if (invalidos.length > 0) {
      toast.error(
        `Correo(s) no valido(s): ${invalidos.join(', ')}. Usa formato usuario@dominio.com`
      )

      return
    }

    try {
      setEnviandoPruebaIndice(0)

      const estadoEmail =
        await emailConfigService.verificarEstadoConfiguracionEmail()

      if (!estadoEmail?.configurada) {
        const problemas =
          estadoEmail?.problemas?.join('. ') ||
          'servidor SMTP, usuario y contrasena'

        toast.error(
          `Configura el email SMTP antes de enviar pruebas: ${problemas} Ve a Configuracion > Email.`,

          { duration: 6000 }
        )

        setEnviandoPruebaIndice(null)

        return
      }

      const resultado = await notificacionService.enviarPruebaPaqueteCompleta({
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
      }
    } catch (error: unknown) {
      const detalle = getErrorDetail(error)

      const mensaje =
        detalle ||
        (error as Error)?.message ||
        'Error al enviar el correo de prueba'

      toast.error(mensaje, { duration: 5000 })
    } finally {
      setEnviandoPruebaIndice(null)
    }
  }
"""

out_lines = lines[:start] + [new_handler.rstrip("\n")] + lines[end:]
p.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
print("ok", start, end, "lines", len(out_lines))
