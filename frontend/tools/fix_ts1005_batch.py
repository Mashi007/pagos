from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"

# (path relative to src, old, new) — exact substring replacements
REPLACEMENTS: list[tuple[str, str, str]] = [
    # ExcelUploaderPagosUI.tsx
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.cedula ? ',
        "{OBSERVACIONES_POR_CAMPO.cedula ?? ",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.fecha_pago ? ',
        "{OBSERVACIONES_POR_CAMPO.fecha_pago ?? ",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.monto_pagado ? ',
        "{OBSERVACIONES_POR_CAMPO.monto_pagado ?? ",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.numero_documento ? ',
        "{OBSERVACIONES_POR_CAMPO.numero_documento ?? ",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        "row.prestamo_id ? 'n'",
        "row.prestamo_id ?? 'n'",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.prestamo_id ? ',
        "{OBSERVACIONES_POR_CAMPO.prestamo_id ?? ",
    ),
    (
        "components/pagos/ExcelUploaderPagosUI.tsx",
        '{OBSERVACIONES_POR_CAMPO.conciliado ? ',
        "{OBSERVACIONES_POR_CAMPO.conciliado ?? ",
    ),
    # PagosBuscadorAmortizacion.tsx
    (
        "components/pagos/PagosBuscadorAmortizacion.tsx",
        "const prestamoIds = prestamos?.map((p) => p.id) ? []",
        "const prestamoIds = prestamos?.map((p) => p.id) ?? []",
    ),
    (
        "components/pagos/PagosBuscadorAmortizacion.tsx",
        "const listaCuotas = cuotas ? []",
        "const listaCuotas = cuotas ?? []",
    ),
    (
        "components/pagos/PagosBuscadorAmortizacion.tsx",
        "(prestamos?.length?? 0)",
        "(prestamos?.length ?? 0)",
    ),
    (
        "components/pagos/PagosBuscadorAmortizacion.tsx",
        ": (c as any).monto?.toFixed(2) ? '-'",
        ": ((c as any).monto != null ? (c as any).monto.toFixed(2) : '-')",
    ),
    # PagosKPIsNuevo.tsx
    (
        "components/pagos/PagosKPIsNuevo.tsx",
        "          {nombreMes} {kpiDataFinal.anio ? (kpiDataFinal as any)?.[\"a\u00f1o\"] ? new Date().getFullYear()}",
        "          {nombreMes} {kpiDataFinal.anio ?? (kpiDataFinal as any)?.['a\u00f1o'] ?? new Date().getFullYear()}",
    ),
    # PagosListResumen.tsx
    (
        "components/pagos/PagosListResumen.tsx",
        "<TableCell>{pago.numero_documento ? '-'}</TableCell>",
        "<TableCell>{pago.numero_documento ?? '-'}</TableCell>",
    ),
    # TablaEditablePagos.tsx
    (
        "components/pagos/TablaEditablePagos.tsx",
        "  const isSaving = (rowIndex: number) => savingProgress[rowIndex] ? localSaving.has(rowIndex)",
        "  const isSaving = (rowIndex: number) =>\n    !!savingProgress[rowIndex] || localSaving.has(rowIndex)",
    ),
    # AprobarPrestamoManualModal.tsx
    (
        "components/prestamos/AprobarPrestamoManualModal.tsx",
        "    const tasaAnual = tasaInteres ? 0",
        "    const tasaAnual = tasaInteres ?? 0",
    ),
    # CrearPrestamoForm.tsx
    (
        "components/prestamos/CrearPrestamoForm.tsx",
        "        modelo: formData.modelo_vehiculo ? undefined,",
        "        modelo: formData.modelo_vehiculo || undefined,",
    ),
    # EvaluacionRiesgoCriteriosSection.tsx — match mojibake-safe: use regex? read file
    (
        "components/prestamos/evaluacion/EvaluacionRiesgoCriteriosSection.tsx",
        "?.toString() ? '0'",
        "?.toString() ?? '0'",
    ),
    (
        "components/prestamos/evaluacion/EvaluacionRiesgoMLSection.tsx",
        "{puntuacion_total?.toFixed(1) ? 'N/A'}",
        "{puntuacion_total?.toFixed(1) ?? 'N/A'}",
    ),
    (
        "components/prestamos/PrestamoDetalleModal.tsx",
        "<p className=\"font-medium\">{prestamoData.cedula ? '-'}</p>",
        "<p className=\"font-medium\">{prestamoData.cedula ?? '-'}</p>",
    ),
    (
        "components/prestamos/PrestamoDetalleModal.tsx",
        "<p className=\"font-medium\">{prestamoData.nombres ? '-'}</p>",
        "<p className=\"font-medium\">{prestamoData.nombres ?? '-'}</p>",
    ),
    (
        "components/prestamos/PrestamosKPIs.tsx",
        "  const nombreMes = MESES[(kpiDataFinal.mes ? mesSel) - 1]",
        "  const nombreMes = MESES[(kpiDataFinal.mes ?? mesSel) - 1]",
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        '<TableCell className="font-mono text-xs">{item.fila_origen ? \'-\'}</TableCell>',
        '<TableCell className="font-mono text-xs">{item.fila_origen ?? \'-\'}</TableCell>',
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        'title={item.errores ?? \'\'}>{item.errores ? \'-\'}</TableCell>',
        "title={item.errores ?? ''}>{item.errores ?? '-'}</TableCell>",
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        "<TableCell>{item.estado ? '-'}</TableCell>",
        "<TableCell>{item.estado ?? '-'}</TableCell>",
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        '<div className="font-medium">{prestamo.nombres ? prestamo.nombre_cliente ? `Cliente #${prestamo.cliente_id ? \'-\'}`}</div>',
        '<div className="font-medium">{prestamo.nombres ?? prestamo.nombre_cliente ?? `Cliente #${prestamo.cliente_id ?? \'-\'}`}</div>',
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        "<TableCell>{prestamo.cedula ? prestamo.cedula_cliente ? '-'}</TableCell>",
        "<TableCell>{prestamo.cedula ?? prestamo.cedula_cliente ?? '-'}</TableCell>",
    ),
    (
        "components/prestamos/PrestamosList.tsx",
        "                           prestamo.modalidad_pago ? '-'}",
        "                           '-'}",
    ),
    (
        "components/prestamos/TablaAmortizacionPrestamo.tsx",
        "    const montoConciliado = cuota.pago_monto_conciliado ? 0",
        "    const montoConciliado = cuota.pago_monto_conciliado ?? 0",
    ),
    (
        "components/prestamos/TablaAmortizacionPrestamo.tsx",
        "                    const montoConciliado = c.pago_monto_conciliado ? 0",
        "                    const montoConciliado = c.pago_monto_conciliado ?? 0",
    ),
    (
        "components/reportes/DialogConciliacion.tsx",
        "              const ta = row[2] ? 0",
        "              const ta = row[2] ?? 0",
    ),
    (
        "components/reportes/ReportePagos.tsx",
        "                  <TableRow key={item.pago_id ? `${item.fecha}-${item.cedula}-${item.documento}`}>",
        "                  <TableRow key={String(item.pago_id ?? `${item.fecha}-${item.cedula}-${item.documento}`)}>",
    ),
    (
        "components/reportes/ReportePagos.tsx",
        "                    <TableCell>{item.prestamo_id ? '-'}</TableCell>",
        "                    <TableCell>{item.prestamo_id ?? '-'}</TableCell>",
    ),
    (
        "hooks/useAuditoriaPrestamo.ts",
        "    observaciones: item.descripcion ? null,",
        "    observaciones: item.descripcion ?? null,",
    ),
    (
        "hooks/useEvaluacionRiesgo.ts",
        "      setResumenPrestamos(resumenRes ? { error: true, tiene_prestamos: false, prestamos: [] })",
        "      setResumenPrestamos(resumenRes ?? { error: true, tiene_prestamos: false, prestamos: [] })",
    ),
    (
        "hooks/useExcelUploadPrestamos.ts",
        "          numero_cuotas: row.numero_cuotas ? null,",
        "          numero_cuotas: row.numero_cuotas ?? null,",
    ),
    (
        "hooks/useGmailPipeline.ts",
        "            const emails = s.last_emails ? 0",
        "            const emails = s.last_emails ?? 0",
    ),
    (
        "hooks/useGmailPipeline.ts",
        "            const files = s.last_files ? 0",
        "            const files = s.last_files ?? 0",
    ),
    (
        "hooks/useGmailPipeline.ts",
        "            const processed = s.last_emails ? 0",
        "            const processed = s.last_emails ?? 0",
    ),
    (
        "pages/Campanas.tsx",
        "                          <li key={d.cliente_id ? i} className=\"flex items-center gap-2\">",
        '                          <li key={d.cliente_id ?? i} className="flex items-center gap-2">',
    ),
]


def main() -> None:
    failed: list[tuple[str, str]] = []
    for rel, old, new in REPLACEMENTS:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        if old not in text:
            failed.append((rel, old[:80]))
            continue
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        print("ok", rel)
    if failed:
        print("\nFAILED (substring not found):")
        for rel, frag in failed:
            print(rel, "...", frag)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
