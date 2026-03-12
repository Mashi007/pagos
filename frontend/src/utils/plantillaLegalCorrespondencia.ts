/**
 * Plantilla de correspondencia legal para el cuerpo del email.
 * Convierte redacción (cuerpo + firma) en HTML con formato profesional predefinido.
 */

export const SEPARATOR_FIRMA = '<!-- SEPARATOR_FIRMA -->'

const LEGAL_LETTER_STYLES = `
  margin: 0;
  padding: 0;
  font-family: 'Times New Roman', Times, serif;
  font-size: 12pt;
  line-height: 1.5;
  color: #1a1a1a;
  max-width: 21cm;
`.trim()

const LEGAL_LETTER_HEADER = `
  <div style="border-bottom: 2px solid #1e3a5f; padding-bottom: 8px; margin-bottom: 16px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 11pt;">
      <tr>
        <td style="color: #1e3a5f; font-weight: 600;">Rapi-Credit, C.A.</td>
      </tr>
      <tr>
        <td style="color: #4a5568; font-size: 10pt;">Correspondencia oficial</td>
      </tr>
    </table>
  </div>
`.trim()

/**
 * Convierte texto a HTML: si ya contiene etiquetas, se deja; si no, se escapan y se envuelven en <p>.
 */
function textToHtml(text: string): string {
  if (!text || !text.trim()) return ''
  const trimmed = text.trim()
  if (/<[a-z][\s\S]*>/i.test(trimmed)) return trimmed
  return trimmed
    .split(/\n\n+/)
    .map(p => `<p style="margin: 0 0 12px 0;">${p.replace(/\n/g, '<br />')}</p>`)
    .join('')
}

/**
 * Construye el cuerpo completo del email en HTML con formato de correspondencia legal.
 * Incluye encabezado corporativo, cuerpo, separador y firma.
 */
export function buildCuerpoConFormatoLegal(
  encabezado: string,
  cuerpo: string,
  firma: string
): string {
  const encHtml = textToHtml(encabezado)
  const cuerpoHtml = textToHtml(cuerpo)
  const firmaHtml = textToHtml(firma)

  const partes: string[] = []
  if (encHtml) partes.push(encHtml)
  if (cuerpoHtml) partes.push(cuerpoHtml)
  if (firmaHtml) partes.push(SEPARATOR_FIRMA, firmaHtml)

  const contenido = partes.join('\n')

  return `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Correspondencia</title>
</head>
<body style="${LEGAL_LETTER_STYLES}">
  <div style="padding: 24px 32px; max-width: 21cm;">
    ${LEGAL_LETTER_HEADER}
    <div class="cuerpo-legal" style="margin-top: 16px;">
      ${contenido}
    </div>
    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 10pt; color: #718096;">
      Este correo es un recordatorio oficial de Rapi-Credit, C.A.
    </div>
  </div>
</body>
</html>`
}

/**
 * Parsea el cuerpo guardado (HTML) para extraer cuerpo y firma usando el separador.
 * Si no hay separador, devuelve todo el contenido en cuerpo y firma vacía.
 */
export function parseCuerpoGuardado(html: string): { encabezado: string; cuerpo: string; firma: string } {
  if (!html || !html.trim()) return { encabezado: '', cuerpo: '', firma: '' }
  if (!html.includes(SEPARATOR_FIRMA)) {
    const sinWrapper = quitarWrapperHtml(html)
    return { encabezado: '', cuerpo: sinWrapper, firma: '' }
  }
  const [antes, despues] = html.split(SEPARATOR_FIRMA)
  const parteCuerpo = quitarWrapperHtml(antes)
  const parteFirma = quitarWrapperHtml(despues || '')
  return { encabezado: '', cuerpo: parteCuerpo, firma: parteFirma }
}

function quitarWrapperHtml(html: string): string {
  const divMatch = html.match(/<div[^>]*class="cuerpo-legal"[^>]*>([\s\S]*?)<\/div>/i)
  if (divMatch) return divMatch[1].trim()
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i)
  if (bodyMatch) return bodyMatch[1].trim()
  const innerMatch = html.match(/<div[^>]*style="margin-top: 16px"[^>]*>([\s\S]*?)<\/div>/i)
  if (innerMatch) return innerMatch[1].trim()
  return html.trim()
}
