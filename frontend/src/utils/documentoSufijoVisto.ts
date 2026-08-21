/**
 * Desambiguación de serial (autorizar duplicado del banco).
 *
 * Adelante (único contrato de escritura para serial duplicado, no Binance):
 *   token `D####` en `codigo_documento` → BD: `serial §CD:D####`
 *
 * Legado (solo lectura / no migrar):
 *   - `_A####` / `_P####` pegados al comprobante (Control 5 y cargas antiguas)
 *   - códigos `A####` / `P####` vía §CD:
 *
 * Control 5 (auditoría mismo día+monto) sigue escribiendo `_A/_P` en backend;
 * no se usa aquí para autorizar serial duplicado.
 *
 * Carga masiva: el ojo asigna `codigo_documento` (D####), no modifica el serial.
 */

import { composeNumeroDocumentoAlmacenado } from './documentoPago'
import {
  NUMERO_DOCUMENTO_MAX_LEN,
  claveDocumentoExcelCompuesta,
  normalizarNumeroDocumento,
} from './pagoExcelValidation'

/** Prefijo único de escrituras nuevas (revisión / Excel / Cobros / Infopagos). */
export const PREFIJO_CODIGO_DESAMBIGUACION = 'D' as const

/** Legado Control 5 / cargas antiguas: `_A####` / `_P####` al final del comprobante. */
export const SUFIJO_VISTO_ARCHIVO_RE = /_[AP]\d{4}$/i

export const TOKEN_SUFIJO_VISTO_ARCHIVO_RE = /_([AP]\d{4})$/i

/** Token en campo Código o tras §CD: (nuevo D + legado A/P). */
export const TOKEN_CODIGO_DESAMBIGUACION_RE = /^([APD]\d{4})$/i

const SUFIJO_CD = ' \u00a7CD:'

export type AplicarSufijoVistoOptions = {
  /**
   * Si true: quita un _A####/_P#### final, lo marca como usado y asigna uno nuevo.
   * Solo legado / Control 5; no usar para autorizar serial duplicado nuevo.
   */
  reemplazarSufijoAdmin?: boolean
}

function randomCuatroDigitos(): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const buf = new Uint32Array(1)
    crypto.getRandomValues(buf)
    return String(buf[0] % 10000).padStart(4, '0')
  }
  return String(Math.floor(Math.random() * 10000)).padStart(4, '0')
}

/** Genera token con letra dada único dentro de `usados` (aleatorio, luego secuencial). */
export function allocarTokenSufijoVistoArchivo(
  letter: 'A' | 'P' | 'D',
  usados: Set<string>
): string {
  const maxRandomAttempts = 64
  for (let i = 0; i < maxRandomAttempts; i++) {
    const tok = `${letter}${randomCuatroDigitos()}`
    if (!usados.has(tok)) {
      usados.add(tok)
      return tok
    }
  }
  for (let n = 0; n < 10000; n++) {
    const tok = `${letter}${String(n).padStart(4, '0')}`
    if (!usados.has(tok)) {
      usados.add(tok)
      return tok
    }
  }
  const tok = `${letter}${String(Date.now() % 10000).padStart(4, '0')}`
  if (!usados.has(tok)) {
    usados.add(tok)
    return tok
  }
  return `${letter}9999`
}

/** Token nuevo único `D####` para autorizar serial duplicado. */
export function allocarTokenCodigoDesambiguacion(usados: Set<string>): string {
  return allocarTokenSufijoVistoArchivo(PREFIJO_CODIGO_DESAMBIGUACION, usados)
}

/**
 * @deprecated A/P ya no se eligen al autorizar duplicado; siempre D.
 * Se mantiene por compatibilidad de imports; ignora el mensaje.
 */
export function letterSufijoVistoDesdeMensajeDuplicado(
  _msg?: string
): 'A' | 'P' | 'D' {
  return PREFIJO_CODIGO_DESAMBIGUACION
}

/** Tokens ya usados: legado `_A/_P` en documento + códigos en `codigo_documento` / §CD:. */
export function collectTokensSufijoVistoArchivoDesdeFilas(
  rows: {
    numero_documento?: string | null
    codigo_documento?: string | null
  }[]
): Set<string> {
  const usados = new Set<string>()
  for (const r of rows) {
    const nd = String(r.numero_documento ?? '').trim()
    const mDoc = nd.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    if (mDoc) usados.add(mDoc[1].toUpperCase())
    if (nd.includes(SUFIJO_CD)) {
      const code = nd.split(SUFIJO_CD).pop()?.trim() ?? ''
      const mCd = code.match(TOKEN_CODIGO_DESAMBIGUACION_RE)
      if (mCd) usados.add(mCd[1].toUpperCase())
      else if (code) usados.add(code.toUpperCase().slice(0, 24))
    }
    const c = String(r.codigo_documento ?? '').trim()
    const mc = c.match(TOKEN_CODIGO_DESAMBIGUACION_RE)
    if (mc) usados.add(mc[1].toUpperCase())
    else if (c) usados.add(c.toUpperCase().slice(0, 24))
  }
  return usados
}

/**
 * Legado: añade `_A####` / `_P####` al comprobante (Control 5 / filas antiguas).
 * No usar para autorizar serial duplicado nuevo → preferir `codigo_documento` + D####.
 */
export function aplicarSufijoVistoADocumento(
  numeroDocumentoRaw: string | null | undefined,
  letter: 'A' | 'P' | 'D',
  usados: Set<string>,
  options?: AplicarSufijoVistoOptions
): string {
  const raw = String(numeroDocumentoRaw ?? '').trim()
  const reemplazar = !!options?.reemplazarSufijoAdmin

  if (!reemplazar && SUFIJO_VISTO_ARCHIVO_RE.test(raw)) return raw

  let base = raw
  if (reemplazar) {
    const m = base.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    if (m) {
      usados.add(m[1].toUpperCase())
      base = base.replace(SUFIJO_VISTO_ARCHIVO_RE, '').trim()
    }
  }

  const token = allocarTokenSufijoVistoArchivo(letter, usados)
  const maxBase = NUMERO_DOCUMENTO_MAX_LEN - 1 - token.length
  if (base.length > maxBase) base = base.slice(0, Math.max(0, maxBase))
  const joined = `${base}_${token}`
  return normalizarNumeroDocumento(joined) || joined
}

/**
 * Compone `serial §CD:D####` (o reemplaza código §CD: / quita `_A/_P` legado).
 * Uso: Cobros / Infopagos donde el campo único es numero_operacion.
 */
export function aplicarCodigoDesambiguacionANumeroOperacion(
  numeroOperacionRaw: string | null | undefined,
  usados: Set<string>,
  options?: { reemplazarCodigo?: boolean }
): { numero: string; token: string } | null {
  const raw = String(numeroOperacionRaw ?? '').trim()
  if (!raw) return null

  let base = raw
  let hadCode = false

  if (base.includes(SUFIJO_CD)) {
    const parts = base.split(SUFIJO_CD)
    base = (parts[0] ?? '').trim()
    const prevCode = (parts[1] ?? '').trim()
    if (prevCode) {
      hadCode = true
      usados.add(prevCode.toUpperCase().slice(0, 24))
    }
  }

  const mLegado = base.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
  if (mLegado) {
    hadCode = true
    usados.add(mLegado[1].toUpperCase())
    base = base.replace(SUFIJO_VISTO_ARCHIVO_RE, '').trim()
  }

  if (hadCode && !options?.reemplazarCodigo) {
    return null
  }

  base = (normalizarNumeroDocumento(base) || base).trim()
  if (!base) return null

  const token = allocarTokenCodigoDesambiguacion(usados)
  const composed =
    composeNumeroDocumentoAlmacenado(base, token) || `${base}${SUFIJO_CD}${token}`
  return { numero: composed.slice(0, NUMERO_DOCUMENTO_MAX_LEN), token }
}

/** Texto fijo: no incluir sufijos internos en celdas Excel (origen humano). */
export const MENSAJE_EXCEL_NO_INCLUIR_SUFIJO_VISTO_ADMIN =
  'No incluya en el archivo el sufijo _A####/_P#### ni códigos §CD: en el comprobante. En la tabla de carga use el ícono de ojo en Acción para asignar el código D#### cuando haya duplicado.'

/**
 * Bloquea que un humano escriba o pegue el sufijo legado `_A/_P` en el comprobante.
 * El token nuevo va en Código (Visto / ojo), no en el serial.
 */
export function mensajeEdicionManualSufijoVistoProhibida(
  valorAnterior: string | null | undefined,
  valorNuevo: string | null | undefined
): string | null {
  const oldT = String(valorAnterior ?? '').trim()
  const newT = String(valorNuevo ?? '').trim()
  const oldHad = SUFIJO_VISTO_ARCHIVO_RE.test(oldT)
  const newHas = SUFIJO_VISTO_ARCHIVO_RE.test(newT)
  if (newHas && !oldHad) {
    return 'No escriba ni pegue manualmente _A#### ni _P#### en el comprobante. Use Visto (o el ícono de ojo en carga masiva) para asignar el código D#### en el campo Código.'
  }
  if (newHas && oldHad) {
    const mo = oldT.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    const mn = newT.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    const to = mo ? mo[1].toUpperCase() : ''
    const tn = mn ? mn[1].toUpperCase() : ''
    if (to && tn && to !== tn) {
      return 'No modifique manualmente el sufijo legado _A####/_P#### del comprobante.'
    }
  }
  if (newT.includes('\u00a7CD:') && !oldT.includes('\u00a7CD:')) {
    return 'No escriba §CD: en el comprobante. Use Visto para asignar el código en el campo Código.'
  }
  return null
}

/** Fila mínima para asignar código en carga masiva (Excel / tabla editable). */
export type FilaDocumentoPagoMasiva = {
  _rowIndex: number
  numero_documento?: string | null
  codigo_documento?: string | null
  prestamo_id?: number | null
}

function filaYaDesambiguada(snap: FilaDocumentoPagoMasiva): boolean {
  const raw = String(snap.numero_documento ?? '').trim()
  if (SUFIJO_VISTO_ARCHIVO_RE.test(raw)) return true
  if (raw.includes(SUFIJO_CD)) return true
  if (String(snap.codigo_documento ?? '').trim()) return true
  return false
}

/**
 * Asigna `codigo_documento` = D#### cuando la clave compuesta está repetida
 * (archivo o BD). No modifica el serial ni filas ya desambiguadas.
 */
export function autoAplicarSufijosVistoFilasCargaMasiva<
  T extends FilaDocumentoPagoMasiva,
>(
  rows: T[],
  _prestamoPorDocDupBD: Map<string, number | null>,
  documentosDuplicadosBD: Set<string>,
  documentosRepetidosArchivoJustificados: Set<string>
): T[] {
  const freq = new Map<string, number>()
  for (const r of rows) {
    const cl = claveDocumentoExcelCompuesta(
      r.numero_documento,
      r.codigo_documento ?? null
    )
    if (cl) freq.set(cl, (freq.get(cl) || 0) + 1)
  }

  const usados = collectTokensSufijoVistoArchivoDesdeFilas(rows)
  const out = rows.map(r => ({ ...r }))
  const indexPorFila = new Map(out.map((r, i) => [r._rowIndex, i]))

  const sorted = [...out].sort((a, b) => a._rowIndex - b._rowIndex)

  for (const snap of sorted) {
    const clave = claveDocumentoExcelCompuesta(
      snap.numero_documento,
      snap.codigo_documento ?? null
    )
    if (!clave) continue
    if (documentosRepetidosArchivoJustificados.has(clave)) continue

    const dupArchivo = (freq.get(clave) || 0) > 1
    const dupBD = documentosDuplicadosBD.has(clave)
    if (!dupArchivo && !dupBD) continue
    if (filaYaDesambiguada(snap)) continue

    const token = allocarTokenCodigoDesambiguacion(usados)
    const idx = indexPorFila.get(snap._rowIndex)
    if (idx == null) continue
    out[idx] = { ...out[idx], codigo_documento: token }
  }

  return out
}

/**
 * Asigna `codigo_documento` = D#### solo a la fila indicada (conflicto de serial).
 * No toca el serial; no modifica filas ya con código o sufijo legado.
 */
export function aplicarSufijoVistoUnaFila<T extends FilaDocumentoPagoMasiva>(
  rows: T[],
  targetRowIndex: number,
  _prestamoPorDocDupBD: Map<string, number | null>,
  documentosDuplicadosBD: Set<string>,
  documentosRepetidosArchivoJustificados: Set<string>
): T[] | null {
  const idx = rows.findIndex(r => r._rowIndex === targetRowIndex)
  if (idx < 0) return null

  const snap = rows[idx]
  const clave = claveDocumentoExcelCompuesta(
    snap.numero_documento,
    snap.codigo_documento ?? null
  )
  if (!clave) return null
  if (documentosRepetidosArchivoJustificados.has(clave)) return null
  if (filaYaDesambiguada(snap)) return null

  const freq = new Map<string, number>()
  for (const r of rows) {
    const cl = claveDocumentoExcelCompuesta(
      r.numero_documento,
      r.codigo_documento ?? null
    )
    if (cl) freq.set(cl, (freq.get(cl) || 0) + 1)
  }
  const dupArchivo = (freq.get(clave) || 0) > 1
  const dupBD = documentosDuplicadosBD.has(clave)
  if (!dupArchivo && !dupBD) return null

  const usados = collectTokensSufijoVistoArchivoDesdeFilas(rows)
  const token = allocarTokenCodigoDesambiguacion(usados)

  return rows.map((r, i) =>
    i === idx ? { ...r, codigo_documento: token } : { ...r }
  )
}
