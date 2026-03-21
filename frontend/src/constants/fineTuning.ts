/**
 * Constantes para Fine Tuning (conversaciones, feedback negativo, mÃ­nimo requerido)
 */

export const MINIMO_CONVERSACIONES_ENTRENAMIENTO = 10

/** Palabras clave que indican feedback negativo (alineado con backend) */
export const PALABRAS_NEGATIVAS_FEEDBACK = [
  'mal', 'malo', 'incorrecto', 'error', 'equivocado', 'confuso',
  'no entendÃ­', 'no entiendo', 'poco claro', 'poco clara',
  'incompleto', 'incompleta', 'faltante', 'falta', 'deficiente',
  'mejorar', 'deberÃ­a', 'podrÃ­a',
  'serÃ­a mejor', 'no me gusta', 'no me sirve', 'no ayuda',
  'no es Ãºtil', 'muy tÃ©cnico', 'muy tÃ©cnica', 'demasiado complejo',
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
