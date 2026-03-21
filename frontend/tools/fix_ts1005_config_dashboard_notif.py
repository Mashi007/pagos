from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"


def replace_one(path: pathlib.Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def main() -> None:
    fixes: list[tuple[str, str, str]] = [
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            "    const totalDisponible = metricas.conversaciones.listas_entrenamiento ? 0",
            "    const totalDisponible = metricas.conversaciones.listas_entrenamiento ?? 0",
        ),
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            "        descripcion: `Tienes ${conv.listas_entrenamiento ? 0} conversaciones listas. Puedes iniciar el fine-tuning ahora.`",
            "        descripcion: `Tienes ${conv.listas_entrenamiento ?? 0} conversaciones listas. Puedes iniciar el fine-tuning ahora.`",
        ),
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            "        descripcion: `Tienes ${conv.listas_entrenamiento ? 0} conversaciones listas. Se recomiendan al menos 10 para entrenar (ideal: 50+).`",
            "        descripcion: `Tienes ${conv.listas_entrenamiento ?? 0} conversaciones listas. Se recomiendan al menos 10 para entrenar (ideal: 50+).`",
        ),
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            '                      <p className="text-3xl font-bold text-blue-900">{metricas.conversaciones.total ? 0}</p>',
            '                      <p className="text-3xl font-bold text-blue-900">{metricas.conversaciones.total ?? 0}</p>',
        ),
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            '                      <p className="text-3xl font-bold text-purple-900">{metricas.conversaciones.con_calificacion ? 0}</p>',
            '                      <p className="text-3xl font-bold text-purple-900">{metricas.conversaciones.con_calificacion ?? 0}</p>',
        ),
        (
            "components/configuracion/EntrenamientoMejorado.tsx",
            "                        {metricas.conversaciones.listas_entrenamiento ? 0}",
            "                        {metricas.conversaciones.listas_entrenamiento ?? 0}",
        ),
        (
            "components/configuracion/GmailPipelineCard.tsx",
            "        throw new Error(err.detail ? `Error ${res.status}`)",
            "        throw new Error(String(err.detail ?? `Error ${res.status}`))",
        ),
        (
            "components/configuracion/GmailPipelineCard.tsx",
            "      const name = res.headers.get('Content-Disposition')?.match(/filename=\"?([^\";]+)\"?/)?.[1] ? 'Pagos_Gmail_temporal.xlsx'",
            "      const name = res.headers.get('Content-Disposition')?.match(/filename=\"?([^\";]+)\"?/)?.[1] ?? 'Pagos_Gmail_temporal.xlsx'",
        ),
        (
            "components/configuracion/GmailPipelineCard.tsx",
            "                  \u00faltima ejecuci\u00f3n: {status.last_status ? '-'} \u2022 {status.last_emails} correos, {status.last_files} archivos",
            "                  \u00daltima ejecuci\u00f3n: {status.last_status ?? '-'} \u2022 {status.last_emails} correos, {status.last_files} archivos",
        ),
        (
            "components/configuracion/ModelosVehiculosConfig.tsx",
            "      const payload = { modelo: modeloFormateado, activo: formData.activo ? true, precio: precioVal }",
            "      const payload = { modelo: modeloFormateado, activo: !!formData.activo, precio: precioVal }",
        ),
        (
            "components/configuracion/tabs/ConfigGeneralTab.tsx",
            "      if (!validacion.valido) error = validacion.error ? null",
            "      if (!validacion.valido) error = validacion.error ?? null",
        ),
        (
            "components/dashboard/ChartWithDateRangeSlider.tsx",
            "  const labelFrom = data[fromIndex]?.[dataKey] ? ''",
            "  const labelFrom = data[fromIndex]?.[dataKey] ?? ''",
        ),
        (
            "components/dashboard/ChartWithDateRangeSlider.tsx",
            "  const labelTo = data[toIndex]?.[dataKey] ? ''",
            "  const labelTo = data[toIndex]?.[dataKey] ?? ''",
        ),
        (
            "components/dashboard/DashboardFiltrosPanel.tsx",
            "                value={filtrosTemporales.analista ? '__ALL__'}",
            "                value={filtrosTemporales.analista ?? '__ALL__'}",
        ),
        (
            "components/dashboard/DashboardFiltrosPanel.tsx",
            "                value={filtrosTemporales.concesionario ? '__ALL__'}",
            "                value={filtrosTemporales.concesionario ?? '__ALL__'}",
        ),
        (
            "components/dashboard/DashboardFiltrosPanel.tsx",
            "                value={filtrosTemporales.modelo ? '__ALL__'}",
            "                value={filtrosTemporales.modelo ?? '__ALL__'}",
        ),
        (
            "components/notificaciones/ConfiguracionNotificaciones.tsx",
            "    emailsPruebas = [data.emails_pruebas[0] ?? '', data.emails_pruebas[1] ? '']",
            "    emailsPruebas = [data.emails_pruebas[0] ?? '', data.emails_pruebas[1] ?? '']",
        ),
        (
            "components/notificaciones/ConfiguracionNotificaciones.tsx",
            "      plantilla_id: c.plantilla_id ? null,",
            "      plantilla_id: c.plantilla_id ?? null,",
        ),
        (
            "components/notificaciones/ConfiguracionNotificaciones.tsx",
            "      programador: c.programador ? HORA_DEFAULT,",
            "      programador: c.programador ?? HORA_DEFAULT,",
        ),
        (
            "components/notificaciones/ConfiguracionNotificaciones.tsx",
            "        const { enviados, fallidos, sin_email, omitidos_config } = res ? {}",
            "        const { enviados, fallidos, sin_email, omitidos_config } = res ?? {}",
        ),
        (
            "components/notificaciones/ConfiguracionNotificaciones.tsx",
            "          toast.success(`Env\u00edos masivos prueba: ${enviados ? 0} enviados, ${fallidos ? 0} fallidos, ${sin_email ? 0} sin email.`)",
            "          toast.success(`Env\u00edos masivos prueba: ${enviados ?? 0} enviados, ${fallidos ?? 0} fallidos, ${sin_email ?? 0} sin email.`)",
        ),
        (
            "components/notificaciones/DocumentosPdfAnexos.tsx",
            ") => setArchivo(e.target.files?.[0] ? null)} />",
            ") => setArchivo(e.target.files?.[0] ?? null)} />",
        ),
        (
            "components/notificaciones/GeneraVariables.tsx",
            "                  checked={nuevaVariable.activa ? true}",
            "                  checked={!!nuevaVariable.activa}",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "        setCiudadDefault(pdfData.ciudad_default ? 'Guacara')",
            "        setCiudadDefault(pdfData.ciudad_default ?? 'Guacara')",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "        const cuerpoPrincipal = pdfData.cuerpo_principal ? DEFAULT_CUERPO",
            "        const cuerpoPrincipal = pdfData.cuerpo_principal ?? DEFAULT_CUERPO",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "        setFirma(pdfData.firma ? pdfData.clausula_septima ? DEFAULT_CLAUSULA)",
            "        setFirma(pdfData.firma ?? pdfData.clausula_septima ?? DEFAULT_CLAUSULA)",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "      const start = el.selectionStart ? current.length",
            "      const start = el.selectionStart ?? current.length",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "      const end = el.selectionEnd ? current.length",
            "      const end = el.selectionEnd ?? current.length",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "      const start = el.selectionStart ? 0",
            "      const start = el.selectionStart ?? 0",
        ),
        (
            "components/notificaciones/PlantillaAnexoPdf.tsx",
            "      const end = el.selectionEnd ? 0",
            "      const end = el.selectionEnd ?? 0",
        ),
        (
            "components/notificaciones/PlantillaPdfCobranza.tsx",
            "          setCiudadDefault(pdfData.ciudad_default ? 'Guacara')",
            "          setCiudadDefault(pdfData.ciudad_default ?? 'Guacara')",
        ),
        (
            "components/notificaciones/PlantillaPdfCobranza.tsx",
            "          setCuerpoPrincipal(pdfData.cuerpo_principal ? DEFAULT_CUERPO)",
            "          setCuerpoPrincipal(pdfData.cuerpo_principal ?? DEFAULT_CUERPO)",
        ),
        (
            "components/notificaciones/PlantillaPdfCobranza.tsx",
            "          setClausulaSeptima(pdfData.clausula_septima ? DEFAULT_CLAUSULA)",
            "          setClausulaSeptima(pdfData.clausula_septima ?? DEFAULT_CLAUSULA)",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "      const start = (el as any).selectionStart ? current.length",
            "      const start = (el as any).selectionStart ?? current.length",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "      const end = (el as any).selectionEnd ? current.length",
            "      const end = (el as any).selectionEnd ?? current.length",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "      const start = el.selectionStart ? 0",
            "      const start = el.selectionStart ?? 0",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "      const end = el.selectionEnd ? 0",
            "      const end = el.selectionEnd ?? 0",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "                        const start = elTarget.selectionStart ? currentTarget.length",
            "                        const start = elTarget.selectionStart ?? currentTarget.length",
        ),
        (
            "components/notificaciones/PlantillasNotificaciones.tsx",
            "                        const end = elTarget.selectionEnd ? currentTarget.length",
            "                        const end = elTarget.selectionEnd ?? currentTarget.length",
        ),
        (
            "components/notificaciones/VinculacionPlantillaAnexoPdf.tsx",
            "        const label = tipoToLabel.get(key) ? key",
            "        const label = tipoToLabel.get(key) ?? key",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "      const d = e.datos ? {}",
            "      const d = e.datos ?? {}",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "      const registrados = result.registros_procesados ? 0",
            "      const registrados = result.registros_procesados ?? 0",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "      const filasOmitidas = result.filas_omitidas ? 0",
            "      const filasOmitidas = result.filas_omitidas ?? 0",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "      const numErrores = result.errores_total ? result.errores?.length?? 0",
            "      const numErrores = result.errores_total ?? result.errores?.length ?? 0",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "                      <span className=\"font-semibold\">{results.registros_procesados ? 0} pago(s) registrado(s)</span>",
            "                      <span className=\"font-semibold\">{results.registros_procesados ?? 0} pago(s) registrado(s)</span>",
        ),
        (
            "components/pagos/ExcelUploader.tsx",
            "                        {(results.errores_total ? results.errores?.length?? 0)} fila(s) con error. Revisa la tabla inferior para ver fila, c\u00e9dula y descripci\u00f3n.",
            "                        {(results.errores_total ?? results.errores?.length ?? 0)} fila(s) con error. Revisa la tabla inferior para ver fila, c\u00e9dula y descripci\u00f3n.",
        ),
    ]

    failed: list[str] = []
    for rel, old, new in fixes:
        p = ROOT / rel
        if not p.exists():
            failed.append(f"missing file {rel}")
            continue
        if not replace_one(p, old, new):
            failed.append(f"no match {rel}: {old[:70]}...")

    for msg in failed:
        print("FAIL:", msg)
    if failed:
        raise SystemExit(1)
    print("ok", len(fixes), "replacements")


if __name__ == "__main__":
    main()
