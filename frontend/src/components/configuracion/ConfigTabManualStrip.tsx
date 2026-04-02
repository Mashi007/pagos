import type { ReactNode } from 'react'

/**
 * Franja consistente: acciones solo disparadas por el usuario (sin temporizadores ni programador en UI).
 */
export function ConfigTabManualStrip({
  children,
  note,
}: {
  children: ReactNode
  note?: string
}) {
  return (
    <div
      className="mb-4 flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 sm:flex-row sm:items-center sm:justify-between"
      role="region"
      aria-label="Acciones manuales"
    >
      <p className="text-xs text-slate-600">
        {note ??
          'Acciones manuales: use los botones; no hay ejecucion automatica desde esta pestaña.'}
      </p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  )
}
