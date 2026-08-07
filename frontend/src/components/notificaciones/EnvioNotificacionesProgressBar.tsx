export type EnvioProgressState = {
  procesados: number
  total: number
  enviados: number
  fallidos: number
  sin_email: number
  /** enviando | pausado_limite_gmail | finalizado */
  estado?: string
}

/** Barra de avance del lote de notificaciones (mismo UI en listado y Configuracion). */
export function EnvioNotificacionesProgressBar({
  progress,
}: {
  progress: EnvioProgressState | null
}) {
  const total = progress && progress.total > 0 ? progress.total : 0
  const procesados = progress
    ? Math.min(progress.procesados, total || progress.procesados)
    : 0
  const pct =
    progress && total > 0
      ? Math.min(100, Math.round((progress.procesados / total) * 100))
      : 15
  const pausado =
    String(progress?.estado || '')
      .trim()
      .toLowerCase() === 'pausado_limite_gmail'
  const restantes =
    total > 0 ? Math.max(0, total - (progress?.procesados || 0)) : 0

  const border = pausado
    ? 'border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-50'
    : 'border-sky-200 bg-sky-50 text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-50'
  const track = pausado
    ? 'bg-amber-200/70 dark:bg-amber-900'
    : 'bg-sky-200/70 dark:bg-sky-900'
  const fill = pausado ? 'bg-amber-600 dark:bg-amber-400' : 'bg-sky-600 dark:bg-sky-400'

  return (
    <div className={`w-full min-w-[220px] max-w-md rounded-md border px-3 py-2 ${border}`}>
      <div className="mb-1 flex items-center justify-between gap-2 text-xs font-medium">
        <span>
          {pausado
            ? progress && total > 0
              ? `Pausado ${progress.procesados} de ${total} (cupo Gmail)`
              : 'Pausado por cupo diario Gmail'
            : progress && total > 0
              ? `Enviando ${progress.procesados} de ${total}`
              : 'Enviando notificaciones…'}
        </span>
        {progress ? (
          <span className="text-[11px] tabular-nums opacity-80">
            OK {progress.enviados}
            {progress.fallidos > 0 ? ` · fallos ${progress.fallidos}` : ''}
            {progress.sin_email > 0
              ? ` · sin correo ${progress.sin_email}`
              : ''}
          </span>
        ) : null}
      </div>
      <div
        className={`h-2 w-full overflow-hidden rounded-full ${track}`}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total > 0 ? total : 100}
        aria-valuenow={procesados}
        aria-label="Progreso de envio de notificaciones"
      >
        <div
          className={`h-full transition-all duration-300 ${fill}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] leading-snug opacity-80">
        {pausado
          ? `Quedan ~${restantes}. El servidor reanuda automaticamente al dia siguiente (ya enviados se omiten). No hace falta reconsultar a cada rato.`
          : 'El servidor sigue hasta terminar el lote aunque cierre o cambie de menu. Barra en vivo cada ~3 s.'}
      </p>
    </div>
  )
}
