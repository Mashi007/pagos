# -*- coding: utf-8 -*-
from pathlib import Path

root = Path(__file__).resolve().parent

ns = root / "src" / "services" / "notificacionService.ts"
t = ns.read_text(encoding="utf-8")
old = """    return await apiClient.get<DiagnosticoPaquetePruebaResponse>(
      `${this.baseUrl}/diagnostico-paquete-prueba?${params}`
    )
  }

  async enviarPruebaPaqueteCompleta"""
new = """    return await apiClient.get<DiagnosticoPaquetePruebaResponse>(
      `${this.baseUrl}/diagnostico-paquete-prueba?${params}`,
      { timeout: 180000 }
    )
  }

  async enviarPruebaPaqueteCompleta"""
if old not in t:
    raise SystemExit("notificacionService block not found")
ns.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok ns")

api = root / "src" / "services" / "api.ts"
t2 = api.read_text(encoding="utf-8")
needle = """    const tablasCamposTimeout = 90000 // 90 segundos para consulta de estructura completa de BD

    let defaultTimeout = DEFAULT_TIMEOUT_MS

    if (isRevisionManual) {
      defaultTimeout = revisionManualTimeout
    } else if (isReportesDashboard) {
      defaultTimeout = reportesDashboardTimeout
    } else if (isClientesAtrasados) {
      defaultTimeout = verySlowTimeout
    } else if (isTablasCampos) {
      defaultTimeout = tablasCamposTimeout"""
insert = """    const tablasCamposTimeout = 90000 // 90 segundos para consulta de estructura completa de BD

    const isDiagnosticoPaquetePrueba = url.includes('diagnostico-paquete-prueba')

    const diagnosticoPaqueteTimeout = 180000

    let defaultTimeout = DEFAULT_TIMEOUT_MS

    if (isRevisionManual) {
      defaultTimeout = revisionManualTimeout
    } else if (isReportesDashboard) {
      defaultTimeout = reportesDashboardTimeout
    } else if (isClientesAtrasados) {
      defaultTimeout = verySlowTimeout
    } else if (isDiagnosticoPaquetePrueba) {
      defaultTimeout = diagnosticoPaqueteTimeout
    } else if (isTablasCampos) {
      defaultTimeout = tablasCamposTimeout"""
if needle not in t2:
    raise SystemExit("api.ts block not found")
t2 = t2.replace(needle, insert, 1)
api.write_text(t2, encoding="utf-8")
print("ok api")
