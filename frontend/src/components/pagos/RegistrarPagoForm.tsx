import { useState, useEffect, useMemo } from 'react'

import { motion, AnimatePresence } from 'framer-motion'

import {
  X,
  DollarSign,
  Calendar,
  CreditCard,
  FileText,
  Building2,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
} from 'lucide-react'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import { pagoService, type PagoCreate } from '../../services/pagoService'

import { pagoConErrorService } from '../../services/pagoConErrorService'

import { usePrestamosByCedula, usePrestamo } from '../../hooks/usePrestamos'

import { useDebounce } from '../../hooks/useDebounce'

import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'

import {
  opcionesBancoConValorActual,
  SIN_ESPECIFICAR_VALUE,
} from '../../constants/institucionesBancariasPagos'

import { BASE_PATH } from '../../config/env'

import { getTasaPorFecha } from '../../services/tasaCambioService'

import {
  getErrorMessage,
  isAxiosError,
  getErrorDetail,
} from '../../types/errors'

import type { Prestamo } from '../../types'

import {
  normalizarNumeroDocumento,
  NUMERO_DOCUMENTO_MAX_LEN,
  pareceCedulaEnCampoDocumento,
} from '../../utils/pagoExcelValidation'

import { hoyYmdCaracas } from '../../utils/fechaZona'

const DUPLICADO_DOCUMENTO_UI =
  'Este comprobante ya fue registrado. Verifique el numero_documento.'

const DUPLICADO_HUELLA_UI =
  'Pago duplicado detectado para este prestamo, fecha, monto y referencia.'

interface RegistrarPagoFormProps {
  onClose: () => void

  onSuccess: () => void

  pagoInicial?: Partial<PagoCreate>

  pagoId?: number // Si está presente, es modo edición

  /** Si true, muestra "Guardar y Procesar": actualiza BD y aplica reglas (conciliación + aplicar a cuotas) */

  modoGuardarYProcesar?: boolean

  /** Si true, edición usa pagos_con_errores */

  esPagoConError?: boolean

  /**
   * Si true, exige URL de comprobante aunque la fecha no sea «hoy» en Caracas.
   * Por defecto el enlace es opcional salvo la regla de fecha (hoy Caracas) y validación de URL si se completa.
   */
  requiereLinkComprobante?: boolean

  /**
   * Revisión manual: ID del préstamo que se está editando. Garantiza que ese crédito
   * (p. ej. LIQUIDADO) figure en el selector y pase validación aunque la lista por cédula falle o venga incompleta.
   */
  prestamoContextoRevisionManualId?: number
}

export function RegistrarPagoForm({
  onClose,
  onSuccess,
  pagoInicial,
  pagoId,
  modoGuardarYProcesar,
  esPagoConError,
  requiereLinkComprobante,
  prestamoContextoRevisionManualId,
}: RegistrarPagoFormProps) {
  const isEditing = !!pagoId

  const [formData, setFormData] = useState<PagoCreate>({
    cedula_cliente: pagoInicial?.cedula_cliente || '',

    prestamo_id: pagoInicial?.prestamo_id || null,

    fecha_pago:
      pagoInicial?.fecha_pago || new Date().toISOString().split('T')[0],

    monto_pagado: pagoInicial?.monto_pagado || 0,

    numero_documento: pagoInicial?.numero_documento || '',

    institucion_bancaria: pagoInicial?.institucion_bancaria || null,

    notas: pagoInicial?.notas || null,

    link_comprobante: pagoInicial?.link_comprobante ?? null,
  })

  const [isSubmitting, setIsSubmitting] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})

  const [monedaRegistro, setMonedaRegistro] = useState<'USD' | 'BS'>(() =>
    (pagoInicial as { moneda_registro?: string } | undefined)
      ?.moneda_registro === 'BS'
      ? 'BS'
      : 'USD'
  )

  const [puedePagarBs, setPuedePagarBs] = useState<boolean | null>(null)

  const [consultandoBs, setConsultandoBs] = useState(false)

  const [tasaBd, setTasaBd] = useState<number | null>(null)

  const [tasaBdLoading, setTasaBdLoading] = useState(false)

  const [tasaManual, setTasaManual] = useState('')

  // Debounce de la cédula para buscar préstamos

  const debouncedCedula = useDebounce(formData.cedula_cliente, 500)

  // Buscar préstamos cuando cambia la cédula (con al menos 2 caracteres)

  const { data: prestamos, isLoading: isLoadingPrestamos } =
    usePrestamosByCedula(debouncedCedula.length >= 2 ? debouncedCedula : '')

  // Información del préstamo seleccionado (el crédito solo puede ser uno de la lista por cédula)

  const { data: prestamoSeleccionado } = usePrestamo(formData.prestamo_id || 0)

  const pidRevisionCtx =
    prestamoContextoRevisionManualId && prestamoContextoRevisionManualId > 0
      ? prestamoContextoRevisionManualId
      : 0

  const { data: prestamoContextoRevisionManual } = usePrestamo(pidRevisionCtx)

  /** Incluye el préstamo cargado por ID si la lista por cédula aún no lo trae (evita placeholder "Seleccione el crédito" con valor 478). */
  const opcionesBancoSelect = useMemo(
    () => opcionesBancoConValorActual(formData.institucion_bancaria),
    [formData.institucion_bancaria]
  )

  const bancoSelectValue = (() => {
    const t = (formData.institucion_bancaria || '').trim()
    if (!t) return SIN_ESPECIFICAR_VALUE
    return t
  })()

  const prestamosParaSelect = useMemo((): Prestamo[] => {
    const list = Array.isArray(prestamos) ? [...prestamos] : []

    const mergeIfMissing = (base: Prestamo[], p?: Prestamo): Prestamo[] => {
      if (!p?.id) return base
      if (base.some(x => x.id === p.id)) return base
      return [p, ...base]
    }

    let out = list
    const pCtx = prestamoContextoRevisionManual as Prestamo | undefined
    if (pidRevisionCtx > 0 && pCtx?.id === pidRevisionCtx) {
      out = mergeIfMissing(out, pCtx)
    }

    const pid = formData.prestamo_id
    if (!pid || out.some(p => p.id === pid)) {
      return out
    }
    const psel = prestamoSeleccionado as Prestamo | undefined
    if (psel && psel.id === pid) {
      return mergeIfMissing(out, psel)
    }
    return out
  }, [
    prestamos,
    formData.prestamo_id,
    prestamoSeleccionado,
    pidRevisionCtx,
    prestamoContextoRevisionManual,
  ])

  const exigeComprobantePorFechaCaracas = useMemo(() => {
    const fp = (formData.fecha_pago || '').trim()
    if (!fp) return false
    return fp === hoyYmdCaracas()
  }, [formData.fecha_pago])

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

  // Auto-seleccionar préstamo si hay solo uno disponible

  useEffect(() => {
    if (prestamos && prestamos.length === 1 && !formData.prestamo_id) {
      setFormData(prev => ({ ...prev, prestamo_id: prestamos[0].id }))
    } else if (prestamos && prestamos.length === 0) {
      // No borrar crédito al editar o si venía préstamo en pagoInicial (lista puede cargar tarde o Radix sin ítem).
      const preservarCredito =
        isEditing ||
        (pagoInicial?.prestamo_id != null &&
          Number(pagoInicial.prestamo_id) > 0)
      if (preservarCredito) {
        return
      }
      setFormData(prev => ({ ...prev, prestamo_id: null }))
    }
  }, [prestamos, isEditing, pagoInicial?.prestamo_id, formData.prestamo_id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validaciones segun criterios documentados

    // Validar campos básicos

    const newErrors: Record<string, string> = {}

    const hoyCaracas = hoyYmdCaracas()

    if (!formData.cedula_cliente) {
      newErrors.cedula_cliente = 'Cédula requerida'
    }

    // Crédito: solo se acepta uno de la lista obtenida por cédula (tabla prestamos). Si hay más de uno, debe escogerse.

    if (prestamosParaSelect.length > 0 && !formData.prestamo_id) {
      newErrors.prestamo_id =
        prestamosParaSelect.length > 1
          ? 'Debe escoger un crédito de la lista'
          : 'Debe seleccionar el crédito'
    }

    const permiteCreditoRevisionManual =
      !!prestamoContextoRevisionManualId &&
      formData.prestamo_id === prestamoContextoRevisionManualId

    if (
      formData.prestamo_id &&
      prestamosParaSelect.length > 0 &&
      !prestamosParaSelect.some(p => p.id === formData.prestamo_id) &&
      !permiteCreditoRevisionManual
    ) {
      newErrors.prestamo_id =
        'El crédito debe ser uno de la lista para esta cédula'
    }

    // CRITERIO 1: Verificación de cédula del pago vs cédula del préstamo

    const prestamoParaCedula: Prestamo | undefined =
      permiteCreditoRevisionManual &&
      (prestamoContextoRevisionManual as Prestamo | undefined)?.id ===
        formData.prestamo_id
        ? (prestamoContextoRevisionManual as Prestamo)
        : (prestamoSeleccionado as Prestamo | undefined)

    if (formData.prestamo_id && prestamoParaCedula) {
      if (formData.cedula_cliente !== prestamoParaCedula.cedula) {
        newErrors.cedula_cliente = `La cédula del pago (${formData.cedula_cliente}) no coincide con la cédula del préstamo (${prestamoParaCedula.cedula}). El pago solo se aplicará si las cédulas coinciden.`

        newErrors.prestamo_id =
          'La cédula del pago debe coincidir con la cédula del préstamo seleccionado'
      }
    }

    // CRITERIO 2: Validación de monto

    if (!formData.monto_pagado || formData.monto_pagado <= 0) {
      newErrors.monto_pagado = 'Monto inválido. Debe ser mayor a cero'
    } else if (formData.monto_pagado > 1000000) {
      newErrors.monto_pagado = 'Monto muy alto. Por favor verifique el valor'
    }

    // CRITERIO 3: Número de documento (misma lógica que carga masiva Excel)

    const numeroDocumentoNormalizado = normalizarNumeroDocumento(
      formData.numero_documento
    )

    if (!numeroDocumentoNormalizado) {
      newErrors.numero_documento = 'Número de documento requerido'
    } else if (pareceCedulaEnCampoDocumento(formData.numero_documento)) {
      newErrors.numero_documento =
        'No ingrese la cédula aquí. Use el campo de cédula del cliente; en documento va la referencia o comprobante del banco (regla alineada con carga masiva).'
    } else if (numeroDocumentoNormalizado.length > NUMERO_DOCUMENTO_MAX_LEN) {
      newErrors.numero_documento = `El número de documento no puede superar ${NUMERO_DOCUMENTO_MAX_LEN} caracteres.`
    }

    // CRITERIO 4: Validación de fecha (Caracas; antes del comprobante para no exigir URL en fechas inválidas)

    if (!formData.fecha_pago) {
      newErrors.fecha_pago = 'Fecha de pago requerida'
    } else if (formData.fecha_pago > hoyCaracas) {
      newErrors.fecha_pago =
        'La fecha de pago no puede ser posterior a hoy (America/Caracas).'
    }

    const linkComprobanteTrim = (formData.link_comprobante || '').trim()

    const fechaPagoPermitida =
      !!formData.fecha_pago && formData.fecha_pago <= hoyCaracas

    const exigeComprobantePorFecha =
      fechaPagoPermitida && formData.fecha_pago >= hoyCaracas

    if (exigeComprobantePorFecha && !linkComprobanteTrim) {
      newErrors.link_comprobante =
        'Para fecha de pago desde hoy (America/Caracas) debe indicar el enlace al comprobante (imagen o PDF).'
    } else if (requiereLinkComprobante && !linkComprobanteTrim) {
      newErrors.link_comprobante =
        'Enlace al comprobante (imagen o PDF) requerido en revisión manual.'
    } else if (linkComprobanteTrim) {
      try {
        const u = new URL(linkComprobanteTrim)
        if (!['http:', 'https:'].includes(u.protocol)) {
          newErrors.link_comprobante =
            'El comprobante debe ser una URL http o https válida.'
        }
      } catch {
        newErrors.link_comprobante = 'URL de comprobante no válida.'
      }
    }

    if (monedaRegistro === 'BS') {
      const tm = parseFloat(String(tasaManual).replace(',', '.'))

      if (!tasaBd && (!Number.isFinite(tm) || tm <= 0)) {
        newErrors.general =
          'Bolivares: no hay tasa en BD para esa fecha; ingrese tasa manual (Bs por 1 USD).'
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)

      return
    }

    setIsSubmitting(true)

    try {
      // Aplicar normalización al número de documento antes de enviar

      const datosEnvio: any = {
        ...formData,

        numero_documento: numeroDocumentoNormalizado,

        moneda_registro: monedaRegistro,

        link_comprobante: linkComprobanteTrim || null,
      }

      if (monedaRegistro === 'BS' && !tasaBd) {
        const tm = parseFloat(String(tasaManual).replace(',', '.'))

        if (Number.isFinite(tm) && tm > 0) datosEnvio.tasa_cambio_manual = tm
      }

      // Siempre conciliar cuando hay crédito asignado: así el backend aplica el pago a cuotas

      // (desde tabla normal o desde "Revisar Pagos" con Guardar y Procesar)

      if (formData.prestamo_id && formData.monto_pagado > 0) {
        datosEnvio.conciliado = true
      }

      if (isEditing && pagoId) {
        if (esPagoConError) {
          await pagoConErrorService.update(pagoId, datosEnvio)
        } else {
          await pagoService.updatePago(pagoId, datosEnvio)
        }

        // La asignación a cuotas la hace el backend al recibir conciliado=true (con prestamo_id y monto)
      } else {
        await pagoService.createPago(datosEnvio)
      }

      onSuccess()
    } catch (error: unknown) {
      console.error(
        `Error ${isEditing ? 'actualizando' : 'registrando'} pago:`,
        error
      )

      let errorMessage = getErrorMessage(error)

      if (isAxiosError(error)) {
        const status = error.response?.status
        const detail = getErrorDetail(error)
        const detailLower = (detail || '').toLowerCase()

        if (status === 409 && detailLower.includes('huella funcional')) {
          errorMessage = DUPLICADO_HUELLA_UI
        } else if (
          status === 409 &&
          (detailLower.includes('numero_documento') ||
            detailLower.includes('documento'))
        ) {
          errorMessage = DUPLICADO_DOCUMENTO_UI
        } else if (detail) {
          errorMessage = detail
        }
      }

      setErrors({
        general:
          errorMessage ||
          `Error al ${isEditing ? 'actualizar' : 'registrar'} el pago`,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95 }}
          className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-lg bg-white shadow-xl"
        >
          {/* Header fijo (fuera del scroll, evita efecto scroll-linked en Firefox) */}

          <div className="flex flex-shrink-0 items-center justify-between rounded-t-lg border-b bg-white p-4">
            <h2 className="text-xl font-bold">
              {isEditing ? 'Editar Pago' : 'Registrar Pago'}
            </h2>

            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Form con scroll */}

          <form
            onSubmit={handleSubmit}
            className="min-h-0 flex-1 space-y-6 overflow-y-auto p-6"
          >
            {/* Error general */}

            {!isEditing && !requiereLinkComprobante && (
              <div className="rounded border border-amber-100 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
                <p>
                  Para elegir moneda (Bs./USD), adjuntar comprobante y recibo
                  PDF con la tasa del dia de la fecha de pago, use{' '}
                  <a
                    href={`${BASE_PATH}/${SEGMENTO_INFOPAGOS}`.replace(
                      /\/+/g,
                      '/'
                    )}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-amber-900 underline"
                  >
                    Infopagos
                  </a>
                  . Este formulario es para registro o edición directa en la
                  tabla interna de pagos (conciliación).
                </p>
              </div>
            )}

            {requiereLinkComprobante && (
              <div className="rounded border border-sky-100 bg-sky-50/90 px-3 py-2 text-xs text-sky-950">
                <p>
                  <strong>Revisión manual:</strong> indique la URL del
                  comprobante (foto o PDF en Drive, etc.). El sistema no admite
                  el mismo Nº de documento dos veces; si ya existe, el servidor
                  rechazará el guardado.
                </p>
              </div>
            )}

            {errors.general && (
              <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                {errors.general}
              </div>
            )}

            {/* Cédula e ID Préstamo */}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Cédula Cliente <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="text"
                    value={formData.cedula_cliente}
                    onChange={e => {
                      setFormData({
                        ...formData,
                        cedula_cliente: e.target.value,
                        prestamo_id: null,
                      })
                    }}
                    className={`pl-10 ${errors.cedula_cliente ? 'border-red-500' : ''}`}
                    placeholder="V12345678"
                  />
                </div>

                {errors.cedula_cliente && (
                  <p className="text-sm text-red-600">
                    {errors.cedula_cliente}
                  </p>
                )}

                {isLoadingPrestamos && formData.cedula_cliente.length >= 2 && (
                  <p className="flex items-center gap-1 text-xs text-blue-600">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Buscando préstamos...
                  </p>
                )}

                {!isLoadingPrestamos &&
                  prestamos &&
                  prestamos.length > 0 &&
                  formData.cedula_cliente.length >= 2 && (
                    <p className="flex items-center gap-1 text-xs text-green-600">
                      <CheckCircle className="h-3 w-3" />
                      {prestamos.length} préstamo
                      {prestamos.length !== 1 ? 's' : ''} encontrado
                      {prestamos.length !== 1 ? 's' : ''}
                    </p>
                  )}

                {!isLoadingPrestamos &&
                  prestamos &&
                  prestamos.length === 0 &&
                  formData.cedula_cliente.length >= 2 && (
                    <p className="text-xs text-yellow-600">
                      No se encontraron préstamos para esta cédula
                    </p>
                  )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Crédito al que aplica el pago{' '}
                  {formData.cedula_cliente &&
                    prestamosParaSelect.length > 0 && (
                      <span className="text-red-500">*</span>
                    )}
                </label>

                {prestamos && prestamos.length > 1 && (
                  <p className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-600">
                    Esta persona tiene {prestamos.length} préstamos. Seleccione
                    a cuál se carga este pago.
                  </p>
                )}

                {prestamosParaSelect.length > 0 ? (
                  <Select
                    value={formData.prestamo_id?.toString() || undefined}
                    onValueChange={value =>
                      setFormData({ ...formData, prestamo_id: parseInt(value) })
                    }
                  >
                    <SelectTrigger
                      className={errors.prestamo_id ? 'border-red-500' : ''}
                    >
                      <SelectValue
                        placeholder={
                          prestamosParaSelect.length > 1
                            ? 'Seleccione el crédito'
                            : 'Seleccione un crédito'
                        }
                      />
                    </SelectTrigger>

                    <SelectContent>
                      {prestamosParaSelect.map(prestamo => {
                        const modelo =
                          (prestamo as any).modelo_vehiculo ||
                          (prestamo as any).modelo ||
                          prestamo.producto ||
                          ''

                        const concesionario =
                          (prestamo as any).concesionario || ''

                        const desc =
                          [modelo, concesionario].filter(Boolean).join(' · ') ||
                          prestamo.estado

                        return (
                          <SelectItem
                            key={prestamo.id}
                            value={prestamo.id.toString()}
                          >
                            ID {prestamo.id} - {desc} - $
                            {Number(prestamo.total_financiamiento ?? 0).toFixed(
                              2
                            )}
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                ) : formData.cedula_cliente &&
                  prestamos &&
                  prestamos.length === 0 &&
                  prestamosParaSelect.length === 0 ? (
                  <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    No hay préstamo asociado
                  </div>
                ) : null}

                {(errors.prestamo_id ||
                  (formData.cedula_cliente &&
                    prestamosParaSelect.length > 0 &&
                    !formData.prestamo_id)) && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.prestamo_id ||
                      (prestamosParaSelect.length > 1
                        ? 'Debe escoger un crédito de la lista'
                        : 'Debe seleccionar un crédito')}
                  </p>
                )}

                {/* Verificación de cédula del préstamo vs cédula del pago */}

                {formData.prestamo_id &&
                  prestamoSeleccionado &&
                  formData.cedula_cliente && (
                    <div
                      className={`flex items-start gap-2 rounded p-2 text-xs ${
                        formData.cedula_cliente === prestamoSeleccionado.cedula
                          ? 'border border-green-200 bg-green-50 text-green-700'
                          : 'border border-red-200 bg-red-50 text-red-700'
                      }`}
                    >
                      {formData.cedula_cliente ===
                      prestamoSeleccionado.cedula ? (
                        <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      )}

                      <div>
                        {formData.cedula_cliente ===
                        prestamoSeleccionado.cedula ? (
                          <span className="font-medium">Cédulas coinciden</span>
                        ) : (
                          <div>
                            <span className="font-medium">
                              {' '}
                              Cédulas no coinciden
                            </span>

                            <p className="mt-1">
                              Cédula del pago:{' '}
                              <strong>{formData.cedula_cliente}</strong>
                              <br />
                              Cédula del préstamo:{' '}
                              <strong>{prestamoSeleccionado.cedula}</strong>
                              <br />
                              <span className="text-xs">
                                El pago solo se aplicará si las cédulas
                                coinciden.
                              </span>
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {puedePagarBs === true && (
              <div className="space-y-2 rounded border border-slate-200 bg-slate-50/80 p-3">
                <label className="text-sm font-medium text-gray-700">
                  Moneda del pago <span className="text-red-500">*</span>
                </label>

                <Select
                  value={monedaRegistro}
                  onValueChange={v => setMonedaRegistro(v as 'USD' | 'BS')}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Moneda" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="USD">Dolares (USD)</SelectItem>

                    <SelectItem value="BS">Bolivares (Bs.)</SelectItem>
                  </SelectContent>
                </Select>

                <p className="text-xs text-gray-600">
                  La opcion en bolivares solo esta disponible para cedulas
                  autorizadas en la lista de pagos en bolivares.
                </p>
              </div>
            )}

            {consultandoBs && (
              <p className="text-xs text-blue-600">
                Consultando autorizacion bolivares...
              </p>
            )}

            {/* Fecha y Monto */}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Pago <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="date"
                    value={formData.fecha_pago}
                    onChange={e =>
                      setFormData({ ...formData, fecha_pago: e.target.value })
                    }
                    className={`pl-10 ${errors.fecha_pago ? 'border-red-500' : ''}`}
                    max={hoyYmdCaracas()}
                  />
                </div>

                {errors.fecha_pago && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.fecha_pago}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  {monedaRegistro === 'BS'
                    ? 'Monto (Bs.)'
                    : 'Monto pagado (USD)'}{' '}
                  <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="number"
                    step="0.01"
                    value={formData.monto_pagado}
                    onChange={e =>
                      setFormData({
                        ...formData,
                        monto_pagado: parseFloat(e.target.value) || 0,
                      })
                    }
                    className={`pl-10 ${errors.monto_pagado ? 'border-red-500' : ''}`}
                    placeholder="0.00"
                  />
                </div>

                {errors.monto_pagado && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.monto_pagado}
                  </p>
                )}

                {monedaRegistro === 'BS' && (
                  <div className="mt-2 space-y-2 rounded border border-amber-100 bg-amber-50/80 p-2 text-xs text-amber-950">
                    <p>
                      {tasaBdLoading
                        ? 'Consultando tasa en BD para la fecha de pago...'
                        : tasaBd
                          ? `Tasa oficial en BD para esta fecha: ${tasaBd} Bs. por 1 USD.`
                          : 'No hay tasa en BD para esa fecha. Ingrese tasa manual (Bs por 1 USD).'}
                    </p>

                    {!tasaBd && !tasaBdLoading && (
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center">
                        <label className="font-medium">
                          Tasa manual (Bs/USD)
                        </label>

                        <Input
                          type="number"
                          step="0.000001"
                          value={tasaManual}
                          onChange={e => setTasaManual(e.target.value)}
                          className="max-w-xs"
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Información sobre cómo se aplicará el pago */}

                {formData.monto_pagado > 0 &&
                  formData.prestamo_id &&
                  prestamoSeleccionado && (
                    <div className="rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-700">
                      <div className="flex items-start gap-2">
                        <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />

                        <div>
                          <p className="mb-1 font-medium">
                            {' '}
                            Cómo se aplicará el pago:
                          </p>

                          <ul className="ml-2 list-inside list-disc space-y-1">
                            <li>
                              Se aplicará a las cuotas más antiguas primero (por
                              fecha de vencimiento)
                            </li>

                            <li>
                              Se distribuirá proporcionalmente entre capital e
                              interés
                            </li>

                            {formData.monto_pagado >= 500 && (
                              <li>
                                Si el monto cubre una cuota completa y sobra, el
                                exceso se aplicará a la siguiente cuota
                              </li>
                            )}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {/* Banco (misma variable que plantilla Excel / listado) */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Banco</label>

              <div className="relative">
                <Building2 className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-gray-400" />

                <Select
                  value={bancoSelectValue}
                  onValueChange={v =>
                    setFormData({
                      ...formData,
                      institucion_bancaria:
                        v === SIN_ESPECIFICAR_VALUE ? null : v,
                    })
                  }
                >
                  <SelectTrigger className="w-full pl-10">
                    <SelectValue placeholder="Seleccione banco" />
                  </SelectTrigger>

                  <SelectContent className="max-h-[min(24rem,70vh)]">
                    <SelectItem value={SIN_ESPECIFICAR_VALUE}>
                      Sin especificar
                    </SelectItem>

                    {opcionesBancoSelect.map(b => (
                      <SelectItem key={b} value={b}>
                        {b}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Número de Documento */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Número de Documento <span className="text-red-500">*</span>
              </label>

              <div className="relative">
                <FileText className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                <Input
                  type="text"
                  value={formData.numero_documento}
                  onChange={e =>
                    setFormData({
                      ...formData,
                      numero_documento: e.target.value,
                    })
                  }
                  onBlur={() => {
                    const n = normalizarNumeroDocumento(
                      formData.numero_documento
                    )
                    const raw = String(formData.numero_documento ?? '').trim()
                    if (n !== raw) {
                      setFormData(prev => ({
                        ...prev,
                        numero_documento: n,
                      }))
                    }
                  }}
                  className={`pl-10 ${errors.numero_documento ? 'border-red-500' : ''}`}
                  placeholder="Número de referencia"
                />
              </div>

              {errors.numero_documento && (
                <p className="text-sm text-red-600">
                  {errors.numero_documento}
                </p>
              )}
            </div>

            {/* Comprobante (URL) - revisión manual y trazabilidad */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Comprobante (URL){' '}
                {requiereLinkComprobante || exigeComprobantePorFechaCaracas ? (
                  <span className="text-red-500">*</span>
                ) : (
                  <span className="text-xs font-normal text-gray-500">
                    (opcional si la fecha es anterior a hoy en Caracas)
                  </span>
                )}
              </label>

              <div className="relative">
                <Upload className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                <Input
                  type="url"
                  inputMode="url"
                  autoComplete="off"
                  value={formData.link_comprobante || ''}
                  onChange={e =>
                    setFormData({
                      ...formData,
                      link_comprobante: e.target.value || null,
                    })
                  }
                  className={`pl-10 ${errors.link_comprobante ? 'border-red-500' : ''}`}
                  placeholder="https://… (enlace al comprobante)"
                />
              </div>

              {errors.link_comprobante && (
                <p className="text-sm text-red-600">
                  {errors.link_comprobante}
                </p>
              )}

              {exigeComprobantePorFechaCaracas && (
                <p className="text-xs text-amber-800">
                  Obligatorio: la fecha de pago es hoy (America/Caracas).
                  Adjunte enlace al comprobante (imagen o PDF).
                </p>
              )}

              {(() => {
                const u = (formData.link_comprobante || '').trim()

                if (!u) return null

                const base = u.split(/[?#]/)[0].toLowerCase()

                const esImg = /\.(jpe?g|png|gif|webp|bmp|svg)$/.test(base)

                if (!esImg) return null

                return (
                  <div className="overflow-hidden rounded border bg-muted/40 p-2">
                    <p className="mb-2 text-xs text-muted-foreground">
                      Vista previa (solo URLs directas a imagen):
                    </p>
                    <img
                      src={u}
                      alt="Vista previa comprobante"
                      className="max-h-40 max-w-full rounded object-contain"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      onError={e => {
                        ;(e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                  </div>
                )
              })()}
            </div>

            {/* Notas */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Notas (Opcional)
              </label>

              <Textarea
                value={formData.notas || ''}
                onChange={e =>
                  setFormData({ ...formData, notas: e.target.value || null })
                }
                placeholder="Observaciones adicionales"
                rows={3}
              />
            </div>

            {modoGuardarYProcesar && (
              <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <div className="flex items-start gap-2">
                  <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />

                  <p>
                    <strong>Guardar y Procesar</strong> actualizará el pago en
                    la base de datos y aplicará las reglas de negocio
                    (conciliación y aplicación a cuotas) automáticamente.
                  </p>
                </div>
              </div>
            )}

            {/* Botones */}

            <div className="flex justify-end gap-3 border-t pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancelar
              </Button>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />

                    {modoGuardarYProcesar
                      ? 'Guardando y procesando...'
                      : isEditing
                        ? 'Actualizando...'
                        : 'Registrando...'}
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />

                    {modoGuardarYProcesar
                      ? 'Guardar y Procesar'
                      : isEditing
                        ? 'Actualizar Pago'
                        : 'Registrar Pago'}
                  </>
                )}
              </Button>
            </div>
          </form>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
