from pathlib import Path

# 1) envioBatchActivo
path = Path("frontend/src/utils/envioBatchActivo.ts")
text = path.read_text(encoding="utf-8")
old = "  if (estado === 'finalizado' || estado === 'pausado_limite_gmail') return false\n"
new = "  if (\n    estado === 'finalizado' ||\n    estado === 'pausado_limite_gmail' ||\n    estado === 'cancelado_usuario'\n  )\n    return false\n"
if "cancelado_usuario" in text:
    print("activo already")
elif old not in text:
    raise SystemExit("activo missing")
else:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("activo ok")
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "if (det && det.pausado_limite_gmail && estado !== 'en_proceso') return false",
        "if (\n    det &&\n    (det.pausado_limite_gmail || det.cancelado_usuario) &&\n    estado !== 'en_proceso'\n  )\n    return false",
        1,
    )
    path.write_text(text, encoding="utf-8")

# 2) notificacionService cancelarEnvioBatch
path = Path("frontend/src/services/notificacionService.ts")
text = path.read_text(encoding="utf-8")
if "cancelarEnvioBatch" in text:
    print("service already")
else:
    needle = "  async obtenerUltimoEnvioBatch(opts?: { signal?: AbortSignal }): Promise<{\n    ultimo: Record<string, unknown> | null\n  }> {\n    return await apiClient.get<{ ultimo: Record<string, unknown> | null }>(\n      `${this.baseUrl}/envio-batch/ultimo`,\n      { signal: opts?.signal, timeout: 60000 }\n    )\n  }\n"
    # may have lotes_continuar in type now - check actual
    idx = text.find("async obtenerUltimoEnvioBatch")
    if idx < 0:
        raise SystemExit("obtener missing")
    # insert after the method
    end = text.find("\n  // Variables de notificaciones", idx)
    if end < 0:
        end = text.find("\n  async listarVariables", idx)
    insert = '''
  /** Cancela el lote en el servidor (corta entre correos) y cierra el resumen activo. */
  async cancelarEnvioBatch(opts?: { signal?: AbortSignal }): Promise<{
    ok: boolean
    mensaje?: string
    tipo_caso?: string | null
  }> {
    return await apiClient.post<{
      ok: boolean
      mensaje?: string
      tipo_caso?: string | null
    }>(`${this.baseUrl}/envio-batch/cancelar`, {}, {
      signal: opts?.signal,
      timeout: 60000,
    })
  }

'''
    text = text[:end] + insert + text[end:]
    # also handle cancelado in poll like pausado
    path.write_text(text, encoding="utf-8")
    print("service ok")

# Handle cancelado in enviarCasoManual poll (like pausadoGmail)
text = path.read_text(encoding="utf-8")
if "cancelado_usuario" in text and "pausadoGmail" in text:
    # extend pausadoGmail check
    old_p = """        const pausadoGmail =
          estadoUlt === 'pausado_limite_gmail' ||
          Boolean(
            detRec &&
              'pausado_limite_gmail' in detRec &&
              (detRec as Record<string, unknown>).pausado_limite_gmail
          )
"""
    new_p = """        const pausadoGmail =
          estadoUlt === 'pausado_limite_gmail' ||
          Boolean(
            detRec &&
              'pausado_limite_gmail' in detRec &&
              (detRec as Record<string, unknown>).pausado_limite_gmail
          )
        const canceladoUi =
          estadoUlt === 'cancelado_usuario' ||
          Boolean(
            detRec &&
              'cancelado_usuario' in detRec &&
              (detRec as Record<string, unknown>).cancelado_usuario
          )
"""
    if "canceladoUi" in text:
        print("poll cancel already")
    elif old_p not in text:
        print("poll pausado block MISSING - skip")
    else:
        text = text.replace(old_p, new_p, 1)
        text = text.replace(
            "if (pausadoGmail) {",
            "if (canceladoUi) {\n          opts?.onProgress?.({\n            procesados: Number.isFinite(procesadosN) ? procesadosN : 0,\n            total: Number.isFinite(totalN) ? totalN : 0,\n            enviados: Number(ultimo.enviados ?? 0),\n            fallidos: Number(ultimo.fallidos ?? 0),\n            sin_email: Number(ultimo.sin_email ?? 0),\n            estado: 'cancelado_usuario',\n          })\n          return {\n            mensaje:\n              'Envío cancelado. El pendiente queda para continuar luego; los ya enviados se omiten.',\n            tipo_caso: tipo,\n            total_en_lista: Number(ultimo.total_en_lista ?? 0),\n            enviados: Number(ultimo.enviados ?? 0),\n            sin_email: Number(ultimo.sin_email ?? 0),\n            fallidos: Number(ultimo.fallidos ?? 0),\n            procesados: Number.isFinite(procesadosN) ? procesadosN : 0,\n            estado: 'cancelado_usuario',\n            cancelado_usuario: true,\n          }\n        }\n        if (pausadoGmail) {",
            1,
        )
        path.write_text(text, encoding="utf-8")
        print("poll cancel ok")
