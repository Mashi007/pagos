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

/**
 * Normaliza el valor mientras el usuario escribe un teléfono.
 * - Solo permite dígitos y un + al inicio.
 * - Venezuela: 10 dígitos que empiezan por 4 (ej. 4241234567) o 0+10 dígitos (04241234567) → se antepone +58.
 * - Otros: código país + número (máx. 15 dígitos). Resultado siempre con + al inicio.
 */
export function normalizarTelefonoParaIngreso(raw: string): string {
  if (raw == null) return ''
  let digits = String(raw).replace(/\D/g, '')
  if (digits.length === 0) return ''
  // Venezuela: 0 + 10 dígitos (04241234567) → quitar el 0
  if (digits.startsWith('0') && digits.length === 11) digits = digits.slice(1)
  // Venezuela: 10 dígitos empezando por 4 (móvil) → anteponer 58
  if (digits.length <= 10 && digits.startsWith('4')) digits = '58' + digits
  digits = digits.slice(0, 15)
  return '+' + digits
}

/**
 * Formato legible para mostrar (ej. +584241234567 → +58 424 1234567).
 * Útil para placeholder o resumen; el input puede mostrar el valor normalizado sin espacios.
 */
export function formatearTelefonoParaMostrar(telefono: string): string {
  if (!telefono || typeof telefono !== 'string') return ''
  const digits = telefono.replace(/\D/g, '')
  if (digits.length === 0) return ''
  if (digits.startsWith('58') && digits.length === 12) {
    return `+58 ${digits.slice(2, 5)} ${digits.slice(5)}`
  }
  return (telefono.startsWith('+') ? '' : '+') + digits.replace(/(\d{1,3})(?=\d)/g, '$1 ').trim()
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

// =============================================================================
// Normas de Google para email (SMTP e IMAP)
// =============================================================================
// SMTP (enviar): smtp.gmail.com | Puertos: 587 (STARTTLS) o 465 (SSL) | App Password
// IMAP (recibir): imap.gmail.com | Puertos: 993 (SSL) o 143 (STARTTLS) | App Password
// Ref: https://support.google.com/mail/answer/7126229
// =============================================================================

// Validación de configuración de Gmail (SMTP - envío de correo)
export function validarConfiguracionGmail(config: {
  smtp_host?: string
  smtp_port?: string
  smtp_user?: string
  smtp_password?: string
  smtp_use_tls?: string
  from_email?: string
}): { valido: boolean; errores: string[] } {
  const errores: string[] = []
  const host = config.smtp_host?.toLowerCase().trim() ?? ''
  const esGmail = host === 'smtp.gmail.com' || host.endsWith('.gmail.com')

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

  // Validaciones específicas para Gmail/Google (normas SMTP oficiales)
  if (esGmail) {
    if (!config.smtp_password?.trim()) {
      errores.push('Contraseña de Aplicación es requerida para Gmail/Google Workspace')
    }
    const puerto = parseInt(config.smtp_port || '0')
    if (puerto !== 587 && puerto !== 465) {
      errores.push('Gmail/Google Workspace requiere puerto 587 (STARTTLS) o 465 (SSL). El puerto 587 es recomendado.')
    }
    if (puerto === 587 && config.smtp_use_tls !== 'true') {
      errores.push('Para puerto 587, TLS debe estar habilitado (requerido por Gmail/Google Workspace)')
    }
    // Puerto 465 usa SSL implícito; no requiere checkbox TLS adicional
  }

  return {
    valido: errores.length === 0,
    errores
  }
}

// Validación de configuración IMAP para Google (recibir correo)
// Normas: imap.gmail.com, puerto 993 (SSL) o 143 (STARTTLS), App Password
export function validarConfiguracionImapGmail(config: {
  imap_host?: string
  imap_port?: string
  imap_user?: string
  imap_password?: string
  imap_use_ssl?: string
}): { valido: boolean; errores: string[] } {
  const errores: string[] = []
  const host = config.imap_host?.toLowerCase().trim() ?? ''
  const esGmailImap = host === 'imap.gmail.com' || host.endsWith('.gmail.com')

  if (!config.imap_host?.trim()) {
    errores.push('Servidor IMAP es requerido')
  }
  if (!config.imap_port?.trim()) {
    errores.push('Puerto IMAP es requerido')
  } else {
    const puerto = parseInt(config.imap_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      errores.push('Puerto IMAP debe ser un número entre 1 y 65535')
    }
  }
  if (!config.imap_user?.trim()) {
    errores.push('Email de usuario IMAP es requerido')
  } else if (!validarEmail(config.imap_user)) {
    errores.push('Email de usuario IMAP no es válido')
  }

  if (esGmailImap) {
    if (!config.imap_password?.trim()) {
      errores.push('Contraseña de Aplicación es requerida para Gmail/Google Workspace (IMAP)')
    }
    const puerto = parseInt(config.imap_port || '0')
    if (puerto !== 993 && puerto !== 143) {
      errores.push('Gmail IMAP requiere puerto 993 (SSL) o 143 (STARTTLS). El puerto 993 es recomendado.')
    }
    if (puerto === 143 && config.imap_use_ssl !== 'true') {
      errores.push('Para puerto 143, TLS/STARTTLS debe estar habilitado (requerido por Gmail/Google Workspace)')
    }
  }

  return {
    valido: errores.length === 0,
    errores
  }
}

// =============================================================================
// Normas de Meta WhatsApp Business API (Cloud API)
// =============================================================================
// - Base URL: https://graph.facebook.com/v{version}/ (v18.0, v19.0, v20.0, v21.0, v22.0)
// - Webhook: GET (hub.mode, hub.verify_token, hub.challenge) | POST (X-Hub-Signature-256, payload object "whatsapp_business_account")
// - Envío: POST {api_url}/{phone_number_id}/messages | Auth: Bearer {access_token}
// - Phone Number ID: solo dígitos (ID numérico de Meta)
// Ref: https://developers.facebook.com/docs/whatsapp/cloud-api
// =============================================================================

/** Verifica que la URL sea la base de Meta Graph API (WhatsApp Cloud API). Ej: https://graph.facebook.com/v18.0 */
export function esGraphApiUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false
  const u = url.trim().toLowerCase()
  return u.startsWith('https://') && u.includes('graph.facebook.com') && /\/v\d+/.test(u)
}

// Validación de configuración de WhatsApp (Meta Cloud API)
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
  } else if (!esGraphApiUrl(config.api_url)) {
    errores.push('API URL debe ser la base de Meta Graph API (ej: https://graph.facebook.com/v18.0)')
  }

  if (!config.access_token?.trim()) {
    errores.push('Access Token es requerido (token de Meta Developers)')
  }

  const phoneNumberIdValidacion = validarPhoneNumberID(config.phone_number_id || '')
  if (!phoneNumberIdValidacion.valido) {
    errores.push(phoneNumberIdValidacion.error || 'Phone Number ID es requerido (solo números, desde Meta Business)')
  }

  return {
    valido: errores.length === 0,
    errores
  }
}
