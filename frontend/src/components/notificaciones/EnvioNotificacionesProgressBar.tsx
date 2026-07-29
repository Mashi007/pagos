export type EnvioProgressState = {
  procesados: number
  total: number
  enviados: number
  fallidos: number
  sin_email: number
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

  return (
    <div className="w-full min-w-[220px] max-w-md rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-50">
      <div className="mb-1 flex items-center justify-between gap-2 text-xs font-medium">
        <span>
          {progress && total > 0
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
        className="h-2 w-full overflow-hidden rounded-full bg-sky-200/70 dark:bg-sky-900"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total > 0 ? total : 100}
        aria-valuenow={procesados}
        aria-label="Progreso de envio de notificaciones"
      >
        <div
          className="h-full bg-sky-600 transition-all duration-300 dark:bg-sky-400"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] leading-snug opacity-80">
        El servidor sigue hasta terminar el lote aunque cierre o cambie de menu.
      </p>
    </div>
  )
}
