export type EnvioProgressState = {
  procesados: number
  total: number
  enviados: number
  fallidos: number
  sin_email: number
  /** enviando | pausado_limite_gmail | cancelado_usuario | finalizado */
  estado?: string
  /**
   * Checkpoint: desde donde reanuda esta sesion (procesados del dia anterior / pausa).
   * Si no hay, se asume 0 (lote nuevo).
   */
  desde?: number
  /** Objetivo del lote (igual a total; explicito para la UI). */
  hasta?: number
  tipo_caso?: string
  /** Recibos: un correo por cédula; no usa cupo Gmail ni reanudación al día siguiente. */
  variante?: 'recibos' | 'notificaciones'
  omitidos?: number
  /** ESTADO_CUENTA: tope proactivo diario (600). */
  cupo_diario?: number
  enviados_hoy?: number
}

/** Barra de avance del lote de notificaciones (mismo UI en listado y Configuracion). */
export function EnvioNotificacionesProgressBar({
  progress,
}: {
  progress: EnvioProgressState | null
}) {
  const total = progress && progress.total > 0 ? progress.total : 0
  const hasta = progress?.hasta && progress.hasta > 0 ? progress.hasta : total
  const desde = Math.max(0, Number(progress?.desde ?? 0))
  const procesados = progress
    ? Math.min(progress.procesados, hasta || progress.procesados)
    : 0
  const pct =
    progress && hasta > 0
      ? Math.min(100, Math.round((progress.procesados / hasta) * 100))
      : 15
  const estado = String(progress?.estado || '')
    .trim()
    .toLowerCase()
  const pausado = estado === 'pausado_limite_gmail'
  const cancelado = estado === 'cancelado_usuario'
  const restantes = hasta > 0 ? Math.max(0, hasta - procesados) : 0
  const tramoHoy = Math.max(0, procesados - desde)

  const border = pausado
    ? 'border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-50'
    : cancelado
      ? 'border-slate-300 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-900/40 dark:text-slate-50'
      : 'border-sky-200 bg-sky-50 text-sky-950 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-50'
  const track = pausado
    ? 'bg-amber-200/70 dark:bg-amber-900'
    : cancelado
      ? 'bg-slate-200 dark:bg-slate-800'
      : 'bg-sky-200/70 dark:bg-sky-900'
  const fill = pausado
    ? 'bg-amber-600 dark:bg-amber-400'
    : cancelado
      ? 'bg-slate-500 dark:bg-slate-400'
      : 'bg-sky-600 dark:bg-sky-400'

  const esRecibos = progress?.variante === 'recibos'
  const esEstadoCuenta =
    String(progress?.tipo_caso || '')
      .trim()
      .toUpperCase() === 'ESTADO_CUENTA'
  const cupoDia =
    esEstadoCuenta && Number(progress?.cupo_diario || 0) > 0
      ? Number(progress?.cupo_diario)
      : esEstadoCuenta
        ? 600
        : 0
  const enviandoActivo = estado === 'enviando' || estado === 'en_proceso'
  const enviandoIndet =
    enviandoActivo && procesados <= 0 && !pausado && !cancelado
  const titulo = (() => {
    if (esRecibos) {
      if (!progress || hasta <= 0) return 'Enviando Recibos (1 correo por cédula)…'
      if (estado === 'finalizado')
        return `Recibos: ${procesados} de ${hasta} cédulas`
      return `Enviando Recibos: ${procesados} de ${hasta} cédulas`
    }
    if (!progress) return 'Enviando notificaciones…'
    if (hasta <= 0) return 'Enviando notificaciones…'
    if (estado === 'finalizado')
      return `Notificaciones: ${procesados} de ${hasta}`
    if (pausado && esEstadoCuenta)
      return `Pausado en ${procesados} de ${hasta} (cupo ${cupoDia}/día)`
    if (pausado) return `Pausado en ${procesados} de ${hasta} (cupo Gmail)`
    if (cancelado) return `Cancelado en ${procesados} de ${hasta}`
    if (desde > 0 && esEstadoCuenta)
      return `Reanudando: ${procesados} de ${hasta} (siguiente tras cupo ${cupoDia})`
    if (desde > 0) return `Reanudando: ${procesados} de ${hasta}`
    if (esEstadoCuenta)
      return `Enviando ${procesados} de ${hasta} (máx. ${cupoDia}/día)`
    return `Enviando ${procesados} de ${hasta}`
  })()

  return (
    <div
      className={`w-full min-w-[260px] max-w-lg rounded-md border px-3 py-2 ${border}`}
    >
      <div className="mb-1 flex items-center justify-between gap-2 text-xs font-medium">
        <span>{titulo}</span>
        {progress ? (
          <span className="text-[11px] tabular-nums opacity-80">
            OK {progress.enviados}
            {progress.fallidos > 0 ? ` · fallos ${progress.fallidos}` : ''}
            {progress.sin_email > 0
              ? ` · sin correo ${progress.sin_email}`
              : ''}
            {(progress.omitidos ?? 0) > 0
              ? ` · omitidos ${progress.omitidos}`
              : ''}
          </span>
        ) : null}
      </div>

      {hasta > 0 && !esRecibos ? (
        <div className="mb-1.5 grid grid-cols-3 gap-1 rounded border border-black/5 bg-white/50 px-2 py-1 text-[10px] tabular-nums dark:border-white/10 dark:bg-black/20">
          <div>
            <div className="opacity-70">Desde (ayer/pausa)</div>
            <div className="font-semibold">{desde}</div>
          </div>
          <div>
            <div className="opacity-70">Ahora</div>
            <div className="font-semibold">{procesados}</div>
          </div>
          <div>
            <div className="opacity-70">Hasta (lista)</div>
            <div className="font-semibold">{hasta}</div>
          </div>
        </div>
      ) : null}

      <div
        className={`h-2 w-full overflow-hidden rounded-full ${track}`}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={hasta > 0 ? hasta : 100}
        aria-valuenow={procesados}
        aria-label="Progreso de envio de notificaciones"
      >
        <div
          className={`h-full transition-all duration-300 ${fill} ${enviandoIndet ? 'animate-pulse' : ''}`}
          style={{ width: `${enviandoIndet ? 35 : pct}%` }}
        />
      </div>
      <p className="mt-1 text-[10px] leading-snug opacity-80">
        {esRecibos
          ? estado === 'finalizado'
            ? 'Unidad = cédula (varios pagos del mismo préstamo = un correo). Nadie de la lista pendiente se deja fuera; omitidos son sin email, bloqueados o sin datos.'
            : 'Recorriendo todas las cédulas pendientes del listado. Un correo por cédula, no por pago.'
          : esEstadoCuenta
            ? estado === 'finalizado'
              ? 'Unidad = préstamo APROBADO. Tope 600/día; al terminar el cupo se reanuda mañana (ej. 601).'
              : pausado
                ? `Cupo diario ${cupoDia} agotado. Mañana reanuda en ${procesados + 1} (siguiente tras ${procesados}). Hasta lista: ${hasta}.`
                : desde > 0
                  ? `Reanudación: desde ${desde}. Tramo de hoy +${tramoHoy} (máx. ${cupoDia}). Ahora ${procesados}; el corte de hoy será el nuevo inicio mañana.`
                  : `Tope proactivo ${cupoDia}/día (Caracas). Al llegar a ${cupoDia} se pausa; mañana continúa en ${cupoDia + 1}.`
          : estado === 'finalizado'
            ? 'Unidad = fila del listado (1 correo por préstamo). Nadie elegible se deja fuera; omitidos son ya enviados hoy, sin email, bloqueados o paquete incompleto.'
          : pausado
          ? `Nuevo punto de partida manana: ${procesados}. Quedan ~${restantes}. Se omiten los OK desde el inicio del lote.`
          : cancelado
            ? `Queda guardado para continuar luego desde ${procesados} hasta ${hasta}.`
            : desde > 0
              ? `Tramo de hoy: +${tramoHoy} (desde ${desde}). Sigue hasta cupo Gmail o hasta ${hasta}; esa marca sera el nuevo inicio manana.`
              : 'El servidor sigue hasta terminar o hasta el cupo diario Gmail. Ese corte sera el nuevo inicio del dia siguiente.'}
      </p>
    </div>
  )
}

export type LoteContinuarItem = {
  tipo_caso?: unknown
  procesados?: unknown
  total_en_lista?: unknown
  enviados?: unknown
  fallidos?: unknown
  estado?: unknown
  fecha_negocio_inicio?: unknown
  fecha_negocio_pausa?: unknown
}

/** Indicador estatico de cola: desde donde reanuda manana y hasta donde debe llegar. */
export function LoteContinuarIndicador({
  lotes,
}: {
  lotes: LoteContinuarItem[] | null | undefined
}) {
  if (!Array.isArray(lotes) || lotes.length === 0) return null
  return (
    <div className="w-full max-w-lg rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-50">
      <p className="font-medium">Reanudacion programada (dia siguiente)</p>
      <p className="mt-0.5 text-[10px] opacity-80">
        {lotes.some(
          L => String(L.tipo_caso || '').trim().toUpperCase() === 'ESTADO_CUENTA'
        )
          ? 'Mañana continúa desde el checkpoint (ej. 600 → 601), con tope 600/día, hasta completar o volver a cortar.'
          : 'Manana el sistema inicia donde se quedo ayer, sigue hasta el cupo Gmail, y esa marca sera el nuevo inicio del dia siguiente.'}
      </p>
      <ul className="mt-2 space-y-2">
        {lotes.map((L, i) => {
          const tipo = String(L.tipo_caso || '-')
          const desde = Number(L.procesados ?? 0)
          const hasta = Number(L.total_en_lista ?? 0)
          const rest = Math.max(0, hasta - desde)
          const pct =
            hasta > 0 ? Math.min(100, Math.round((desde / hasta) * 100)) : 0
          return (
            <li
              key={`${tipo}-${i}`}
              className="rounded border border-amber-200/80 bg-white/60 px-2 py-1.5 dark:border-amber-900 dark:bg-black/20"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2 font-medium">
                <span>{tipo}</span>
                <span className="tabular-nums">
                  Desde {desde} → Hasta {hasta}
                </span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-amber-200/80 dark:bg-amber-900">
                <div
                  className="h-full bg-amber-600 dark:bg-amber-400"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="mt-1 text-[10px] tabular-nums opacity-80">
                OK {Number(L.enviados ?? 0)}
                {Number(L.fallidos ?? 0) > 0
                  ? ` · fallos ${Number(L.fallidos ?? 0)}`
                  : ''}
                {' · '}
                pendientes ~{rest}
                {' · '}
                pausa {String(L.fecha_negocio_pausa || '-')}
                {' · '}
                omite OK desde {String(L.fecha_negocio_inicio || '-')}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
