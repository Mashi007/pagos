/**
 * Utilidades de validación comunes para el frontend
 * Centraliza validaciones para evitar código duplicado
 */

// Regex patterns
export const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const telefonoRegex = /^\+?[1-9]\d{9,14}$/
export const urlRegex = /^https?:\/\/.+\..+/

// Validación de email
export function validarEmail(email: string): boolean {
  if (!email || typeof email !== 'string') return false
  return emailRegex.test(email.trim())
}

// Validación de teléfono
export function validarTelefono(telefono: string): boolean {
  if (!telefono || typeof telefono !== 'string') return false
  const telefonoLimpio = telefono.replace(/[\s\-\(\)]/g, '')
  return telefonoRegex.test(telefonoLimpio)
}

// Validación de URL
export function validarURL(url: string): boolean {
  if (!url || typeof url !== 'string') return false
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

// Validación de puerto SMTP
export function validarPuertoSMTP(puerto: string | number): boolean {
  const puertoNum = typeof puerto === 'string' ? parseInt(puerto, 10) : puerto
  return !isNaN(puertoNum) && puertoNum >= 1 && puertoNum <= 65535
}

// Validación de nombre de empresa
export function validarNombreEmpresa(nombre: string): { valido: boolean; error?: string } {
  if (!nombre || typeof nombre !== 'string') {
    return { valido: false, error: 'El nombre de la empresa es requerido' }
  }
  const nombreLimpio = nombre.trim()
  if (nombreLimpio.length < 3) {
    return { valido: false, error: 'El nombre debe tener al menos 3 caracteres' }
  }
  if (nombreLimpio.length > 100) {
    return { valido: false, error: 'El nombre no puede exceder 100 caracteres' }
  }
  return { valido: true }
}

// Validación de moneda
export function validarMoneda(moneda: string): boolean {
  const monedasValidas = ['VES', 'USD', 'EUR']
  return monedasValidas.includes(moneda)
}

// Validación de zona horaria
export function validarZonaHoraria(zona: string): boolean {
  const zonasValidas = [
    'America/Caracas',
    'America/New_York',
    'America/Los_Angeles',
    'America/Mexico_City',
    'America/Bogota',
    'America/Lima',
    'America/Santiago',
    'America/Buenos_Aires',
    'UTC'
  ]
  return zonasValidas.includes(zona)
}

// Validación de idioma
export function validarIdioma(idioma: string): boolean {
  const idiomasValidos = ['ES', 'EN']
  return idiomasValidos.includes(idioma)
}

// Validación de Phone Number ID (solo números)
export function validarPhoneNumberID(phoneNumberId: string): { valido: boolean; error?: string } {
  if (!phoneNumberId || typeof phoneNumberId !== 'string') {
    return { valido: false, error: 'Phone Number ID es requerido' }
  }
  const limpio = phoneNumberId.trim()
  if (!/^\d+$/.test(limpio)) {
    return { valido: false, error: 'Phone Number ID debe contener solo números (sin espacios ni caracteres especiales)' }
  }
  return { valido: true }
}

// Validación de rango numérico
export function validarRangoNumerico(
  valor: string | number,
  min: number,
  max: number,
  nombreCampo: string = 'Valor'
): { valido: boolean; error?: string } {
  const valorNum = typeof valor === 'string' ? parseFloat(valor) : valor
  if (isNaN(valorNum)) {
    return { valido: false, error: `${nombreCampo} debe ser un número válido` }
  }
  if (valorNum < min || valorNum > max) {
    return { valido: false, error: `${nombreCampo} debe estar entre ${min} y ${max}` }
  }
  return { valido: true }
}

// Sanitizar string (remover espacios, limitar longitud)
export function sanitizarString(texto: string, maxLength: number = 100): string {
  if (!texto || typeof texto !== 'string') return ''
  return texto.trim().slice(0, maxLength)
}

// Validación de configuración de Gmail
export function validarConfiguracionGmail(config: {
  smtp_host?: string
  smtp_port?: string
  smtp_user?: string
  smtp_password?: string
  smtp_use_tls?: string
}): { valido: boolean; errores: string[] } {
  const errores: string[] = []
  const esGmail = config.smtp_host?.toLowerCase().includes('gmail.com') || false

  // Validaciones básicas
  if (!config.smtp_host?.trim()) {
    errores.push('Servidor SMTP es requerido')
  }
  if (!config.smtp_port?.trim()) {
    errores.push('Puerto SMTP es requerido')
  } else {
    const puerto = parseInt(config.smtp_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      errores.push('Puerto SMTP debe ser un número entre 1 y 65535')
    }
  }
  if (!config.smtp_user?.trim()) {
    errores.push('Email de usuario es requerido')
  } else if (!validarEmail(config.smtp_user)) {
    errores.push('Email de usuario no es válido')
  }
  if (!config.from_email?.trim()) {
    errores.push('Email del remitente es requerido')
  } else if (!validarEmail(config.from_email)) {
    errores.push('Email del remitente no es válido')
  }

  // Validaciones específicas para Gmail
  if (esGmail) {
    if (!config.smtp_password?.trim()) {
      errores.push('Contraseña de Aplicación es requerida para Gmail/Google Workspace')
    }
    const puerto = parseInt(config.smtp_port || '0')
    if (puerto !== 587 && puerto !== 465) {
      errores.push('Gmail/Google Workspace requiere puerto 587 (TLS) o 465 (SSL). El puerto 587 es recomendado.')
    }
    if (puerto === 587 && config.smtp_use_tls !== 'true') {
      errores.push('Para puerto 587, TLS debe estar habilitado (requerido por Gmail/Google Workspace)')
    }
  }

  return {
    valido: errores.length === 0,
    errores
  }
}

// Validación de configuración de WhatsApp
export function validarConfiguracionWhatsApp(config: {
  api_url?: string
  access_token?: string
  phone_number_id?: string
}): { valido: boolean; errores: string[] } {
  const errores: string[] = []

  if (!config.api_url?.trim()) {
    errores.push('API URL es requerida')
  } else if (!validarURL(config.api_url)) {
    errores.push('API URL no es válida')
  }

  if (!config.access_token?.trim()) {
    errores.push('Access Token es requerido')
  }

  const phoneNumberIdValidacion = validarPhoneNumberID(config.phone_number_id || '')
  if (!phoneNumberIdValidacion.valido) {
    errores.push(phoneNumberIdValidacion.error || 'Phone Number ID es requerido')
  }

  return {
    valido: errores.length === 0,
    errores
  }
}
