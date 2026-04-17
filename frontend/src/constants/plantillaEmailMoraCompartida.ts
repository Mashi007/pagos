/**
 * HTML equivalente al texto de respaldo de mora en backend
 * (`notificaciones_tabs`: `asunto_ret` + `cuerpo_ret` para PAGO_1_DIA_ATRASADO
 * y PAGO_10_DIAS_ATRASADO). Solo esas frases y variables; sin lineas adicionales.
 *
 * Variables sustituidas al enviar: {{nombre}}, {{cedula}}, {{fecha_vencimiento}},
 * {{numero_cuota}}, {{monto}} (ver `_sustituir_variables` en notificaciones.py).
 */

export const PLANTILLA_EMAIL_MORA_ASUNTO =
  'Cuenta con cuota atrasada - Rapicredit'

/** Sin bloque extra: el armado en UI usa encabezado vacio para este caso. */
export const PLANTILLA_EMAIL_MORA_ENCABEZADO_FIJO = ''

/** Parrafos variables + fijos del cuerpo (sin cierre de saludo; va en firma). */
export const PLANTILLA_EMAIL_MORA_CUERPO_VARIABLES = `<p>Estimado/a <strong>{{nombre}}</strong> (cédula {{cedula}}),</p>
<p>Le recordamos que tiene una cuota en mora.</p>
<p><strong>Fecha de vencimiento:</strong> {{fecha_vencimiento}}<br/>
<strong>Número de cuota:</strong> {{numero_cuota}}<br/>
<strong>Monto:</strong> {{monto}}</p>
<p>Por favor regularice su pago lo antes posible.</p>`

export const PLANTILLA_EMAIL_MORA_FIRMA_FIJO = `<p>Saludos,<br/>Rapicredit</p>`

/** Mismo contenido que encabezado + cuerpo + firma en un solo HTML (Editor HTML). */
export function plantillaEmailMoraHtmlMonobloque(): string {
  const parts = [
    PLANTILLA_EMAIL_MORA_ENCABEZADO_FIJO.trim(),
    PLANTILLA_EMAIL_MORA_CUERPO_VARIABLES.trim(),
    PLANTILLA_EMAIL_MORA_FIRMA_FIJO.trim(),
  ].filter(Boolean)
  return parts.join('\n\n')
}
