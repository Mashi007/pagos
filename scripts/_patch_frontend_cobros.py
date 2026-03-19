# -*- coding: utf-8 -*-
"""Patch pagoService + PagosList for importar-desde-cobros response fields."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch_pago_service() -> None:
    p = ROOT / "frontend" / "src" / "services" / "pagoService.ts"
    t = p.read_text(encoding="utf-8")
    old = """  async importarDesdeCobros(): Promise<{
    registros_procesados: number
    registros_con_error: number
    errores_detalle: Array<{ referencia: string; error: string }>
    ids_pagos_con_errores: number[]
    cuotas_aplicadas?: number
    mensaje: string
  }> {
    return await apiClient.post(`${this.baseUrl}/importar-desde-cobros`)
  }"""
    new = """  async importarDesdeCobros(): Promise<{
    registros_procesados: number
    registros_con_error: number
    errores_detalle: Array<{ referencia: string; error: string }>
    ids_pagos_con_errores: number[]
    /** Suma de operaciones en cuotas (completadas + parciales), no cantidad de filas del cronograma. */
    cuotas_aplicadas?: number
    operaciones_cuota_total?: number
    pagos_con_aplicacion_a_cuotas?: number
    pagos_sin_aplicacion_cuotas?: Array<{
      pago_id: number | null
      cedula_cliente: string
      prestamo_id: number | null
      motivo: string
      detalle: string
    }>
    pagos_sin_aplicacion_cuotas_total?: number
    pagos_sin_aplicacion_cuotas_truncados?: boolean
    total_datos_revisar?: number
    mensaje: string
  }> {
    return await apiClient.post(`${this.baseUrl}/importar-desde-cobros`)
  }"""
    if old not in t:
        raise SystemExit("pagoService: block not found")
    p.write_text(t.replace(old, new, 1), encoding="utf-8")


def patch_pagos_list() -> None:
    p = ROOT / "frontend" / "src" / "components" / "pagos" / "PagosList.tsx"
    t = p.read_text(encoding="utf-8")

    old_state = """  const [lastImportCobrosResult, setLastImportCobrosResult] = useState<{
    registros_procesados: number
    registros_con_error: number
    cuotas_aplicadas?: number
    mensaje: string
  } | null>(null)"""
    new_state = """  const [lastImportCobrosResult, setLastImportCobrosResult] = useState<{
    registros_procesados: number
    registros_con_error: number
    cuotas_aplicadas?: number
    operaciones_cuota_total?: number
    pagos_con_aplicacion_a_cuotas?: number
    pagos_sin_aplicacion_cuotas_total?: number
    pagos_sin_aplicacion_cuotas_truncados?: boolean
    pagos_sin_aplicacion_cuotas?: Array<{
      pago_id: number | null
      cedula_cliente: string
      prestamo_id: number | null
      motivo: string
      detalle: string
    }>
    mensaje: string
  } | null>(null)"""
    if old_state not in t:
        raise SystemExit("PagosList: state block not found")
    t = t.replace(old_state, new_state, 1)

    old_handler = """      setLastImportCobrosResult({
        registros_procesados: res.registros_procesados,
        registros_con_error: res.registros_con_error,
        cuotas_aplicadas: res.cuotas_aplicadas,
        mensaje: res.mensaje,
      })
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      const mensajeConCuotas =
        typeof res.cuotas_aplicadas === 'number' && res.cuotas_aplicadas > 0
          ? `${res.mensaje} ${res.cuotas_aplicadas} cuotas aplicadas a créditos.`
          : res.mensaje
      toast.success(mensajeConCuotas)
      if (res.registros_con_error > 0) {
        toast('Hay registros con error. Use el botón "Descargar Excel (errores de esta importación)" para revisarlos.', { duration: 5000 })
      }"""
    new_handler = """      setLastImportCobrosResult({
        registros_procesados: res.registros_procesados,
        registros_con_error: res.registros_con_error,
        cuotas_aplicadas: res.cuotas_aplicadas,
        operaciones_cuota_total: res.operaciones_cuota_total,
        pagos_con_aplicacion_a_cuotas: res.pagos_con_aplicacion_a_cuotas,
        pagos_sin_aplicacion_cuotas_total: res.pagos_sin_aplicacion_cuotas_total,
        pagos_sin_aplicacion_cuotas_truncados: res.pagos_sin_aplicacion_cuotas_truncados,
        pagos_sin_aplicacion_cuotas: res.pagos_sin_aplicacion_cuotas,
        mensaje: res.mensaje,
      })
      await queryClient.invalidateQueries({ queryKey: ['pagos'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-kpis'], exact: false })
      await queryClient.invalidateQueries({ queryKey: ['pagos-con-errores'], exact: false })
      const ops =
        typeof res.operaciones_cuota_total === 'number'
          ? res.operaciones_cuota_total
          : res.cuotas_aplicadas
      const pagosArticulados = res.pagos_con_aplicacion_a_cuotas
      const extraOps =
        typeof ops === 'number' && ops > 0 && typeof pagosArticulados === 'number'
          ? ` ${ops} operaciones en cuotas (${pagosArticulados} pago(s) con monto aplicado a cronograma).`
          : ''
      toast.success(`${res.mensaje}${extraOps}`)
      const sinAplicar = res.pagos_sin_aplicacion_cuotas_total ?? 0
      if (sinAplicar > 0) {
        toast(
          `${sinAplicar} pago(s) quedaron en tabla Pagos sin aplicar a cuotas (revisar préstamo o usar «Aplicar a cuotas»).`,
          { duration: 8000 },
        )
      }
      if (res.registros_con_error > 0) {
        toast('Hay registros con error. Use el botón "Descargar Excel (errores de esta importación)" para revisarlos.', { duration: 5000 })
      }"""
    if old_handler not in t:
        raise SystemExit("PagosList: handler block not found")
    t = t.replace(old_handler, new_handler, 1)

    old_banner = """      {lastImportCobrosResult && lastImportCobrosResult.registros_con_error > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="py-3 flex flex-wrap items-center gap-3">
            <span className="text-sm text-amber-800">
              {lastImportCobrosResult.registros_procesados} importados
              {typeof lastImportCobrosResult.cuotas_aplicadas === 'number' && lastImportCobrosResult.cuotas_aplicadas > 0 && (
                <> ({lastImportCobrosResult.cuotas_aplicadas} cuotas aplicadas)</>
              )}
              ; {lastImportCobrosResult.registros_con_error} con error (no cumplen reglas de carga masiva). Descargue el Excel para revisar y corregir.
            </span>"""
    new_banner = """      {lastImportCobrosResult && lastImportCobrosResult.registros_con_error > 0 && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="py-3 flex flex-wrap items-center gap-3">
            <span className="text-sm text-amber-800">
              {lastImportCobrosResult.registros_procesados} importados
              {typeof lastImportCobrosResult.cuotas_aplicadas === 'number' && lastImportCobrosResult.cuotas_aplicadas > 0 && (
                <>
                  {' '}
                  ({lastImportCobrosResult.cuotas_aplicadas} operaciones en cuotas
                  {typeof lastImportCobrosResult.pagos_con_aplicacion_a_cuotas === 'number'
                    ? `, ${lastImportCobrosResult.pagos_con_aplicacion_a_cuotas} pago(s) con aplicación`
                    : ''}
                  )
                </>
              )}
              ; {lastImportCobrosResult.registros_con_error} con error (no cumplen reglas de carga masiva). Descargue el Excel para revisar y corregir.
            </span>"""
    if old_banner not in t:
        raise SystemExit("PagosList: amber banner not found")
    t = t.replace(old_banner, new_banner, 1)

    insert_after = """            <Button variant="ghost" size="sm" onClick={() => setLastImportCobrosResult(null)}>Ocultar</Button>
          </CardContent>
        </Card>
      )}
      {/* Pestañas: por defecto Resumen por Cliente"""
    if insert_after not in t:
        # try without special char in comment
        insert_after = """            <Button variant="ghost" size="sm" onClick={() => setLastImportCobrosResult(null)}>Ocultar</Button>
          </CardContent>
        </Card>
      )}
      {/* Pesta"""
    idx = t.find(insert_after)
    if idx == -1:
        raise SystemExit("PagosList: insert anchor not found")
    # Only insert if not already present
    if "border-orange-200 bg-orange-50" not in t:
        block = """
      {lastImportCobrosResult &&
        (lastImportCobrosResult.pagos_sin_aplicacion_cuotas_total ?? 0) > 0 && (
          <Card className="border-orange-200 bg-orange-50">
            <CardContent className="py-3 flex flex-col gap-2">
              <span className="text-sm text-orange-900 font-medium">
                {lastImportCobrosResult.pagos_sin_aplicacion_cuotas_total} pago(s) importado(s) sin aplicar a cuotas
                {lastImportCobrosResult.pagos_sin_aplicacion_cuotas_truncados ? ' (lista truncada)' : ''}
              </span>
              <p className="text-xs text-orange-800">
                Revise cuotas del préstamo o use «Aplicar a cuotas» en la fila del pago. Detalle:
              </p>
              <ul className="text-xs text-orange-900 list-disc pl-5 max-h-32 overflow-y-auto">
                {(lastImportCobrosResult.pagos_sin_aplicacion_cuotas ?? []).map((row, i) => (
                  <li key={`${row.pago_id ?? i}-${row.cedula_cliente}`}>
                    {row.pago_id != null ? `#${row.pago_id}` : '—'} · {row.cedula_cliente || '—'} · préstamo{' '}
                    {row.prestamo_id ?? '—'} · {row.motivo}: {row.detalle}
                  </li>
                ))}
              </ul>
              <Button variant="ghost" size="sm" className="self-start" onClick={() => setLastImportCobrosResult(null)}>
                Ocultar
              </Button>
            </CardContent>
          </Card>
        )}
"""
        t = t[: idx + len("        </Card>\n      )}\n")] + block + t[idx + len("        </Card>\n      )}\n") :]

    p.write_text(t, encoding="utf-8")


def main() -> None:
    patch_pago_service()
    patch_pagos_list()
    print("frontend patched")


if __name__ == "__main__":
    main()
