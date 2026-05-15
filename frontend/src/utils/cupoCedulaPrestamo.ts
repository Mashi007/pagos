/** Alineado con backend `app.utils.cedula_almacenamiento` (cupo prestamos APROBADO). */

export type PrefijoCupoCedula = 'E' | 'V' | 'J'

export function normalizarCedulaClaveCupo(value: string): string {
  return (value || '').trim().toUpperCase().replace(/-/g, '').replace(/\s/g, '')
}

export function prefijoPoliticaCupoAprobados(
  clave: string
): PrefijoCupoCedula | null {
  if (!clave) return null
  const c0 = clave[0]
  if (c0 === 'E' || c0 === 'V' || c0 === 'J') return c0
  return null
}

export function maxAprobadosPermitidosPorPrefijo(
  prefijo: PrefijoCupoCedula | null
): number | null {
  if (prefijo === 'E' || prefijo === 'V') return 1
  if (prefijo === 'J') return 5
  return null
}

export function cedulaPermiteVariosPrestamosAprobados(clave: string): boolean {
  return prefijoPoliticaCupoAprobados(normalizarCedulaClaveCupo(clave)) === 'J'
}

export function descripcionPoliticaCupo(prefijo: PrefijoCupoCedula | null): string {
  if (prefijo === 'J') {
    return 'Cedula juridica (empieza por J): hasta 5 prestamos APROBADO con la misma cedula.'
  }
  if (prefijo === 'E' || prefijo === 'V') {
    return 'Cedula natural (V o E): maximo 1 prestamo APROBADO por cedula.'
  }
  return 'Solo cedulas que empiezan por V, E o J tienen cupo de prestamos APROBADO.'
}
