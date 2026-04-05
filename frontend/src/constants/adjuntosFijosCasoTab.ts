/**
 * Pestaña "Documentos PDF anexos": claves tipo_tab del backend (get_adjuntos_fijos_por_caso).
 * dias_1_retraso = envíos «día siguiente al vencimiento» (PAGO_1_DIA_ATRASADO en tabs).
 */
export const ETIQUETA_CASO_TAB_ADJUNTO: Record<string, string> = {
  dias_1_retraso: 'Día siguiente al vencimiento',
  d_2_antes_vencimiento: '2 días antes (pendiente, vence en 2 días)',
  dias_3_retraso: '3 días retraso',
  dias_5_retraso: '5 días retraso',
  dias_30_retraso: '30 días retraso',
  prejudicial: 'Prejudicial',
  masivos: 'Comunicaciones masivas',
}

/** Casos disponibles al subir un PDF (todos los tipo_caso del backend para anexos). */
export const TIPOS_CASO_ADJUNTO_SUBIDA: { value: string; label: string }[] = [
  {
    value: 'dias_1_retraso',
    label: ETIQUETA_CASO_TAB_ADJUNTO.dias_1_retraso,
  },
  {
    value: 'd_2_antes_vencimiento',
    label: ETIQUETA_CASO_TAB_ADJUNTO.d_2_antes_vencimiento,
  },
  {
    value: 'dias_3_retraso',
    label: ETIQUETA_CASO_TAB_ADJUNTO.dias_3_retraso,
  },
  {
    value: 'dias_5_retraso',
    label: ETIQUETA_CASO_TAB_ADJUNTO.dias_5_retraso,
  },
  {
    value: 'dias_30_retraso',
    label: ETIQUETA_CASO_TAB_ADJUNTO.dias_30_retraso,
  },
  {
    value: 'prejudicial',
    label: ETIQUETA_CASO_TAB_ADJUNTO.prejudicial,
  },
  {
    value: 'masivos',
    label: ETIQUETA_CASO_TAB_ADJUNTO.masivos,
  },
]

export type AdjuntoFijoCasoItem = {
  id: string
  nombre_archivo: string
  ruta: string
}

/** Orden estable para mostrar documentos por caso (incluye claves solo legacy). */
export function listarCasosConAdjuntosGuardados(
  porCaso: Record<string, AdjuntoFijoCasoItem[] | undefined>
): { value: string; label: string; items: AdjuntoFijoCasoItem[] }[] {
  const order = TIPOS_CASO_ADJUNTO_SUBIDA.map(t => t.value)
  const keysWith = Object.entries(porCaso)
    .filter(([, items]) => (items?.length ?? 0) > 0)
    .map(([k]) => k)
  const sorted = [
    ...order.filter(k => keysWith.includes(k)),
    ...keysWith.filter(k => !order.includes(k)),
  ]
  return sorted.map(value => ({
    value,
    label: ETIQUETA_CASO_TAB_ADJUNTO[value] || value,
    items: porCaso[value] ?? [],
  }))
}
