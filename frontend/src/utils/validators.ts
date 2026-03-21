/**


 * Utilidades de validaci├â┬â├é┬│n comunes para el frontend


 * Centraliza validaciones para evitar c├â┬â├é┬│digo duplicado


 */





// Regex patterns


export const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/


export const telefonoRegex = /^\+?[1-9]\d{9,14}$/


export const urlRegex = /^https?:\/\/.+\..+/





// Validaci├â┬â├é┬│n de email


export function validarEmail(email: string): boolean {


  if (!email || typeof email !== 'string') return false


  return emailRegex.test(email.trim())


}





// Validaci├â┬â├é┬│n de tel├â┬â├é┬⌐fono


export function validarTelefono(telefono: string): boolean {


  if (!telefono || typeof telefono !== 'string') return false


  const telefonoLimpio = telefono.replace(/[\s\-\(\)]/g, '')


  return telefonoRegex.test(telefonoLimpio)


}





/**


 * Normaliza el valor mientras el usuario escribe un tel├â┬â├é┬⌐fono.


 * - Solo permite d├â┬â├é┬¡gitos y un + al inicio.


 * - Venezuela: 10 d├â┬â├é┬¡gitos que empiezan por 4 (ej. 4241234567) o 0+10 d├â┬â├é┬¡gitos (04241234567) ├â┬ó├é┬å├é┬Æ se antepone +58.


 * - Otros: c├â┬â├é┬│digo pa├â┬â├é┬¡s + n├â┬â├é┬║mero (m├â┬â├é┬íx. 15 d├â┬â├é┬¡gitos). Resultado siempre con + al inicio.


 */


export function normalizarTelefonoParaIngreso(raw: string): string {


  if (raw == null) return ''


  let digits = String(raw).replace(/\D/g, '')


  if (digits.length === 0) return ''


  // Venezuela: 0 + 10 d├â┬â├é┬¡gitos (04241234567) ├â┬ó├é┬å├é┬Æ quitar el 0


  if (digits.startsWith('0') && digits.length === 11) digits = digits.slice(1)


  // Venezuela: 10 d├â┬â├é┬¡gitos empezando por 4 (m├â┬â├é┬│vil) ├â┬ó├é┬å├é┬Æ anteponer 58


  if (digits.length <= 10 && digits.startsWith('4')) digits = '58' + digits


  digits = digits.slice(0, 15)


  return '+' + digits


}





/**


 * Formato legible para mostrar (ej. +584241234567 ├â┬ó├é┬å├é┬Æ +58 424 1234567).


 * ├â┬â├é┬Ütil para placeholder o resumen; el input puede mostrar el valor normalizado sin espacios.


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





// Validaci├â┬â├é┬│n de URL


export function validarURL(url: string): boolean {


  if (!url || typeof url !== 'string') return false


  try {


    new URL(url)


    return true


  } catch {


    return false


  }


}





// Validaci├â┬â├é┬│n de puerto SMTP


export function validarPuertoSMTP(puerto: string | number): boolean {


  const puertoNum = typeof puerto === 'string' ? parseInt(puerto, 10) : puerto


  return !isNaN(puertoNum) && puertoNum >= 1 && puertoNum <= 65535


}





// Validaci├â┬â├é┬│n de nombre de empresa


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





// Validaci├â┬â├é┬│n de moneda


export function validarMoneda(moneda: string): boolean {


  const monedasValidas = ['VES', 'USD', 'EUR']


  return monedasValidas.includes(moneda)


}





// Validaci├â┬â├é┬│n de zona horaria


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





// Validaci├â┬â├é┬│n de idioma


export function validarIdioma(idioma: string): boolean {


  const idiomasValidos = ['ES', 'EN']


  return idiomasValidos.includes(idioma)


}





// C├â┬â├é┬│digos de pa├â┬â├é┬¡s comunes (sin +). Si el "Phone Number ID" empieza por estos y tiene 10-14 d├â┬â├é┬¡gitos, es un n├â┬â├é┬║mero de tel├â┬â├é┬⌐fono, no el ID de Meta.


const PREFIJOS_NUMERO_TELEFONO = ['58', '57', '593', '52', '54', '51', '56', '598', '595', '55', '59']





/** True si el valor parece un n├â┬â├é┬║mero de tel├â┬â├é┬⌐fono y NO el Phone Number ID de Meta (ej. 1038026026054793). */


export function pareceNumeroTelefonoParaMeta(phoneNumberId: string): boolean {


  if (!phoneNumberId || typeof phoneNumberId !== 'string') return false


  const digits = phoneNumberId.replace(/\D/g, '')


  if (digits.length < 10 || digits.length > 14) return false


  // N├â┬â├é┬║mero con c├â┬â├é┬│digo de pa├â┬â├é┬¡s (58..., 57..., etc.)


  if (PREFIJOS_NUMERO_TELEFONO.some(prefix => digits === prefix || digits.startsWith(prefix))) return true


  // N├â┬â├é┬║mero local sin c├â┬â├é┬│digo: 10 d├â┬â├é┬¡gitos que empiezan por 4 (Venezuela m├â┬â├é┬│vil 424..., 414...) o 04 (0424...)


  if (digits.length === 10 && digits.startsWith('4')) return true


  if (digits.length === 11 && digits.startsWith('04')) return true


  return false


}





// Validaci├â┬â├é┬│n de Phone Number ID (solo n├â┬â├é┬║meros; avisar si parece n├â┬â├é┬║mero de tel├â┬â├é┬⌐fono)


export function validarPhoneNumberID(phoneNumberId: string): { valido: boolean; error?: string } {


  if (!phoneNumberId || typeof phoneNumberId !== 'string') {


    return { valido: false, error: 'Phone Number ID es requerido' }


  }


  const limpio = phoneNumberId.trim()


  if (!/^\d+$/.test(limpio)) {


    return { valido: false, error: 'Phone Number ID debe contener solo n├â┬â├é┬║meros (sin espacios ni caracteres especiales)' }


  }


  if (pareceNumeroTelefonoParaMeta(limpio)) {


    return {


      valido: false,


      error: 'Parece un n├â┬â├é┬║mero de tel├â┬â├é┬⌐fono (+58, +57, etc.). Debes usar el ID num├â┬â├é┬⌐rico de Meta (Business Suite ├â┬ó├é┬å├é┬Æ WhatsApp ├â┬ó├é┬å├é┬Æ tu n├â┬â├é┬║mero ├â┬ó├é┬å├é┬Æ ID), no el n├â┬â├é┬║mero con c├â┬â├é┬│digo de pa├â┬â├é┬¡s.'


    }


  }


  return { valido: true }


}





// Validaci├â┬â├é┬│n de rango num├â┬â├é┬⌐rico


export function validarRangoNumerico(


  valor: string | number,


  min: number,


  max: number,


  nombreCampo: string = 'Valor'


): { valido: boolean; error?: string } {


  const valorNum = typeof valor === 'string' ? parseFloat(valor) : valor


  if (isNaN(valorNum)) {


    return { valido: false, error: `${nombreCampo} debe ser un n├â┬â├é┬║mero v├â┬â├é┬ílido` }


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





// Validaci├â┬â├é┬│n de configuraci├â┬â├é┬│n de Gmail (SMTP - env├â┬â├é┬¡o de correo)


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





  // Validaciones b├â┬â├é┬ísicas


  if (!config.smtp_host?.trim()) {


    errores.push('Servidor SMTP es requerido')


  }


  if (!config.smtp_port?.trim()) {


    errores.push('Puerto SMTP es requerido')


  } else {


    const puerto = parseInt(config.smtp_port)


    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {


      errores.push('Puerto SMTP debe ser un n├â┬â├é┬║mero entre 1 y 65535')


    }


  }


  if (!config.smtp_user?.trim()) {


    errores.push('Email de usuario es requerido')


  } else if (!validarEmail(config.smtp_user)) {


    errores.push('Email de usuario no es v├â┬â├é┬ílido')


  }


  if (!config.from_email?.trim()) {


    errores.push('Email del remitente es requerido')


  } else if (!validarEmail(config.from_email)) {


    errores.push('Email del remitente no es v├â┬â├é┬ílido')


  }





  // Validaciones espec├â┬â├é┬¡ficas para Gmail/Google (normas SMTP oficiales)


  if (esGmail) {


    if (!config.smtp_password?.trim()) {


      errores.push('Contrase├â┬â├é┬▒a es requerida (normal o de aplicaci├â┬â├é┬│n; en cuentas corporativas suele bastar la contrase├â┬â├é┬▒a normal)')


    }


    const puerto = parseInt(config.smtp_port || '0')


    if (puerto !== 587 && puerto !== 465) {


      errores.push('Gmail/Google Workspace requiere puerto 587 (STARTTLS) o 465 (SSL). El puerto 587 es recomendado.')


    }


    if (puerto === 587 && config.smtp_use_tls !== 'true') {


      errores.push('Para puerto 587, TLS debe estar habilitado (requerido por Gmail/Google Workspace)')


    }


    // Puerto 465 usa SSL impl├â┬â├é┬¡cito; no requiere checkbox TLS adicional


  }





  return {


    valido: errores.length === 0,


    errores


  }


}





// Validaci├â┬â├é┬│n de configuraci├â┬â├é┬│n IMAP para Google (recibir correo)


// Normas: imap.gmail.com, puerto 993 (SSL) o 143 (STARTTLS), App Password


export function validarConfiguracionImapGmail(config: {


  imap_host?: string


  imap_port?: string


  imap_user?: string


  imap_password?: string


  imap_use_ssl?: string


}): { valido: boolean; errores: string[] } {


  const errores: string[] = []


  const host = config.imap_host?.toLowerCase().trim() ? ''


  const esGmailImap = host === 'imap.gmail.com' || host.endsWith('.gmail.com')





  if (!config.imap_host?.trim()) {


    errores.push('Servidor IMAP es requerido')


  }


  if (!config.imap_port?.trim()) {


    errores.push('Puerto IMAP es requerido')


  } else {


    const puerto = parseInt(config.imap_port)


    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {


      errores.push('Puerto IMAP debe ser un n├â┬â├é┬║mero entre 1 y 65535')


    }


  }


  if (!config.imap_user?.trim()) {


    errores.push('Email de usuario IMAP es requerido')


  } else if (!validarEmail(config.imap_user)) {


    errores.push('Email de usuario IMAP no es v├â┬â├é┬ílido')


  }





  if (esGmailImap) {


    if (!config.imap_password?.trim()) {


      errores.push('Contrase├â┬â├é┬▒a es requerida para IMAP (normal o de aplicaci├â┬â├é┬│n; en cuentas corporativas usa la contrase├â┬â├é┬▒a normal)')


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


// - Env├â┬â├é┬¡o: POST {api_url}/{phone_number_id}/messages | Auth: Bearer {access_token}


// - Phone Number ID: solo d├â┬â├é┬¡gitos (ID num├â┬â├é┬⌐rico de Meta)


// Ref: https://developers.facebook.com/docs/whatsapp/cloud-api


// =============================================================================





/** Verifica que la URL sea la base de Meta Graph API (WhatsApp Cloud API). Ej: https://graph.facebook.com/v18.0 */


export function esGraphApiUrl(url: string): boolean {


  if (!url || typeof url !== 'string') return false


  const u = url.trim().toLowerCase()


  return u.startsWith('https://') && u.includes('graph.facebook.com') && /\/v\d+/.test(u)


}





// Validaci├â┬â├é┬│n de configuraci├â┬â├é┬│n de WhatsApp (Meta Cloud API)


export function validarConfiguracionWhatsApp(config: {


  api_url?: string


  access_token?: string


  phone_number_id?: string


}): { valido: boolean; errores: string[] } {


  const errores: string[] = []





  if (!config.api_url?.trim()) {


    errores.push('API URL es requerida')


  } else if (!validarURL(config.api_url)) {


    errores.push('API URL no es v├â┬â├é┬ílida')


  } else if (!esGraphApiUrl(config.api_url)) {


    errores.push('API URL debe ser la base de Meta Graph API (ej: https://graph.facebook.com/v18.0)')


  }





  if (!config.access_token?.trim()) {


    errores.push('Access Token es requerido (token de Meta Developers)')


  }





  const phoneNumberIdValidacion = validarPhoneNumberID(config.phone_number_id || '')


  if (!phoneNumberIdValidacion.valido) {


    errores.push(phoneNumberIdValidacion.error || 'Phone Number ID es requerido (solo n├â┬â├é┬║meros, desde Meta Business)')


  }





  return {


    valido: errores.length === 0,


    errores


  }


}


