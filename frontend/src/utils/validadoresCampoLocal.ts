/**
 * Validación local de campos (mismas reglas que backend validadores/routes.py).
 * Evita POST /validadores/validar-campo en tiempo real cuando el API está frío en Render.
 */

export type ValidacionCampoLocal = {
  valido: boolean
  valor_formateado?: string
  error?: string
  mensaje?: string
}

/** Normaliza +58… / 58… / 10 dígitos → 11 dígitos 0[24]xxxxxxxx para validate_phone. */
export function telefonoVenezuelaDigitos11(valor: string): string {
  let d = String(valor ?? '')
    .trim()
    .replace(/[\s-]/g, '')
    .replace(/\D/g, '')

  if (!d) return ''

  if (d.startsWith('58') && d.length >= 12) {
    d = d.slice(2)
  }

  if (d.length === 10 && /^[24]/.test(d)) {
    d = `0${d}`
  } else if (d.length === 11 && d.startsWith('0')) {
    // ya en formato local
  } else if (d.length > 11 && d.startsWith('0')) {
    d = d.slice(0, 11)
  }

  return d
}

/** Alineado con validate_phone del backend. */
export function validarTelefonoVenezuelaRevisionLocal(
  valor: string
): ValidacionCampoLocal {
  const phoneClean = telefonoVenezuelaDigitos11(valor)

  if (!phoneClean) {
    return { valido: false, error: 'Teléfono no puede estar vacío' }
  }

  if (!/^0[24]\d{9}$/.test(phoneClean)) {
    return {
      valido: false,
      valor_formateado: phoneClean,
      error:
        'Teléfono inválido. Formato: 0XXX-9999999 (11 dígitos, comenzando con 04 o 02)',
    }
  }

  return {
    valido: true,
    valor_formateado: `${phoneClean.slice(0, 4)}-${phoneClean.slice(4)}`,
  }
}

/** Alineado con validate_email del backend. */
export function validarEmailRevisionLocal(valor: string): ValidacionCampoLocal {
  const emailClean = String(valor ?? '')
    .trim()
    .toLowerCase()

  if (!emailClean) {
    return { valido: false, error: 'Email no puede estar vacío' }
  }

  const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/i

  if (!emailPattern.test(emailClean)) {
    return {
      valido: false,
      valor_formateado: emailClean,
      error: 'Email inválido. Formato: usuario@dominio.com',
    }
  }

  return { valido: true, valor_formateado: emailClean }
}

export function mensajeValidacionCampoLocal(
  v: ValidacionCampoLocal | undefined
): string | undefined {
  if (!v || v.valido) return undefined
  const e = v.error
  const m = v.mensaje
  if (typeof e === 'string' && e.trim()) return e.trim()
  if (typeof m === 'string' && m.trim()) return m.trim()
  return undefined
}
