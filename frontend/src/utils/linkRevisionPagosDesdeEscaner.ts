/**
 * Query string para abrir Pagos en la pestaña «Revisión» (PagosList),
 * opcionalmente filtrando por Nº documento / operación.
 */
export function searchParamsRevisionPagosDesdeNumeroDocumento(
  numeroDocumento: string
): string {
  const sp = new URLSearchParams()
  sp.set('pestana', 'revision')
  const t = (numeroDocumento || '').trim()
  if (t) sp.set('numero_documento', t)
  return sp.toString()
}
