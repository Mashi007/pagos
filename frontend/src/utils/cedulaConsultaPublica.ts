/**
 * Cédula en flujos públicos (estado de cuenta, cobros) y filtros internos (préstamos):
 * tolerar pegado con puntos, comas, guiones, espacios y variantes Unicode; validar como V/E/G/J + 6–11 dígitos.
 */

export const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

/**
 * Deja solo V, E, G, J y dígitos ASCII (tras NFKC), quitando separadores y basura de pegado.
 * Uso en onChange del input para alinear con el backend y con normalizarCedulaParaProcesar.
 */
export function extraerCaracteresCedulaPublica(raw: string): string {
  let s: string
  try {
    s = raw.normalize('NFKC')
  } catch {
    s = raw
  }
  return s
    .trim()
    .toUpperCase()
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/[^VEGJ0-9]/g, '')
}

export function normalizarCedulaParaProcesar(val: string): {
  valido: boolean
  valorParaEnviar?: string
  error?: string
} {
  const s = extraerCaracteresCedulaPublica(val)

  if (!s) return { valido: false, error: 'Ingrese el número de cédula.' }

  if (!/^[VEGJ]?\d+$/.test(s)) {
    return {
      valido: false,
      error:
        'Solo se permiten letra V, E, G o J y números. Revise el texto pegado.',
    }
  }

  if (/^\d{6,11}$/.test(s)) return { valido: true, valorParaEnviar: 'V' + s }

  if (CEDULA_REGEX.test(s)) return { valido: true, valorParaEnviar: s }

  return {
    valido: false,
    error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos.',
  }
}

/**
 * Campo "Buscar" en préstamos (cédula o nombre): si el texto completo es una cédula válida
 * (con separadores), devuelve el valor canónico para la API; si no, el texto recortado (nombre, etc.).
 */
export function normalizarBusquedaPrestamosSearch(raw: string): string {
  const t = raw.trim()
  if (!t) return ''
  const v = normalizarCedulaParaProcesar(t)
  if (v.valido && v.valorParaEnviar) return v.valorParaEnviar
  return t
}
