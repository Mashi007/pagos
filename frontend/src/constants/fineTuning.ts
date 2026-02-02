/**
 * Constantes para Fine Tuning (conversaciones, feedback negativo, mínimo requerido)
 */

export const MINIMO_CONVERSACIONES_ENTRENAMIENTO = 10

/** Palabras clave que indican feedback negativo (alineado con backend) */
export const PALABRAS_NEGATIVAS_FEEDBACK = [
  'mal', 'malo', 'incorrecto', 'error', 'equivocado', 'confuso',
  'no entendí', 'no entiendo', 'poco claro', 'poco clara',
  'incompleto', 'incompleta', 'faltante', 'falta', 'deficiente',
  'mejorar', 'debería', 'podría',
  'sería mejor', 'no me gusta', 'no me sirve', 'no ayuda',
  'no es útil', 'muy técnico', 'muy técnica', 'demasiado complejo',
  'compleja', 'no responde', 'no contesta', 'no es lo que busco',
  'no es lo que necesito',
] as const

/** Detecta si el texto de feedback es negativo (2+ palabras negativas) */
export function detectarFeedbackNegativo(feedback: string | null | undefined): boolean {
  if (!feedback) return false
  const lower = feedback.toLowerCase()
  const count = PALABRAS_NEGATIVAS_FEEDBACK.filter((p) => lower.includes(p)).length
  return count >= 2
}
