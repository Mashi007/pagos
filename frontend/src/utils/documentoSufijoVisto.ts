/**
 * Sufijo admin (carga masiva / revisión manual): _ + A|P + 4 dígitos
 * (mismo archivo vs otro préstamo en BD). Se elige un código libre: primero
 * al azar (varios intentos), luego barrido secuencial 0000-9999 si hace falta.
 *
 * Tras validar contra BD (`validar-filas-batch`), `autoAplicarSufijosVistoFilasCargaMasiva`
 * aplica estos sufijos solo en filas que siguen siendo duplicadas (archivo o BD), salvo
 * claves marcadas como «justificadas sin sufijo» por el admin.
 */

import {
  NUMERO_DOCUMENTO_MAX_LEN,
  claveDocumentoExcelCompuesta,
  normalizarNumeroDocumento,
} from './pagoExcelValidation'

export const SUFIJO_VISTO_ARCHIVO_RE = /_[AP]\d{4}$/i

export const TOKEN_SUFIJO_VISTO_ARCHIVO_RE = /_([AP]\d{4})$/i

export type AplicarSufijoVistoOptions = {
  /**
   * Si true: quita un _A####/_P#### final, lo marca como usado y asigna uno nuevo.
   * Reservado a la lógica interna automática; no exponer a edición humana.
   */
  reemplazarSufijoAdmin?: boolean
}

/** Tokens A#### / P#### ya presentes al final de numero_documento. */
export function collectTokensSufijoVistoArchivoDesdeFilas(
  rows: { numero_documento?: string | null }[]
): Set<string> {
  const usados = new Set<string>()
  for (const r of rows) {
    const m = String(r.numero_documento ?? '').match(
      TOKEN_SUFIJO_VISTO_ARCHIVO_RE
    )
    if (m) usados.add(m[1].toUpperCase())
  }
  return usados
}

function randomCuatroDigitos(): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const buf = new Uint32Array(1)
    crypto.getRandomValues(buf)
    return String(buf[0] % 10000).padStart(4, '0')
  }
  return String(Math.floor(Math.random() * 10000)).padStart(4, '0')
}

/** Genera token A#### o P#### único dentro de `usados` (aleatorio, luego secuencial). */
export function allocarTokenSufijoVistoArchivo(
  letter: 'A' | 'P',
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

/**
 * Añade _A#### o _P#### al comprobante si aún no tiene sufijo admin.
 * Con `reemplazarSufijoAdmin`, sustituye un sufijo admin ya presente.
 * Respeta NUMERO_DOCUMENTO_MAX_LEN truncando la base si hace falta.
 */
export function aplicarSufijoVistoADocumento(
  numeroDocumentoRaw: string | null | undefined,
  letter: 'A' | 'P',
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

/** Heurística: mensaje de error 409 / detalle indica duplicado ligado a otro préstamo → sufijo P. */
export function letterSufijoVistoDesdeMensajeDuplicado(
  msg: string | undefined
): 'A' | 'P' {
  const m = (msg || '').toLowerCase()
  if (
    m.includes('otro prestamo') ||
    m.includes('otro préstamo') ||
    m.includes('otro credito') ||
    m.includes('otro crédito')
  ) {
    return 'P'
  }
  return 'A'
}

/** Texto fijo: no incluir _A####/_P#### en celdas Excel (origen humano). */
export const MENSAJE_EXCEL_NO_INCLUIR_SUFIJO_VISTO_ADMIN =
  'No incluya en el archivo el sufijo _A#### ni _P#### en el comprobante. El sistema lo asigna solo al validar la carga contra la base de datos.'

/**
 * Bloquea que un humano escriba o pegue el sufijo admin en el comprobante.
 * La asignación permitida es solo la automática (carga masiva) o, en registro
 * unitario, el token en el campo Código vía botón Visto (no _ en documento).
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
    return 'No escriba ni pegue manualmente _A#### ni _P#### en el comprobante. En carga masiva el sistema los asigna al validar; al registrar un pago use el botón Visto (campo Código).'
  }
  if (newHas && oldHad) {
    const mo = oldT.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    const mn = newT.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
    const to = mo ? mo[1].toUpperCase() : ''
    const tn = mn ? mn[1].toUpperCase() : ''
    if (to && tn && to !== tn) {
      return 'No modifique manualmente el código _A####/_P#### del comprobante.'
    }
  }
  return null
}

/** Fila mínima para asignar sufijos en carga masiva (Excel / tabla editable). */
export type FilaDocumentoPagoMasiva = {
  _rowIndex: number
  numero_documento?: string | null
  codigo_documento?: string | null
  prestamo_id?: number | null
}

/**
 * Asigna _A#### / _P#### de forma automática cuando la clave compuesta está repetida
 * en el archivo o reportada duplicada por la BD (mismos mapas que `applyRowValidationsSync`).
 * No modifica filas ya con sufijo admin ni claves en `documentosRepetidosArchivoJustificados`.
 */
export function autoAplicarSufijosVistoFilasCargaMasiva<
  T extends FilaDocumentoPagoMasiva,
>(
  rows: T[],
  prestamoPorDocDupBD: Map<string, number | null>,
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

    const raw = String(snap.numero_documento ?? '').trim()
    if (SUFIJO_VISTO_ARCHIVO_RE.test(raw)) continue

    const dupPrestamoBd = prestamoPorDocDupBD.get(clave) ?? null
    const rowPid = snap.prestamo_id ?? null
    const letter: 'A' | 'P' =
      dupPrestamoBd != null &&
      rowPid != null &&
      Number(dupPrestamoBd) !== Number(rowPid)
        ? 'P'
        : 'A'

    const nuevo = aplicarSufijoVistoADocumento(
      snap.numero_documento,
      letter,
      usados
    )
    const idx = indexPorFila.get(snap._rowIndex)
    if (idx == null) continue
    out[idx] = { ...out[idx], numero_documento: nuevo }
  }

  return out
}
