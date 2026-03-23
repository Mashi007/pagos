# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent / "src" / "services" / "notificacionService.ts"
t = p.read_text(encoding="utf-8")
if "diagnosticoPaquetePrueba" in t:
    print("ts already")
    raise SystemExit(0)

iface = """
export interface DiagnosticoPaquetePruebaResponse {
  ok?: boolean
  motivo?: string
  tipo_solicitado?: string
  tipo_config?: string
  habilitado_envio?: boolean
  plantilla_id?: number | null
  plantilla_ok?: boolean
  plantilla_motivo?: string | null
  paquete_estricto?: boolean
  relax_solo_prueba_destino?: boolean
  paquete_completo?: boolean
  paquete_motivo?: string | null
  adjuntos_previstos?: Array<{
    nombre: string
    bytes: number
    cabecera_pdf: boolean
  }>
  error_adjuntos?: string
}
"""

# insert after EnvioPruebaPaqueteResponse block - find closing }; of EnvioPruebaPaqueteResponse
marker = "export interface EnvioPruebaPaqueteResponse {"
idx = t.find(marker)
if idx < 0:
    raise SystemExit("EnvioPruebaPaqueteResponse not found")
# find end of that interface - next "}\n\n/**" or "}\n\nconst"
end = t.find("\n}\n", t.find("destinos?: string[]", idx))
if end < 0:
    raise SystemExit("end iface not found")
end = end + len("\n}\n")
t = t[:end] + iface + t[end:]

method = """
  async diagnosticoPaquetePrueba(tipo: string): Promise<DiagnosticoPaquetePruebaResponse> {
    const params = new URLSearchParams({ tipo })
    return await apiClient.get<DiagnosticoPaquetePruebaResponse>(
      `${this.baseUrl}/diagnostico-paquete-prueba?${params}`
    )
  }

"""
insert_at = t.find("  async enviarPruebaPaqueteCompleta")
if insert_at < 0:
    raise SystemExit("enviarPruebaPaqueteCompleta not found")
t = t[:insert_at] + method + t[insert_at:]
p.write_text(t, encoding="utf-8")
print("ok ts")
