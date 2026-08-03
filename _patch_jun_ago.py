from pathlib import Path

# 1) toast
p = Path("frontend/src/constants/reportes.ts")
t = p.read_text(encoding="utf-8")
old = "  cuotasHojaPeriodo: 'Hoja Drive actualizada (cuotas por periodo)',\n"
new = old + "  reporteCuotasJunAgo: 'REPORTE cuotas jun-ago: Drive actualizado (columnas D/E)',\n"
if "reporteCuotasJunAgo" not in t:
    if old not in t:
        raise SystemExit("toast anchor missing")
    p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("toast ok")
else:
    print("toast exists")

# 2) reporteService
p = Path("frontend/src/services/reporteService.ts")
t = p.read_text(encoding="utf-8")
if "actualizarReporteCuotasJunAgoDrive" not in t:
    needle = "  async getResumenDashboard(): Promise<ResumenDashboard> {"
    method = """  async actualizarReporteCuotasJunAgoDrive(opts?: {
    dry_run?: boolean
  }): Promise<{
    filas_leidas: number
    celdas_escritas: number
    dry_run: boolean
    fecha_desde: string
    fecha_hasta: string
    tab: string
    formula: string
  }> {
    const params = new URLSearchParams({
      dry_run: String(Boolean(opts?.dry_run)),
    })
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.post(
      `${this.baseUrl}/reporte-cuotas-jun-ago/actualizar-drive?${params.toString()}`,
      null,
      { timeout: 180000 }
    )
    return response.data
  }

"""
    if needle not in t:
        raise SystemExit("getResumenDashboard not found")
    p.write_text(t.replace(needle, method + needle, 1), encoding="utf-8", newline="\n")
    print("service ok")
else:
    print("service exists")

# 3) Reportes.tsx - tipo + lists + open + generate
p = Path("frontend/src/pages/Reportes.tsx")
t = p.read_text(encoding="utf-8")

if "REPORTE_CUOTAS_JUN_AGO" not in t:
    tipos_block = """  {
    value: 'PRESTAMOS_DRIVE',
    label: 'Préstamos Drive',
    icon: Car,
    subtitle: '11 columnas · filtro por lote (LOTE)',
    titleExtra:
      'Desde la hoja CONCILIACIÓN: cédula, total financiamiento, abonos, modalidad, fechas, producto, concesionario, analista, modelo y número de cuotas; solo filas cuya columna LOTE coincide con el o los números indicados (ej. 70).',
  },
]
"""
    tipos_new = """  {
    value: 'PRESTAMOS_DRIVE',
    label: 'Préstamos Drive',
    icon: Car,
    subtitle: '11 columnas · filtro por lote (LOTE)',
    titleExtra:
      'Desde la hoja CONCILIACIÓN: cédula, total financiamiento, abonos, modalidad, fechas, producto, concesionario, analista, modelo y número de cuotas; solo filas cuya columna LOTE coincide con el o los números indicados (ej. 70).',
  },

  {
    value: 'REPORTE_CUOTAS_JUN_AGO',
    label: 'REPORTE cuotas jun-ago',
    icon: FileSpreadsheet,
    subtitle: 'Estatico · actualiza Drive D/E',
    titleExtra:
      'Periodo fijo 1 jun 2026 - 2 ago 2026. Solo cedulas de la hoja. D = pagadas - impagas; E = monto neto. No descarga archivo.',
  },
]
"""
    if tipos_block not in t:
        raise SystemExit("tiposReporte PRESTAMOS block missing")
    t = t.replace(tipos_block, tipos_new, 1)

    drive_list_old = """const REPORTES_DESDE_DRIVE_SHEET = [
  'FECHA_DRIVE',
  'ANALISIS_FINANCIAMIENTO',
  'CLIENTES_HOJA',
  'PRESTAMOS_DRIVE',
] as const
"""
    drive_list_new = """const REPORTES_DESDE_DRIVE_SHEET = [
  'FECHA_DRIVE',
  'ANALISIS_FINANCIAMIENTO',
  'CLIENTES_HOJA',
  'PRESTAMOS_DRIVE',
  'REPORTE_CUOTAS_JUN_AGO',
] as const
"""
    if drive_list_old not in t:
        raise SystemExit("REPORTES_DESDE_DRIVE_SHEET missing")
    t = t.replace(drive_list_old, drive_list_new, 1)

    open_old = """    if (
      tipo === 'CEDULA' ||
      tipo === 'FECHA_DRIVE' ||
      tipo === 'ANALISIS_FINANCIAMIENTO'
    ) {
      generarReporte(tipo, {
        ['a\\u00f1os']: [],
        meses: [],
      } as unknown as FiltrosReporte)

      return
    }
"""
    # actual file may have unicode año or escape - read exact
    print("open dialog snippet search...")

p.write_text(t, encoding="utf-8", newline="\n")
print("partial page write - check")
