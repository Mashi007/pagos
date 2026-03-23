from pathlib import Path

p = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/services/notificacionService.ts"
)
t = p.read_text(encoding="utf-8")

ins = """/** Respuesta de POST /notificaciones/enviar-prueba-paquete (mismo shape que resumen de envio + meta). */
export interface EnvioPruebaPaqueteResponse {
  mensaje?: string
  enviados?: number
  fallidos?: number
  sin_email?: number
  omitidos_config?: number
  omitidos_paquete_incompleto?: number
  enviados_whatsapp?: number
  fallidos_whatsapp?: number
  tipo?: string
  destinos?: string[]
}

"""

marker = "}\n\n/** Prefijo API v1"
if marker not in t:
    raise SystemExit("marker1 not found")
t = t.replace(marker, "}\n\n" + ins + "/** Prefijo API v1", 1)

old = """  async enviarPruebaPaqueteCompleta(params: {
    tipo: string
    destinos: string[]
  }): Promise<Record<string, unknown>> {
    return await apiClient.post<Record<string, unknown>>(
      `${this.baseUrl}/enviar-prueba-paquete`,
      params,
      { timeout: 120000 }
    )
  }"""

new = """  async enviarPruebaPaqueteCompleta(params: {
    tipo: string
    destinos: string[]
  }): Promise<EnvioPruebaPaqueteResponse> {
    return await apiClient.post<EnvioPruebaPaqueteResponse>(
      `${this.baseUrl}/enviar-prueba-paquete`,
      params,
      { timeout: 120000 }
    )
  }"""

if old not in t:
    raise SystemExit("method block not found")
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("ok")
