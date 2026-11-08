/**
 * Cola Excel de Gestión: carga N correos y los reparte en bloques de `maxCola`
 * (p. ej. 1000 → 100 bloques de 10). El 1.º bloque se escanea ya; el resto queda
 * en cola para arrancar al cerrar cada bloque.
 */
export type PlanColaExcel = {
  totalEmails: number
  bloquesTotal: number
  primerBloque: string[]
  restoCola: string[]
}

export function planificarColaExcel(
  emails: string[],
  maxCola: number
): PlanColaExcel {
  const max = Math.max(1, Math.floor(maxCola) || 1)
  const list = Array.isArray(emails) ? emails.filter(Boolean) : []
  const primerBloque = list.slice(0, max)
  const restoCola = list.slice(max)
  const bloquesTotal = Math.max(1, Math.ceil(list.length / max) || 1)
  return {
    totalEmails: list.length,
    bloquesTotal: list.length === 0 ? 0 : bloquesTotal,
    primerBloque,
    restoCola,
  }
}

/** Saca el siguiente bloque de la cola mutable (misma semántica que Gestión). */
export function tomarSiguienteBloque(
  cola: string[],
  maxCola: number
): { chunk: string[]; resto: string[] } {
  const max = Math.max(1, Math.floor(maxCola) || 1)
  return {
    chunk: cola.slice(0, max),
    resto: cola.slice(max),
  }
}
