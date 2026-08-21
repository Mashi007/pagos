/**

 * Validación carga masiva de pagos (Excel).

 * Clave única: comprobante normalizado + código opcional (misma lógica que POST /pagos).

 */

import {
  validateExcelFile,
  validateExcelData,
  sanitizeFileName,
} from './excelValidation'

import { composeNumeroDocumentoAlmacenado } from './documentoPago'

/** Texto de observación por columna; se muestra solo en la celda correspondiente del Excel. Especifican exactamente qué falla. */

export const OBSERVACIONES_POR_CAMPO: Record<string, string> = {
  numero_documento:
    'Duplicado Excel (misma clave comprobante + código repetida en el archivo)',

  fecha_pago: 'Fecha inválida o formato incorrecto (use DD/MM/YYYY)',

  cedula: 'Cédula sin préstamo registrado (no figura en tabla préstamos)',

  monto_pagado: 'Monto inválido o ≤ 0',

  prestamo_id: 'Crédito inválido (ID fuera de rango o elegir en lista)',

  conciliado: 'Conciliación inválida',
}

/** Observaciones específicas al enviar a Revisar sin error de validación pero con contexto de crédito. */

export const OBSERVACION_SIN_CREDITO = 'Cédula sin crédito activo'

export const OBSERVACION_MULTIPLES_CREDITOS =
  'Múltiples créditos; elegir uno en la lista'

export interface PagoExcelRow {
  _rowIndex: number

  _validation: Record<string, { isValid: boolean; message?: string }>

  _hasErrors: boolean

  cedula: string

  fecha_pago: string

  monto_pagado: number

  numero_documento: string

  /** Columna opcional «Código» (desambigua mismo comprobante). */
  codigo_documento?: string | null

  prestamo_id: number | null

  conciliado: boolean

  /** Banco / institución (columna Excel "Banco", compatible con plantilla) */

  institucion_bancaria?: string | null

  /** Opcional: columnas moneda / tasa en plantilla Excel */

  moneda_registro?: 'USD' | 'BS'

  tasa_cambio_manual?: number

  /**
   * Si el documento ya existe en BD (validar-filas-batch): id del préstamo del registro existente.
   * `null` si el pago en BD no tiene prestamo_id. No definido si no aplica.
   */

  _prestamoIdExistenteDuplicadoBD?: number | null

  /**
   * Si el documento ya existe en BD y el origen es tabla `pagos`: id del pago existente.
   * Permite acción «Visto» (control 5) desde carga masiva. No definido si no aplica.
   */

  _pagoIdExistenteDuplicadoBD?: number | null

  /** URL del comprobante (columna Link en plantillas; Gmail puede rellenarse vía BD al guardar). */
  link_comprobante?: string | null
}

/** Valor para API: string recortado o null si vacío (máx. 255). */

export function institucionBancariaDesdeExcel(
  v: string | null | undefined
): string | null {
  const s = (v ?? '').toString().trim()

  return s ? s.slice(0, 255) : null
}

/** Id Drive sin https -> URL vista; rutas API (/api/.../comprobante-imagen/) se dejan tal cual. */
export function normalizarLinkComprobanteDesdeExcel(
  v: string | null | undefined
): string | null {
  const s = (v ?? '').toString().trim()

  if (!s) return null
  if (!/^https?:\/\//i.test(s)) {
    if (s.includes('comprobante-imagen') || s.startsWith('/api/')) return s
    return `https://drive.google.com/file/d/${s}/view`
  }
  return s
}

/** Texto de celda hipervinculada (ej. "Ver imagen") sin URL real: no inventar enlace. */
export function linkComprobanteDesdeCeldaExcel(
  raw: string | null | undefined
): string | null {
  const t = (raw ?? '').toString().trim()

  if (!t) return null
  if (/^ver\s*imagen$/i.test(t) || /^ver\s*email$/i.test(t)) return null
  return normalizarLinkComprobanteDesdeExcel(t)
}

export function convertirFechaExcelPago(val: unknown): string {
  if (val == null || val === '') return ''

  if (val instanceof Date) {
    if (Number.isNaN(val.getTime())) return ''

    return `${String(val.getDate()).padStart(2, '0')}/${String(val.getMonth() + 1).padStart(2, '0')}/${val.getFullYear()}`
  }

  const s = String(val).trim()

  if (!s) return ''

  if (/^\d{4,}$/.test(s)) {
    try {
      const d = new Date(1900, 0, 1)

      d.setDate(d.getDate() + parseInt(s, 10) - 2)

      return Number.isNaN(d.getTime())
        ? s
        : `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}/${d.getFullYear()}`
    } catch {
      return s
    }
  }

  if (/^\d{2}\/\d{2}\/\d{4}$/.test(s)) return s

  if (/^\d{2}-\d{2}-\d{2}$/.test(s)) {
    const [d, m, yy] = s.split('-')

    const y =
      parseInt(yy, 10) < 50 ? 2000 + parseInt(yy, 10) : 1900 + parseInt(yy, 10)

    return `${d}/${m}/${y}`
  }

  if (/^\d{2}-\d{2}-\d{4}$/.test(s)) {
    const [d, m, y] = s.split('-')

    return `${d}/${m}/${y}`
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-')

    return `${d}/${m}/${y}`
  }

  const p = new Date(s)

  return !Number.isNaN(p.getTime())
    ? `${String(p.getDate()).padStart(2, '0')}/${String(p.getMonth() + 1).padStart(2, '0')}/${p.getFullYear()}`
    : s
}

export function convertirFechaParaBackendPago(f: string): string {
  if (!f?.trim()) return ''

  const m = f.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)

  return m
    ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`
    : f.trim()
}

const LOOKS_LIKE_CEDULA = /^[VEJZ]\d{6,11}$/i

/** Alineado con backend `pagos.numero_documento` String(100). */
export const NUMERO_DOCUMENTO_MAX_LEN = 100

export function cedulaParaLookup(val: unknown): string {
  if (val == null || val === '') return ''

  const s = String(val).trim()

  if (!s) return ''

  const sinGuion = s.replace(/-/g, '').replace(/\s+/g, '')

  if (LOOKS_LIKE_CEDULA.test(sinGuion)) return sinGuion

  const match = s.match(/[VEJZ]\d{6,11}/i)

  if (match) return match[0].replace(/-/g, '')

  // Si es número plano (6-11 dígitos sin prefijo), normalizar a V+dígitos
  if (/^\d{6,11}$/.test(sinGuion)) return 'V' + sinGuion

  if (/^\d{8}$/.test(sinGuion)) return 'V' + sinGuion

  return s
}

export function cedulaLookupParaFila(
  cedula: string,
  numero_documento: string
): string {
  const fromC = cedulaParaLookup(cedula)

  const fromD = cedulaParaLookup(numero_documento)

  if (fromC && LOOKS_LIKE_CEDULA.test(fromC.replace(/-/g, ''))) return fromC

  if (fromD && LOOKS_LIKE_CEDULA.test(fromD.replace(/-/g, ''))) return fromD

  return fromC || fromD
}

/**
 * Busca prestamos en el mapa con fallbacks: con/sin prefijo V/E/J/Z,
 * sin guiones, upper/lower. Evita mismatch entre "V28480006" y "28480006".
 */
export function buscarEnMapaPrestamos<T>(
  lookup: string,
  mapa: Record<string, T[]>
): T[] {
  if (!lookup) return []
  const sinGuion = lookup.replace(/-/g, '')
  const r1 =
    mapa[lookup] ||
    mapa[sinGuion] ||
    mapa[lookup.toUpperCase()] ||
    mapa[lookup.toLowerCase()] ||
    []
  if (r1.length > 0) return r1
  const sinPrefijo = /^[VEJZ]/i.test(sinGuion) ? sinGuion.slice(1) : null
  if (sinPrefijo) {
    const r2 =
      mapa[sinPrefijo] ||
      mapa[sinPrefijo.toUpperCase()] ||
      mapa[sinPrefijo.toLowerCase()] ||
      []
    if (r2.length > 0) return r2
  }
  const conV = /^\d{6,11}$/.test(sinGuion) ? 'V' + sinGuion : null
  if (conV) {
    const r3 =
      mapa[conV] || mapa[conV.toUpperCase()] || mapa[conV.toLowerCase()] || []
    if (r3.length > 0) return r3
  }
  return []
}

/** True si el valor parece Nº documento (ej. 10+ dígitos, BNC/ZELLE) y no cédula V/E/J/Z. */

export function looksLikeDocumentNotCedula(val: unknown): boolean {
  if (val == null || val === '') return false

  const s = String(val).trim()

  if (!s) return false

  if (LOOKS_LIKE_CEDULA.test(s.replace(/-/g, ''))) return false

  if (/^\d{10,}$/.test(s)) return true

  if (
    /^(BNC|ZELLE|BINANCE|VE\/|BS\.|REF\.?)\s*\/?/i.test(s) ||
    /^[A-Z0-9\/\.\s\-]{10,}$/i.test(s)
  )
    return true

  return false
}

function limpiarDocumento(s: string): string {
  return s.replace(/[\u200B-\u200D\uFEFF\r\n\t]/g, '').trim()
}

/**
 * Entrada manual de serial.
 * Por defecto solo dígitos (conserva `_A####` / `_P####` legado).
 * Zelle: permite letras y números (A-Z0-9).
 * Binance: solo dígitos (no conserva sufijo Control 5).
 */
export function filtrarEntradaSerialSoloDigitos(
  valorNuevo: string,
  valorAnterior?: string | null,
  opts?: { institucionBancaria?: string | null }
): string {
  const v = String(valorNuevo ?? '')
  if (esInstitucionZelleSerial(opts?.institucionBancaria)) {
    return v.replace(/[^A-Za-z0-9]/g, '').toUpperCase()
  }
  if (esInstitucionBinanceSerial(opts?.institucionBancaria)) {
    return v.replace(/\D/g, '')
  }
  const prev = String(valorAnterior ?? '')
  const mVisto = prev.match(/(_[AP]\d{4})$/i)
  if (mVisto && v.toUpperCase().endsWith(mVisto[1].toUpperCase())) {
    const tail = mVisto[1]
    const base = v.slice(0, v.length - tail.length).replace(/\D/g, '')
    return base + tail
  }
  return v.replace(/\D/g, '')
}

/** Texto corto para revisión manual (no ampliar). */
export const ADVERTENCIA_SERIAL_SOLO_NUMEROS = 'Solo se admite números'

export const ADVERTENCIA_SERIAL_ZELLE_ALFANUM =
  'Zelle: solo letras y números (sin espacios ni signos)'

const SUFIJO_CD_DOC = ' \u00a7CD:'

export function esInstitucionBinanceSerial(
  institucionBancaria?: string | null
): boolean {
  return (institucionBancaria || '').toUpperCase().includes('BINANCE')
}

export function esInstitucionZelleSerial(
  institucionBancaria?: string | null
): boolean {
  return (institucionBancaria || '').toUpperCase().includes('ZELLE')
}

/**
 * Serial “de banco” sin sufijos internos (§CD: / Control 5 _A####|_P####).
 * No altera el valor en BD; solo para validar letras/signos (bancos no Binance).
 */
export function serialBaseSinSufijosInternos(
  numeroDocumento: string | null | undefined
): string {
  let s = String(numeroDocumento ?? '').trim()
  if (!s) return ''
  if (/^REOCR-PEND-\d+$/i.test(s)) return ''
  if (s.includes(SUFIJO_CD_DOC)) {
    s = s.split(SUFIJO_CD_DOC)[0] ?? ''
  } else if (s.includes('\u00a7CD:')) {
    s = s.split('\u00a7CD:')[0] ?? ''
  }
  s = s.replace(/_[AP]\d{4}$/i, '').trim()
  return s
}

/** True si el serial base tiene letras o signos (cualquier banco; omite sufijos internos). */
export function serialBaseTieneLetrasOSignos(
  numeroDocumento: string | null | undefined
): boolean {
  const base = serialBaseSinSufijosInternos(numeroDocumento)
  if (!base) return false
  return /[^\d]/.test(base)
}

/**
 * Revisión manual: serial inválido.
 * Zelle: admite A-Z0-9; inválido si hay signos/espacios en la base.
 * Binance: NO se omiten §CD: ni _A####/_P#### — el documento debe ser solo dígitos.
 * Otros bancos: se omiten esos sufijos internos al evaluar letras/signos.
 */
export function serialDocumentoInvalidoRevisionManual(
  numeroDocumento: string | null | undefined,
  institucionBancaria?: string | null
): boolean {
  const s = String(numeroDocumento ?? '').trim()
  if (!s || /^REOCR-PEND-\d+$/i.test(s)) return false
  if (esInstitucionZelleSerial(institucionBancaria)) {
    const base = serialBaseSinSufijosInternos(s)
    if (!base) return false
    return /[^A-Za-z0-9]/.test(base)
  }
  if (esInstitucionBinanceSerial(institucionBancaria)) {
    return /[^\d]/.test(s)
  }
  return serialBaseTieneLetrasOSignos(s)
}

export function pagosPrestamoConSerialLetrasOSignos<
  T extends {
    id?: number | null
    numero_documento?: string | null
    institucion_bancaria?: string | null
  },
>(pagos: T[]): T[] {
  return pagos.filter(p =>
    serialDocumentoInvalidoRevisionManual(
      p.numero_documento,
      p.institucion_bancaria
    )
  )
}


/**

 * Normaliza el valor a string para usar como clave de documento.
 * Serial: solo dígitos (sin letras ni signos). Conserva `_A####` / `_P####` (Control 5).

 */

/** Clave canónica compuesta para duplicados (archivo / BD / API). */
export function claveDocumentoExcelCompuesta(
  numero_documento: unknown,
  codigo_documento?: string | null,
  institucionBancaria?: string | null
): string {
  const base = normalizarNumeroDocumento(numero_documento, {
    institucionBancaria,
  })
  return (
    composeNumeroDocumentoAlmacenado(base || null, codigo_documento ?? null) ||
    ''
  )
}

/**
 * Misma unicidad que en BD / POST pagos: comprobante normalizado + código opcional.
 * Minúsculas para resaltar duplicados en listas sin depender de mayúsculas.
 */
export function claveDocumentoPagoListaNormalizada(
  numero_documento: unknown,
  codigo_documento?: string | null,
  institucionBancaria?: string | null
): string {
  return claveDocumentoExcelCompuesta(
    numero_documento,
    codigo_documento,
    institucionBancaria
  )
    .trim()
    .toLowerCase()
}

export function esDocumentoMarcadorPendienteReocr(
  numero: string | null | undefined
): boolean {
  return /^REOCR-PEND-\d+$/i.test(String(numero ?? '').trim())
}

/**
 * Celda de lista / Excel: comprobante que ve el usuario + código (sin marcador interno §CD:).
 */
export function textoDocumentoPagoParaListado(
  numero_documento: string | null | undefined,
  codigo_documento?: string | null
): string {
  const base = (numero_documento ?? '').trim()
  const c = (codigo_documento ?? '').trim()
  if (!base || esDocumentoMarcadorPendienteReocr(base)) return '-'
  if (!c) return base
  return `${base} · ${c}`
}

export function normalizarNumeroDocumento(
  val: unknown,
  opts?: { institucionBancaria?: string | null }
): string {
  if (val == null || val === '') return ''

  let s: string

  if (typeof val === 'object' && val !== null) {
    const rt = (val as { richText?: Array<{ text?: string }> }).richText

    if (Array.isArray(rt)) s = rt.map(x => x?.text ?? '').join('')
    else if ((val as { text?: string }).text != null)
      s = String((val as { text?: string }).text)
    else return ''
  } else if (typeof val === 'number') {
    if (Number.isNaN(val)) return ''

    if (Math.abs(val) >= 1e12) {
      try {
        s = BigInt(Math.round(val)).toString()
      } catch {
        s = val.toFixed(0)
      }
    } else if (Math.abs(val) >= 1e11) {
      s = String(Math.round(val))
    } else {
      s = Math.round(val).toString()
    }
  } else {
    s = String(val)
  }

  s = s.trim()

  if (s.startsWith("'")) s = s.slice(1).trim()

  s = limpiarDocumento(s)

  if (!s || /^(nan|none|undefined|na|n\/a)$/i.test(s)) return ''

  if (/^REOCR-PEND-\d+$/i.test(s)) return s

  if (/^\d+\.?\d*[eE][+-]?\d+$/.test(s)) {
    try {
      const n = parseFloat(s)

      if (!Number.isNaN(n) && isFinite(n))
        s =
          Math.abs(n) >= 1e15
            ? BigInt(Math.round(n)).toString()
            : String(Math.round(n))
    } catch {
      /* mantener s */
    }
  }

  s = s.replace(/\s+/g, ' ').trim()

  const mVisto = s.match(/(_[AP]\d{4})$/i)
  let vistoSuf = ''
  if (mVisto) {
    const tok = mVisto[1]
    vistoSuf = `_${tok[1].toUpperCase()}${tok.slice(2)}`
    s = s.slice(0, mVisto.index).trimEnd()
  }

  if (esInstitucionZelleSerial(opts?.institucionBancaria)) {
    const cuerpo = s.replace(/[^A-Za-z0-9]/g, '').toUpperCase()
    if (!cuerpo) return ''
    return cuerpo + vistoSuf
  }

  // Serial base: solo dígitos (cualquier banco no Zelle). Conserva sufijo Control 5.
  const digitos = s.replace(/\D/g, '')
  if (!digitos) return ''
  return digitos + vistoSuf
}

/**
 * True si el valor parece cédula (V/E/J/Z + dígitos), no referencia bancaria.
 * Misma idea que al parsear Excel: no usar el campo documento para la cédula.
 */
export function pareceCedulaEnCampoDocumento(val: unknown): boolean {
  const s = normalizarNumeroDocumento(val)
  if (!s) return false
  const compact = s.replace(/-/g, '').replace(/\s+/g, '')
  return LOOKS_LIKE_CEDULA.test(compact)
}

const MAX_MONTO = 999_999_999_999.99

const FECHA_REGEX = /^(\d{2})\/(\d{2})\/(\d{4})$/

/** Valida un campo de fila de pago. Retorna isValid + mensaje de error. */

export function validatePagoField(
  field: string,

  value: string | number,

  options?: {
    documentosExistentes?: Set<string>

    documentosEnArchivo?: Set<string>

    cedulasInvalidas?: Set<string>

    documentosDuplicadosBD?: Set<string>

    codigoDocumento?: string | null

    institucionBancaria?: string | null
  }
): { isValid: boolean; message?: string } {
  // ── CÉDULA ──────────────────────────────────────────────────────────────

  if (field === 'cedula') {
    const s = String(value ?? '')
      .trim()
      .replace(/-/g, '')
      .toUpperCase()

    if (!s) return { isValid: false, message: 'Cédula requerida' }

    if (!/^[VEJZ]\d{6,11}$/.test(s))
      return { isValid: false, message: 'Formato inválido (ej: V12345678)' }

    if (options?.cedulasInvalidas?.has(s))
      return { isValid: false, message: 'Cédula sin préstamo registrado' }

    return { isValid: true }
  }

  // ── FECHA ────────────────────────────────────────────────────────────────

  if (field === 'fecha_pago') {
    const s = String(value ?? '').trim()

    if (!s) return { isValid: false, message: 'Fecha requerida' }

    const m = FECHA_REGEX.exec(s)

    if (!m)
      return { isValid: false, message: 'Formato inválido (use DD/MM/YYYY)' }

    const [, dd, mm, yyyy] = m

    const d = new Date(Number(yyyy), Number(mm) - 1, Number(dd))

    if (
      d.getFullYear() !== Number(yyyy) ||
      d.getMonth() !== Number(mm) - 1 ||
      d.getDate() !== Number(dd)
    )
      return { isValid: false, message: 'Fecha inválida' }

    const year = Number(yyyy)

    if (year < 2000 || year > 2100)
      return { isValid: false, message: 'Año fuera de rango (2000-2100)' }

    return { isValid: true }
  }

  // ── MONTO ────────────────────────────────────────────────────────────────

  if (field === 'monto_pagado') {
    const n =
      typeof value === 'number'
        ? value
        : parseFloat(String(value ?? '').replace(',', '.'))

    if (isNaN(n) || !isFinite(n))
      return { isValid: false, message: 'Monto inválido' }

    if (n <= 0)
      return { isValid: false, message: 'El monto debe ser mayor a 0' }

    if (n > MAX_MONTO)
      return {
        isValid: false,
        message: `Monto excede el límite (${MAX_MONTO})`,
      }

    return { isValid: true }
  }

  // ── NÚMERO DE DOCUMENTO ──────────────────────────────────────────────────

  if (field === 'numero_documento') {
    const raw = String(value ?? '').trim()
    const inst = options?.institucionBancaria
    const docNorm =
      value === 'NaN' || value === 'nan' || value === 'undefined'
        ? ''
        : normalizarNumeroDocumento(value, { institucionBancaria: inst }) || ''

    if (!docNorm) {
      if (raw && /[^\d\s]/.test(raw.replace(/_[AP]\d{4}$/i, ''))) {
        const zelle = esInstitucionZelleSerial(inst)
        if (zelle && !/[^A-Za-z0-9\s]/.test(raw.replace(/_[AP]\d{4}$/i, ''))) {
          return { isValid: true }
        }
        return {
          isValid: false,
          message: zelle
            ? ADVERTENCIA_SERIAL_ZELLE_ALFANUM
            : ADVERTENCIA_SERIAL_SOLO_NUMEROS,
        }
      }
      return { isValid: true } // Documento vacío es permitido
    }

    const clave = claveDocumentoExcelCompuesta(
      docNorm,
      options?.codigoDocumento ?? null,
      options?.institucionBancaria
    )

    if (!clave) return { isValid: true }

    if (options?.documentosDuplicadosBD?.has(clave))
      return {
        isValid: false,
        message: 'Documento ya existe en la base de datos',
      }

    if (options?.documentosExistentes?.has(clave))
      return {
        isValid: false,
        message: 'Documento duplicado. No se aceptan duplicados.',
      }

    if (options?.documentosEnArchivo?.has(clave))
      return { isValid: false, message: 'Documento repetido en este archivo' }

    return { isValid: true }
  }

  return { isValid: true }
}

export { validateExcelFile, validateExcelData, sanitizeFileName }

export function parsePrestamoIdFromNumeroCredito(val: unknown): number | null {
  if (val == null) return null
  const s = String(val).trim()
  if (s === '' || s === 'none') return null
  if (/^\d+$/.test(s)) {
    const n = parseInt(s, 10)
    return Number.isNaN(n) ? null : n
  }
  const parts = s.match(/\d+/g)
  if (!parts?.length) return null
  const n = parseInt(parts[parts.length - 1], 10)
  return Number.isNaN(n) ? null : n
}
