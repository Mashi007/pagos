/**
 * Reemplaza imágenes inline en base64 por la variable {{LOGO_URL}} en HTML de plantillas.
 * Solo reemplaza data URLs largas (logo/fotos); deja iconos SVG pequeños (ej. WhatsApp).
 * Así la plantilla no guarda el base64 enorme y el correo se renderiza bien en Gmail.
 * Usar al pegar/guardar en el editor de plantillas.
 */
const MIN_BASE64_LENGTH_TO_REPLACE = 400

export function replaceBase64ImagesWithLogoUrl(html: string): string {
  if (!html || typeof html !== 'string') return html
  return html.replace(/src="(data:image\/[^"]+)"/gi, (_, dataUrl: string) => {
    if (dataUrl.length >= MIN_BASE64_LENGTH_TO_REPLACE) {
      return 'src="{{LOGO_URL}}"'
    }
    return `src="${dataUrl}"`
  })
}
