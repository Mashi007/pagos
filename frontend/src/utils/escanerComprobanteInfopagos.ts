/**
 * Ruta unificada Escanear / Reescanear: FormData, mensajes y merge.
 * Alta de pago: merge conservador. Re-escaneo (`modoReescaneo`): vacía y solo OCR.
 */
import type {
  EscanerInfopagosExtraerResponse,
  EscanerInfopagosSugerencia,
} from '../services/cobrosService'
import {
  FUENTE_TASA_DEFAULT,
  type FuenteTasaCambio,
} from '../constants/fuenteTasaCambio'
import { resolverInstitucionDesdeExtraccion } from '../pages/escanerInfopagosLoteModel'
import { hoyYmdCaracas } from './fechaZona'

/**
 * Fecha OCR para escanear/reescanear: vacía si falta o si coincide con hoy Caracas
 * (Gemini suele copiar la referencia del prompt; no sustituye la fecha impresa).
 */
export function fechaPagoDesdeExtraccionOcrConfiable(
  fechaRaw: string | null | undefined
): string {
  const t = (fechaRaw || '').trim().slice(0, 10)
  if (!t) return ''
  if (t === hoyYmdCaracas()) return ''
  return t
}

export function normalizarInstitucionBancoEscaneo(raw: string): string | null {
  const t = (raw || '').trim()
  if (!t) return null
  if (/^binance$/i.test(t)) return 'Binance'
  if (/^bnc$/i.test(t) || /^bnv$/i.test(t)) return 'BNC'
  if (/mercantil/i.test(t)) return 'Mercantil'
  if (/^recibo/i.test(t)) return 'Recibo'
  if (/banco de venezuela|^bdv$/i.test(t)) return 'Banco de Venezuela'
  return t
}

/** Serial Mercantil 740087 + 9 dígitos = 15 (misma regla que plantilla A / pipeline Gmail). */
export function esSerialMercantil740087(digitsOnly: string): boolean {
  return /^740087\d{9}$/.test(digitsOnly)
}

/** Codigo validador Mercantil (ej. 9824-20260528-105636-DCME-…), no es el Serial. */
export function esCodigoDcmeMercantil(s: string): boolean {
  const t = (s || '').trim()
  if (!t) return false
  return /-\d{8}-\d{6}-DCME-/i.test(t)
}

/** Serial Mercantil 740087 + 9 digitos (15) desde cualquier fragmento OCR. */
export function extraerSerialMercantil7400(texto: string): string {
  if (!texto) return ''
  const compact = texto.replace(/\D/g, '')
  const m15 = compact.match(/740087\d{9}/)
  return m15 ? m15[0] : ''
}

/** Referencias que no son numero de operacion del comprobante (sistema / validador). */
export function esNumeroDocumentoSinteticoOcrInvalido(num: string): boolean {
  const t = (num || '').trim().toUpperCase()
  if (!t) return false
  if (/^REOCR-PEND-\d+$/i.test(t)) return false
  if (t.startsWith('ABONOS-DRIVE-')) return true
  if (esCodigoDcmeMercantil(num)) return true
  return false
}

/**
 * Numero de documento utilizable tras re-escaneo: prioriza Serial 740087…;
 * descarta DCME, ABONOS-DRIVE y otros sinteticos (solo lo leido en imagen).
 */
export function numeroOperacionOcrParaReescaneo(
  sugerencia: Pick<
    EscanerInfopagosSugerencia,
    'numero_operacion' | 'institucion_financiera'
  > &
    Partial<Pick<EscanerInfopagosSugerencia, 'notas_modelo'>>
): string {
  const raw = (sugerencia.numero_operacion || '').trim()
  const aux = `${raw}\n${(sugerencia.notas_modelo || '').trim()}`
  const serial =
    extraerSerialMercantil7400(raw) || extraerSerialMercantil7400(aux)
  if (serial) return serial
  if (!raw || esNumeroDocumentoSinteticoOcrInvalido(raw)) return ''
  return raw
}

/** Fecha impresa en bloque DCME Mercantil (2º bloque YYYYMMDD del papel). */
export function fechaPagoDesdeBloqueDcmeMercantil(texto: string): string {
  const m = (texto || '').match(/-\d{4}-(\d{8})-\d{6}-DCME-/i)
  if (!m?.[1] || m[1].length !== 8) return ''
  const ymd = m[1]
  const iso = `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}`
  return fechaPagoDesdeExtraccionOcrConfiable(iso) || iso
}

/** Fecha desde OCR: campo fecha_pago o bloque DCME visible en numero/notas. */
export function fechaPagoDesdeSugerenciaOcrReescaneo(
  sugerencia: Pick<
    EscanerInfopagosSugerencia,
    'fecha_pago' | 'numero_operacion' | 'notas_modelo'
  >
): string {
  const directa = fechaPagoDesdeExtraccionOcrConfiable(sugerencia.fecha_pago)
  if (directa) return directa
  const ctx = `${sugerencia.numero_operacion || ''} ${sugerencia.notas_modelo || ''}`
  return fechaPagoDesdeBloqueDcmeMercantil(ctx)
}

/**
 * Banco inferido desde la respuesta OCR (Gemini + post-proceso backend).
 * Serial 740087…, codigo DCME o marcadores 0105 / RECAUDACION en notas.
 */
export function institucionDesdeSugerenciaOcr(
  sugerencia:
    | (Pick<
        EscanerInfopagosSugerencia,
        'institucion_financiera' | 'numero_operacion'
      > &
        Partial<Pick<EscanerInfopagosSugerencia, 'notas_modelo'>>)
    | null
): string | null {
  const ocr = normalizarInstitucionBancoEscaneo(
    (sugerencia?.institucion_financiera || '').trim()
  )
  if (ocr) return ocr

  const numRaw = (sugerencia?.numero_operacion || '').trim()
  const ctx = `${numRaw} ${(sugerencia?.notas_modelo || '').trim()}`
  if (extraerSerialMercantil7400(ctx)) return 'Mercantil'
  if (esCodigoDcmeMercantil(numRaw)) return 'Mercantil'
  if (
    /mercantil|0105|rapi-credit|deposito divisas|depósito divisas|recaudaci/i.test(
      ctx
    )
  ) {
    return 'Mercantil'
  }
  return null
}

/** Plantilla opcional pre-OCR: banco ya confirmado en formulario o cartera. */
export function institucionPlantillaConfirmadaEscaneo(
  hint: string | null | undefined
): string | null {
  return normalizarInstitucionBancoEscaneo((hint || '').trim())
}

export type BuildFormDataEscanerOpts = {
  tipoCedula: string
  numeroCedula: string
  comprobante: File
  fuenteTasaCambio?: FuenteTasaCambio
  extraccionSinCliente?: boolean
  prestamoObjetivoId?: number | null
  /** Banco previo en formulario o cartera; se normaliza antes de enviar. */
  institucionPlantillaHint?: string | null
}

/** FormData estándar para POST .../escaner/extraer-comprobante. */
export function buildFormDataEscanerComprobante(
  opts: BuildFormDataEscanerOpts
): FormData {
  const fd = new FormData()
  fd.append('tipo_cedula', (opts.tipoCedula || 'V').trim().toUpperCase())
  fd.append(
    'numero_cedula',
    String(opts.numeroCedula || '')
      .trim()
      .replace(/\D/g, '')
  )
  fd.append('comprobante', opts.comprobante)
  fd.append('fuente_tasa_cambio', opts.fuenteTasaCambio ?? FUENTE_TASA_DEFAULT)
  if (opts.extraccionSinCliente) {
    fd.append('extraccion_sin_cliente', 'true')
  }
  const pid = opts.prestamoObjetivoId
  if (pid != null && Number.isFinite(pid) && pid > 0) {
    fd.append('prestamo_objetivo_id', String(pid))
  }
  const plantilla = institucionPlantillaConfirmadaEscaneo(
    opts.institucionPlantillaHint
  )
  if (plantilla) {
    fd.append('institucion_plantilla', plantilla)
  }
  return fd
}

export function traducirDetalleTecnicoExtraccionEscaner(
  detail: string
): string {
  const raw = (detail || '').trim()
  if (!raw) return raw
  const t = raw.toLowerCase()

  if (t.includes('timeout') || t.includes('econnaborted')) {
    return 'La digitalización tardó demasiado. Espere un momento y vuelva a escanear.'
  }
  const faltaFecha =
    t.includes('valid date or datetime') ||
    t.includes('fecha_pago') ||
    t.includes('input is too short')
  const faltaNumero = t.includes('numero_documento no puede estar vacio')

  if (faltaFecha && faltaNumero) {
    return 'Falta fecha y número de documento en el escaneo.'
  }
  if (faltaFecha) {
    return 'Falta la fecha en el escaneo.'
  }
  if (faltaNumero) {
    return 'Falta el número de documento en el escaneo.'
  }
  return raw
}

export function mensajeErrorExtraccionEscaner(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const detail = (err as { response?: { data?: { detail?: unknown } } })
      .response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return traducirDetalleTecnicoExtraccionEscaner(detail)
    }
    if (Array.isArray(detail)) {
      const msgs = detail
        .map(x =>
          typeof x === 'object' && x && 'msg' in x
            ? String((x as { msg?: string }).msg || '')
            : String(x)
        )
        .filter(Boolean)
      if (msgs.length) {
        return traducirDetalleTecnicoExtraccionEscaner(msgs.join('; '))
      }
    }
  }
  if (err instanceof Error && err.message.trim()) {
    return traducirDetalleTecnicoExtraccionEscaner(err.message)
  }
  return 'Error de red o del servidor al digitalizar el comprobante.'
}

/** Mensaje cuando la API responde ok:false o sin sugerencia. */
export function mensajeFalloExtraccionEscaner(
  res: Pick<
    EscanerInfopagosExtraerResponse,
    'error' | 'validacion_campos' | 'validacion_reglas'
  >
): string {
  return (
    res.validacion_reglas?.trim() ||
    res.validacion_campos?.trim() ||
    res.error?.trim() ||
    'No se pudo digitalizar el comprobante.'
  )
}

export type CamposFormularioEscaner = {
  fechaPago: string
  institucion: string
  otroInstitucion: string
  numeroOperacion: string
  monto: string
  moneda: 'BS' | 'USD'
}

/**
 * Merge conservador: solo reemplaza campos que el OCR devolvió con valor;
 * conserva fecha, banco, número y monto previos si Gemini omitió el dato.
 * Con `reemplazarSinConservarPrevios` (re-escaneo): solo valores OCR confiables.
 */
export function mergeCamposFormularioDesdeSugerenciaOcr(
  actual: CamposFormularioEscaner,
  sugerencia: EscanerInfopagosSugerencia,
  opts?: { reemplazarSinConservarPrevios?: boolean }
): CamposFormularioEscaner {
  const instOcr = institucionDesdeSugerenciaOcr(sugerencia)
  const geminiInst = instOcr || (sugerencia.institucion_financiera || '').trim()
  const { institucion, otroInstitucion } = resolverInstitucionDesdeExtraccion(
    geminiInst,
    actual.institucion,
    actual.otroInstitucion
  )
  const fechaExtraida = fechaPagoDesdeExtraccionOcrConfiable(
    sugerencia.fecha_pago
  )
  const numeroExtraido = (sugerencia.numero_operacion || '').trim()
  const mon = sugerencia.moneda === 'BS' ? 'BS' : 'USD'
  const montoNum =
    sugerencia.monto != null && Number.isFinite(Number(sugerencia.monto))
      ? Number(sugerencia.monto)
      : null
  const soloOcr = Boolean(opts?.reemplazarSinConservarPrevios)

  return {
    fechaPago: soloOcr ? fechaExtraida : fechaExtraida || actual.fechaPago,
    institucion: soloOcr ? institucion : institucion || actual.institucion,
    otroInstitucion: soloOcr
      ? otroInstitucion
      : otroInstitucion || actual.otroInstitucion,
    numeroOperacion: soloOcr
      ? numeroExtraido
      : numeroExtraido || actual.numeroOperacion,
    monto: montoNum != null ? String(montoNum) : soloOcr ? '' : actual.monto,
    moneda: montoNum != null ? mon : soloOcr ? 'USD' : actual.moneda,
  }
}

export type CamposPagoRegistrarEscaner = {
  fecha_pago: string
  institucion_bancaria: string | null
  numero_documento: string
  monto_pagado: number
  monto_bs_original?: number | null
  moneda_registro: 'BS' | 'USD'
}

/** Base vacía antes de re-escanear (fecha, banco, documento, monto, moneda). */
export function camposVaciosOcrRegistrar(): CamposPagoRegistrarEscaner {
  return {
    fecha_pago: '',
    institucion_bancaria: null,
    numero_documento: '',
    monto_pagado: 0,
    monto_bs_original: null,
    moneda_registro: 'USD',
  }
}

/** Merge para RegistrarPagoForm / modal Editar Pago. */
export function mergePagoRegistrarDesdeSugerenciaOcr(
  actual: CamposPagoRegistrarEscaner,
  sugerencia: EscanerInfopagosSugerencia,
  opts?: { modoReescaneo?: boolean }
): CamposPagoRegistrarEscaner {
  const soloOcr = Boolean(opts?.modoReescaneo)
  const base = soloOcr ? camposVaciosOcrRegistrar() : actual
  const inst =
    institucionDesdeSugerenciaOcr(sugerencia) ||
    (soloOcr
      ? null
      : normalizarInstitucionBancoEscaneo(
          (actual.institucion_bancaria || '').trim()
        ))
  const fechaOcr = soloOcr
    ? fechaPagoDesdeSugerenciaOcrReescaneo(sugerencia)
    : fechaPagoDesdeExtraccionOcrConfiable(sugerencia.fecha_pago)
  const numeroOcr = soloOcr
    ? numeroOperacionOcrParaReescaneo(sugerencia)
    : (sugerencia.numero_operacion || '').trim()
  const monedaOcr = sugerencia.moneda === 'BS' ? 'BS' : 'USD'
  const montoOcr =
    sugerencia.monto != null && Number.isFinite(Number(sugerencia.monto))
      ? Number(sugerencia.monto)
      : null

  const next: CamposPagoRegistrarEscaner = {
    ...base,
    fecha_pago: soloOcr ? fechaOcr : fechaOcr || actual.fecha_pago,
    institucion_bancaria: soloOcr
      ? inst || null
      : inst || actual.institucion_bancaria,
    numero_documento: soloOcr
      ? numeroOcr
      : numeroOcr || actual.numero_documento,
  }

  if (montoOcr != null && montoOcr > 0) {
    if (monedaOcr === 'BS') {
      next.moneda_registro = 'BS'
      next.monto_bs_original = montoOcr
      next.monto_pagado = 0
    } else {
      next.moneda_registro = 'USD'
      next.monto_pagado = montoOcr
    }
  } else if (soloOcr) {
    next.moneda_registro = 'USD'
    next.monto_pagado = 0
    next.monto_bs_original = null
  } else if (sugerencia.moneda === 'BS' || sugerencia.moneda === 'USD') {
    next.moneda_registro = monedaOcr
  }

  return next
}
