from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"


def sub(path: str, old: str, new: str) -> bool:
    p = ROOT / path
    t = p.read_text(encoding="utf-8")
    if old not in t:
        return False
    p.write_text(t.replace(old, new, 1), encoding="utf-8")
    return True


def main() -> None:
    p = ROOT / "components/configuracion/GmailPipelineCard.tsx"
    t = p.read_text(encoding="utf-8")
    t2 = t.replace("{status.last_status ? '-'}", "{status.last_status ?? '-'}")
    if t2 != t:
        p.write_text(t2, encoding="utf-8")
        print("GmailPipelineCard last_status")

    rest: list[tuple[str, str, str]] = [
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
            "          toast.success(`Envios masivos prueba: ${enviados ? 0} enviados, ${fallidos ? 0} fallidos, ${sin_email ? 0} sin email.`)",
            "          toast.success(`Envios masivos prueba: ${enviados ?? 0} enviados, ${fallidos ?? 0} fallidos, ${sin_email ?? 0} sin email.`)",
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
            '                      <span className="font-semibold">{results.registros_procesados ? 0} pago(s) registrado(s)</span>',
            '                      <span className="font-semibold">{results.registros_procesados ?? 0} pago(s) registrado(s)</span>',
        ),
    ]

    failed: list[str] = []
    for rel, old, new in rest:
        if not sub(rel, old, new):
            failed.append(rel + " :: " + old[:60])

    # ExcelUploader line 1713 may have mojibake - try regex
    ex = ROOT / "components/pagos/ExcelUploader.tsx"
    tex = ex.read_text(encoding="utf-8")
    old1713 = "                        {(results.errores_total ? results.errores?.length?? 0)} fila(s) con error."
    new1713 = "                        {(results.errores_total ?? results.errores?.length ?? 0)} fila(s) con error."
    if old1713 in tex:
        ex.write_text(tex.replace(old1713, new1713, 1), encoding="utf-8")
        print("ExcelUploader 1713 ascii")
    elif "results.errores?.length??" in tex:
        tex2 = tex.replace("results.errores?.length??", "results.errores?.length ??")
        tex2 = tex2.replace(
            "{(results.errores_total ? results.errores?.length ?? 0)}",
            "{(results.errores_total ?? results.errores?.length ?? 0)}",
            1,
        )
        if tex2 != tex:
            ex.write_text(tex2, encoding="utf-8")
            print("ExcelUploader 1713 fuzzy")
        else:
            failed.append("ExcelUploader 1713")
    else:
        failed.append("ExcelUploader 1713 not found")

    # ConfiguracionNotificaciones toast - try with accented Envíos if file has UTF-8
    cn = ROOT / "components/notificaciones/ConfiguracionNotificaciones.tsx"
    ctext = cn.read_text(encoding="utf-8")
    for a, b in [
        (
            "${enviados ? 0} enviados, ${fallidos ? 0} fallidos, ${sin_email ? 0} sin email.",
            "${enviados ?? 0} enviados, ${fallidos ?? 0} fallidos, ${sin_email ?? 0} sin email.",
        ),
    ]:
        if a in ctext:
            cn.write_text(ctext.replace(a, b, 1), encoding="utf-8")
            print("ConfiguracionNotificaciones toast counts")
            ctext = cn.read_text(encoding="utf-8")
            break
    else:
        if "enviados ? 0" in ctext:
            failed.append("ConfiguracionNotificaciones toast pattern")
        else:
            print("ConfiguracionNotificaciones toast already ok")

    for msg in failed:
        print("FAIL:", msg)
    if any("FAIL" not in x for x in failed) and failed:
        pass
    if failed:
        raise SystemExit(1)
    print("remainder ok")


if __name__ == "__main__":
    main()
