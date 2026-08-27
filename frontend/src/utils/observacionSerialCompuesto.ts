/** Marca «Serial compuesto» (y alias legacy): no cuenta como caso a revisión manual. */
export const MARCA_OBS_SERIAL_COMPUESTO = 'Serial compuesto'

const LEGACY = ['serial mixto'] as const

export function textoTieneMarcaSerialCompuesto(
  texto: string | null | undefined
): boolean {
  const d = (texto ?? '').trim().toLowerCase()
  if (!d) return false
  if (d.includes(MARCA_OBS_SERIAL_COMPUESTO.toLowerCase())) return true
  return LEGACY.some(leg => d.includes(leg))
}

/** True si algún texto incluye Serial compuesto — excluir de cola/casos revisión. */
export function observacionesSuprimenCasoRevision(
  ...textos: Array<string | null | undefined>
): boolean {
  return textos.some(t => textoTieneMarcaSerialCompuesto(t))
}

export function aplicarSupresionRevisionSerialCompuesto(
  requiereRevision: boolean,
  ...textos: Array<string | null | undefined>
): boolean {
  if (observacionesSuprimenCasoRevision(...textos)) return false
  return requiereRevision
}
