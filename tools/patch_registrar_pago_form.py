from pathlib import Path

P = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "pagos" / "RegistrarPagoForm.tsx"
text = P.read_text(encoding="utf-8")

A = "import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'\n\nimport {"
if A not in text:
    raise SystemExit("import anchor A")
text = text.replace(
    A,
    "import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'\n\nimport { getTasaPorFecha } from '../../services/tasaCambioService'\n\nimport {",
    1,
)

B = "  const [errors, setErrors] = useState<Record<string, string>>({})\n\n  // Debounce de la c"
if B not in text:
    raise SystemExit("state anchor B")
INSERT_STATE = """  const [errors, setErrors] = useState<Record<string, string>>({})

  const [monedaRegistro, setMonedaRegistro] = useState<'USD' | 'BS'>(() =>
    (pagoInicial as { moneda_registro?: string } | undefined)?.moneda_registro === 'BS'
      ? 'BS'
      : 'USD'
  )

  const [puedePagarBs, setPuedePagarBs] = useState<boolean | null>(null)

  const [consultandoBs, setConsultandoBs] = useState(false)

  const [tasaBd, setTasaBd] = useState<number | null>(null)

  const [tasaBdLoading, setTasaBdLoading] = useState(false)

  const [tasaManual, setTasaManual] = useState('')

  // Debounce de la c"""
text = text.replace(B, INSERT_STATE, 1)

C = "  const { data: prestamoSeleccionado } = usePrestamo(formData.prestamo_id || 0)\n\n  // Auto-seleccionar pr"
if C not in text:
    raise SystemExit("anchor C")
INSERT_EFFECTS = """  const { data: prestamoSeleccionado } = usePrestamo(formData.prestamo_id || 0)

  useEffect(() => {
    let cancelled = false

    const c = debouncedCedula.trim()

    if (c.length < 5) {
      setPuedePagarBs(null)

      return
    }

    setConsultandoBs(true)

    pagoService

      .consultarCedulaReportarBs(c)

      .then(res => {
        if (cancelled) return

        setPuedePagarBs(res.en_lista)

        if (!res.en_lista) setMonedaRegistro('USD')
      })

      .catch(() => {
        if (!cancelled) setPuedePagarBs(false)
      })

      .finally(() => {
        if (!cancelled) setConsultandoBs(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedCedula])

  useEffect(() => {
    if (monedaRegistro !== 'BS') {
      setTasaBd(null)

      return
    }

    const fp = formData.fecha_pago

    if (!fp) {
      setTasaBd(null)

      return
    }

    setTasaBdLoading(true)

    getTasaPorFecha(fp)

      .then(r => setTasaBd(r?.tasa_oficial ?? null))

      .catch(() => setTasaBd(null))

      .finally(() => setTasaBdLoading(false))
  }, [formData.fecha_pago, monedaRegistro])

  // Auto-seleccionar pr"""
text = text.replace(C, INSERT_EFFECTS, 1)

D = "    if (!formData.fecha_pago) {\n      newErrors.fecha_pago = 'Fecha de pago requerida'"
if D not in text:
    raise SystemExit("anchor D validation")
INSERT_VAL = """    if (!formData.fecha_pago) {\n      newErrors.fecha_pago = 'Fecha de pago requerida'"""
# insert after fecha validation block closing brace before `if (Object.keys(newErrors)`
# Find: `if (fechaPago > hoy) {` block end - add BS tasa validation

E = "      if (fechaPago > hoy) {\n        newErrors.fecha_pago = 'La fecha de pago no puede ser futura'\n      }\n    }\n\n    if (Object.keys(newErrors).length > 0) {"
if E not in text:
    raise SystemExit("anchor E")
INSERT_BS_VAL = """      if (fechaPago > hoy) {\n        newErrors.fecha_pago = 'La fecha de pago no puede ser futura'\n      }\n    }\n\n    if (monedaRegistro === 'BS') {\n      const tm = parseFloat(String(tasaManual).replace(',', '.'))\n\n      if (!tasaBd && (!Number.isFinite(tm) || tm <= 0)) {\n        newErrors.general =\n          'Bolivares: no hay tasa en BD para esa fecha; ingrese tasa manual (Bs por 1 USD).'\n      }\n    }\n\n    if (Object.keys(newErrors).length > 0) {"""
text = text.replace(E, INSERT_BS_VAL, 1)

F = """      const datosEnvio: any = {
        ...formData,

        numero_documento: numeroDocumentoNormalizado,
      }"""
if F not in text:
    raise SystemExit("anchor F datosEnvio")
NEW_F = """      const datosEnvio: any = {
        ...formData,

        numero_documento: numeroDocumentoNormalizado,

        moneda_registro: monedaRegistro,
      }

      if (monedaRegistro === 'BS' && !tasaBd) {
        const tm = parseFloat(String(tasaManual).replace(',', '.'))

        if (Number.isFinite(tm) && tm > 0) datosEnvio.tasa_cambio_manual = tm
      }"""
text = text.replace(F, NEW_F, 1)

G = "            {/* Fecha y Monto */}\n\n            <div className=\"grid grid-cols-1 gap-4 md:grid-cols-2\">"
if G not in text:
    raise SystemExit("anchor G UI")
NEW_G = """            {puedePagarBs === true && (
              <div className=\"space-y-2 rounded border border-slate-200 bg-slate-50/80 p-3\">
                <label className=\"text-sm font-medium text-gray-700\">
                  Moneda del pago <span className=\"text-red-500\">*</span>
                </label>

                <Select
                  value={monedaRegistro}
                  onValueChange={v => setMonedaRegistro(v as 'USD' | 'BS')}
                >
                  <SelectTrigger>
                    <SelectValue placeholder=\"Moneda\" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value=\"USD\">Dolares (USD)</SelectItem>

                    <SelectItem value=\"BS\">Bolivares (Bs.)</SelectItem>
                  </SelectContent>
                </Select>

                <p className=\"text-xs text-gray-600\">
                  La opcion en bolivares solo esta disponible para cedulas autorizadas en la lista
                  de pagos en bolivares.
                </p>
              </div>
            )}

            {consultandoBs && (
              <p className=\"text-xs text-blue-600\">Consultando autorizacion bolivares...</p>
            )}

            {/* Fecha y Monto */}

            <div className=\"grid grid-cols-1 gap-4 md:grid-cols-2\">"""
text = text.replace(G, NEW_G, 1)

H = """                <label className=\"text-sm font-medium text-gray-700\">
                  Monto Pagado <span className=\"text-red-500\">*</span>
                </label>"""
if H not in text:
    raise SystemExit("anchor H monto label")
NEW_H = """                <label className=\"text-sm font-medium text-gray-700\">
                  {monedaRegistro === 'BS' ? 'Monto (Bs.)' : 'Monto pagado (USD)'}{' '}
                  <span className=\"text-red-500\">*</span>
                </label>"""
text = text.replace(H, NEW_H, 1)

I = """                {errors.monto_pagado && (
                  <p className=\"flex items-center gap-1 text-sm text-red-600\">
                    <AlertCircle className=\"h-4 w-4\" />

                    {errors.monto_pagado}
                  </p>
                )}

                {/* Informaci"""
if I not in text:
    raise SystemExit("anchor I after monto errors")
NEW_I = """                {errors.monto_pagado && (
                  <p className=\"flex items-center gap-1 text-sm text-red-600\">
                    <AlertCircle className=\"h-4 w-4\" />

                    {errors.monto_pagado}
                  </p>
                )}

                {monedaRegistro === 'BS' && (
                  <div className=\"mt-2 space-y-2 rounded border border-amber-100 bg-amber-50/80 p-2 text-xs text-amber-950\">
                    <p>
                      {tasaBdLoading
                        ? 'Consultando tasa en BD para la fecha de pago...'
                        : tasaBd
                          ? `Tasa oficial en BD para esta fecha: ${tasaBd} Bs. por 1 USD.`
                          : 'No hay tasa en BD para esa fecha. Ingrese tasa manual (Bs por 1 USD).'}
                    </p>

                    {!tasaBd && !tasaBdLoading && (
                      <div className=\"flex flex-col gap-1 sm:flex-row sm:items-center\">
                        <label className=\"font-medium\">Tasa manual (Bs/USD)</label>

                        <Input
                          type=\"number\"
                          step=\"0.000001\"
                          value={tasaManual}
                          onChange={e => setTasaManual(e.target.value)}
                          className=\"max-w-xs\"
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Informaci"""
text = text.replace(I, NEW_I, 1)

P.write_text(text, encoding="utf-8")
print("RegistrarPagoForm patched")
