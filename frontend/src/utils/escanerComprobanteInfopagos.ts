/**
 * Ruta unificada Escanear / Reescanear: FormData, mensajes y merge conservador
 * (misma API extraer-comprobante + prompts Gmail; no sobrescribir con vacío).
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

/** Serial Mercantil 740087… (misma regla que plantilla A / pipeline Gmail). */
export function esSerialMercantil740087(digitsOnly: string): boolean {
  return /^740087\d{6,}$/.test(digitsOnly)
}

/**
 * Banco inferido desde la respuesta OCR (Gemini + post-proceso backend).
 * Serial 740087… solo si vino en numero_operacion del OCR.
 */
export function institucionDesdeSugerenciaOcr(
  sugerencia: Pick<
    EscanerInfopagosSugerencia,
    'institucion_financiera' | 'numero_operacion'
  > | null
): string | null {
  const ocr = normalizarInstitucionBancoEscaneo(
    (sugerencia?.institucion_financiera || '').trim()
  )
  if (ocr) return ocr

  const numOcr = (sugerencia?.numero_operacion || '').replace(/\D/g, '')
  if (esSerialMercantil740087(numOcr)) return 'Mercantil'
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

export function traducirDetalleTecnicoExtraccionEscaner(detail: string): string {
  const raw = (detail || '').trim()
  if (!raw) return raw
  const t = raw.toLowerCase()

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
    const detail = (
      err as { response?: { data?: { detail?: unknown } } }
    ).response?.data?.detail
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
 */
export function mergeCamposFormularioDesdeSugerenciaOcr(
  actual: CamposFormularioEscaner,
  sugerencia: EscanerInfopagosSugerencia
): CamposFormularioEscaner {
  const instOcr = institucionDesdeSugerenciaOcr(sugerencia)
  const geminiInst =
    instOcr || (sugerencia.institucion_financiera || '').trim()
  const { institucion, otroInstitucion } = resolverInstitucionDesdeExtraccion(
    geminiInst,
    actual.institucion,
    actual.otroInstitucion
  )
  const fechaExtraida = (sugerencia.fecha_pago || '').trim()
  const numeroExtraido = (sugerencia.numero_operacion || '').trim()
  const mon = sugerencia.moneda === 'BS' ? 'BS' : 'USD'
  const montoNum =
    sugerencia.monto != null && Number.isFinite(Number(sugerencia.monto))
      ? Number(sugerencia.monto)
      : null

  return {
    fechaPago: fechaExtraida || actual.fechaPago,
    institucion: institucion || actual.institucion,
    otroInstitucion: otroInstitucion || actual.otroInstitucion,
    numeroOperacion: numeroExtraido || actual.numeroOperacion,
    monto: montoNum != null ? String(montoNum) : actual.monto,
    moneda: montoNum != null ? mon : actual.moneda,
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

/** Merge conservador para RegistrarPagoForm / modal Editar Pago. */
export function mergePagoRegistrarDesdeSugerenciaOcr(
  actual: CamposPagoRegistrarEscaner,
  sugerencia: EscanerInfopagosSugerencia
): CamposPagoRegistrarEscaner {
  const inst =
    institucionDesdeSugerenciaOcr(sugerencia) ||
    normalizarInstitucionBancoEscaneo(
      (actual.institucion_bancaria || '').trim()
    )
  const fechaOcr = (sugerencia.fecha_pago || '').trim()
  const numeroOcr = (sugerencia.numero_operacion || '').trim()
  const monedaOcr = sugerencia.moneda === 'BS' ? 'BS' : 'USD'
  const montoOcr =
    sugerencia.monto != null && Number.isFinite(Number(sugerencia.monto))
      ? Number(sugerencia.monto)
      : null

  const next: CamposPagoRegistrarEscaner = {
    ...actual,
    fecha_pago: fechaOcr || actual.fecha_pago,
    institucion_bancaria: inst || actual.institucion_bancaria,
    numero_documento: numeroOcr || actual.numero_documento,
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
  } else if (
    sugerencia.moneda === 'BS' ||
    sugerencia.moneda === 'USD'
  ) {
    next.moneda_registro = monedaOcr
  }

  return next
}
