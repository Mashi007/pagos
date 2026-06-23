/**





 * Hook para ejecutar el pipeline Gmail y hacer polling hasta que termine.





 * El endpoint run-now devuelve inmediatamente (status="running"); este hook





 * hace polling a /status cada 10s hasta que last_status sea "success" o "error".





 */

import { useState, useRef, useCallback } from 'react'

import toast from 'react-hot-toast'

import { pagoService } from '../services/pagoService'

import { getErrorMessage } from '../types/errors'

/** Resumen de la última corrida (backend); sirve para explicar 0 correos / 0 archivos. */
export type GmailRunSummary = {
  scan_filter?: string
  gmail_messages_listed?: number
  messages_skipped_invalid_sender?: number
  messages_skipped_drive_folder?: number
  list_error?: boolean
  pipeline_error?: boolean
  /** Comprobantes con fila sync_item en esta corrida. */
  comprobantes_digitados?: number
  /** Altas automáticas exitosas (traza CUOTAS_OK con pago). */
  pagos_validos_alta_automatica?: number
  /** Pagos creados sin aplicación de cuotas (requieren revisión). */
  pagos_sin_aplicacion_cuotas?: number
  /** Comprobantes sin alta automática (revisión / Excel). */
  pagos_invalidos_pendientes_revision?: number
  /** Modelo Gemini usado en la corrida (settings GEMINI_MODEL). */
  gemini_model?: string
  /** Fase actual del pipeline (listed, processing, …). */
  pipeline_phase?: string
  /** Métricas de latencia de Gemini por corrida. */
  gemini_calls_total?: number
  gemini_ms_total?: number
  gemini_ms_max?: number
  gemini_ms_avg?: number
  gemini_second_pass_total?: number
  gemini_second_pass_hits?: number
  none_reason_counts?: Record<string, number>
  none_reason_hint_counts?: Record<string, number>
}

/** Texto corto (1 línea) para mostrar en UI fija (barra superior), sin depender del toast. */
export function gmailRunSummaryHeadline(rs: GmailRunSummary): string {
  const partes: string[] = []

  if (typeof rs.pagos_validos_alta_automatica === 'number') {
    partes.push(`Altas OK: ${rs.pagos_validos_alta_automatica}`)
  }
  if (typeof rs.pagos_invalidos_pendientes_revision === 'number') {
    partes.push(`Pendientes: ${rs.pagos_invalidos_pendientes_revision}`)
  }
  if (
    typeof rs.pagos_sin_aplicacion_cuotas === 'number' &&
    rs.pagos_sin_aplicacion_cuotas > 0
  ) {
    partes.push(`Sin cuotas: ${rs.pagos_sin_aplicacion_cuotas}`)
  }
  if (typeof rs.comprobantes_digitados === 'number') {
    partes.push(`Comprobantes: ${rs.comprobantes_digitados}`)
  }

  const pass2Total =
    typeof rs.gemini_second_pass_total === 'number'
      ? rs.gemini_second_pass_total
      : null
  const pass2Hits =
    typeof rs.gemini_second_pass_hits === 'number'
      ? rs.gemini_second_pass_hits
      : null
  if (pass2Total !== null && pass2Hits !== null && pass2Total > 0) {
    partes.push(`2ª pasada: ${pass2Hits}/${pass2Total}`)
  }

  const reasons = rs.none_reason_counts
  const top =
    reasons != null
      ? Object.entries(reasons)
          .filter(([, v]) => Number.isFinite(Number(v)) && Number(v) > 0)
          .sort((a, b) => Number(b[1]) - Number(a[1]))[0]
      : undefined
  if (top) {
    partes.push(`Top falla: ${top[0]}=${top[1]}`)
  }

  return partes.join(' · ')
}

/** Líneas detalladas para un panel colapsable (popover / monitor). */
export function gmailRunSummaryLines(rs: GmailRunSummary): string[] {
  const lines: string[] = []

  if (typeof rs.scan_filter === 'string' && rs.scan_filter.trim()) {
    lines.push(`Filtro escaneo: ${rs.scan_filter}`)
  }

  const listed = Number(rs.gmail_messages_listed)
  const skipS = Number(rs.messages_skipped_invalid_sender)
  const skipD = Number(rs.messages_skipped_drive_folder)
  if (Number.isFinite(listed) && listed >= 0) {
    const sufijo =
      Number.isFinite(skipS) && Number.isFinite(skipD)
        ? ` (omitidos remitente: ${skipS}; Drive: ${skipD})`
        : ''
    lines.push(`Hilos listados en Gmail: ${listed}${sufijo}`)
  }

  if (rs.list_error === true) {
    lines.push('Listado Gmail: error (no implica bandeja vacía).')
  }
  if (rs.pipeline_error === true) {
    lines.push('Pipeline: error reportado en resumen de corrida.')
  }

  if (typeof rs.comprobantes_digitados === 'number') {
    lines.push(
      `Comprobantes digitalizados (sync_item): ${rs.comprobantes_digitados}`
    )
  }
  if (typeof rs.pagos_validos_alta_automatica === 'number') {
    lines.push(
      `Pagos válidos (alta automática / CUOTAS_OK): ${rs.pagos_validos_alta_automatica}`
    )
  }
  if (typeof rs.pagos_sin_aplicacion_cuotas === 'number') {
    lines.push(
      `Pagos sin aplicación a cuotas: ${rs.pagos_sin_aplicacion_cuotas}`
    )
  }
  if (typeof rs.pagos_invalidos_pendientes_revision === 'number') {
    lines.push(
      `Pagos no válidos / pendientes revisión: ${rs.pagos_invalidos_pendientes_revision}`
    )
  }

  if (typeof rs.gemini_model === 'string' && rs.gemini_model.trim()) {
    lines.push(`Modelo Gemini: ${rs.gemini_model}`)
  }
  const calls =
    typeof rs.gemini_calls_total === 'number' ? rs.gemini_calls_total : null
  const msTotal =
    typeof rs.gemini_ms_total === 'number' ? rs.gemini_ms_total : null
  const msAvg = typeof rs.gemini_ms_avg === 'number' ? rs.gemini_ms_avg : null
  const msMax = typeof rs.gemini_ms_max === 'number' ? rs.gemini_ms_max : null
  if (calls !== null && msTotal !== null) {
    const avgTxt = msAvg !== null ? `; avg ${Math.round(msAvg)} ms` : ''
    const maxTxt = msMax !== null ? `; max ${Math.round(msMax)} ms` : ''
    lines.push(
      `Gemini: ${calls} llamada(s), ${Math.round(msTotal)} ms total${avgTxt}${maxTxt}`
    )
  }

  const pass2Total =
    typeof rs.gemini_second_pass_total === 'number'
      ? rs.gemini_second_pass_total
      : null
  const pass2Hits =
    typeof rs.gemini_second_pass_hits === 'number'
      ? rs.gemini_second_pass_hits
      : null
  if (pass2Total !== null && pass2Hits !== null && pass2Total > 0) {
    lines.push(`Rescate 2ª pasada: ${pass2Hits}/${pass2Total}`)
  }

  const reasons = rs.none_reason_counts
  const reasonEntries = reasons
    ? Object.entries(reasons)
        .filter(([, v]) => Number.isFinite(Number(v)) && Number(v) > 0)
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .slice(0, 8)
    : []
  if (reasonEntries.length > 0) {
    lines.push(
      `Top fallas (ninguno): ${reasonEntries.map(([k, v]) => `${k}=${v}`).join(', ')}`
    )
  }

  const hints = rs.none_reason_hint_counts
  const hintEntries = hints
    ? Object.entries(hints)
        .filter(([, v]) => Number.isFinite(Number(v)) && Number(v) > 0)
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .slice(0, 8)
    : []
  if (hintEntries.length > 0) {
    lines.push(
      `Top pistas (ninguno): ${hintEntries.map(([k, v]) => `${k}=${v}`).join(', ')}`
    )
  }

  return lines
}

export function diagnosticoIdentificacionDesdeRunSummary(
  rs: GmailRunSummary
): string {
  const pass2Total =
    typeof rs.gemini_second_pass_total === 'number'
      ? rs.gemini_second_pass_total
      : null
  const pass2Hits =
    typeof rs.gemini_second_pass_hits === 'number'
      ? rs.gemini_second_pass_hits
      : null
  const reasons = rs.none_reason_counts
  const reasonEntries = reasons
    ? Object.entries(reasons)
        .filter(([, v]) => Number.isFinite(Number(v)) && Number(v) > 0)
        .sort((a, b) => Number(b[1]) - Number(a[1]))
        .slice(0, 3)
    : []
  const reasonTxt =
    reasonEntries.length > 0
      ? ` Top fallas: ${reasonEntries.map(([k, v]) => `${k}=${v}`).join(', ')}.`
      : ''
  const passTxt =
    pass2Total !== null && pass2Hits !== null
      ? ` Rescate 2ª pasada: ${pass2Hits}/${pass2Total}.`
      : ''
  return `${passTxt}${reasonTxt}`
}

/** Texto corto para botón / barra mientras last_status=running. */
export function gmailRunningProgressLabel(
  status:
    | Pick<
        GmailStatus,
        'last_status' | 'last_emails' | 'last_files' | 'last_run_summary'
      >
    | null
    | undefined
): string {
  if (!status || status.last_status !== 'running') {
    return 'Procesar manualmente'
  }
  const emails = status.last_emails ?? 0
  const files = status.last_files ?? 0
  const listed = status.last_run_summary?.gmail_messages_listed
  const phase = status.last_run_summary?.pipeline_phase

  if (typeof listed === 'number' && listed > 0) {
    if (emails === 0 && phase === 'listed') {
      return `Listando ${listed} correo(s) en Gmail…`
    }
    if (emails < listed) {
      return `Procesando… ${emails}/${listed} correos (${files} arch.)`
    }
    return `Procesando… ${emails}/${listed} correos (${files} arch.)`
  }

  if (emails === 0 && files === 0) {
    return 'Procesando… iniciando escaneo Gmail'
  }
  return `Procesando… ${emails} correos, ${files} archivos`
}

interface GmailStatus {
  last_run: string | null

  last_status: string | null

  last_emails: number

  last_files: number

  last_error?: string | null

  next_run_approx: string | null

  latest_data_date?: string | null // fecha más reciente con datos disponibles para descargar

  last_correos_marcados_revision?: number

  last_run_summary?: GmailRunSummary | null

  pipeline_phase?: string | null

  /** True si el backend detecta running huérfano (sin actividad prolongada). */
  running_looks_stale?: boolean
}

interface UseGmailPipelineOptions {
  onDone?: (status: GmailStatus) => void

  onStatusUpdate?: (status: GmailStatus) => void

  /**
   * Si es true, el hook no muestra los toasts internos de "terminado" / "sin correos".
   * El caller se encarga del feedback en `onDone` (p. ej. para usar conteos
   * propios de la pantalla en lugar de `last_emails` del sync global).
   */
  suppressDoneToasts?: boolean
}

const POLL_MAX_ATTEMPTS = 220

/** Intervalo entre consultas: alineado con STALE_MAX_RUNNING_MINUTES (~110 min) en backend. */
function pollDelayMs(attempt: number): number {
  if (attempt === 0) return 3000
  if (attempt < 40) return 10000
  if (attempt < 90) return 20000
  if (attempt < 160) return 30000
  return 45000
}

/** Tras varios fallos de red / timeout (servidor ocupado con Gemini), dejar de martillar el API. */
const POLL_MAX_CONSECUTIVE_FETCH_ERRORS = 8

/**
 * Un solo loop de polling Gmail en toda la SPA.
 * Sin esto, remounts o varios useGmailPipeline disparan decenas de cadenas en paralelo
 * (~2-3 GET /status por segundo en logs de backend).
 */
let globalGmailPollSession = 0
let globalGmailPollTimeout: ReturnType<typeof setTimeout> | null = null

function beginGlobalGmailPollSession(): number {
  globalGmailPollSession += 1
  if (globalGmailPollTimeout !== null) {
    clearTimeout(globalGmailPollTimeout)
    globalGmailPollTimeout = null
  }
  return globalGmailPollSession
}

function cancelGlobalGmailPollSession(): void {
  globalGmailPollSession += 1
  if (globalGmailPollTimeout !== null) {
    clearTimeout(globalGmailPollTimeout)
    globalGmailPollTimeout = null
  }
}

type GmailScanFilter =
  | 'unread'
  | 'read'
  | 'all'
  | 'pending_identification'
  | 'error_email_rescan'
  | 'manual_redigitaliza_por_remitente'

function mensajeSinCorreosNiFilas(scan: GmailScanFilter): string {
  const base =
    'No hubo correos que cumplieran la búsqueda del pipeline (p. ej. imagen/PDF que aplique) o ninguno generó filas en esta pasada (p. ej. varias piezas en el hilo, PDF multipágina, remitente sin coincidencia en clientes).'

  const porFiltro: Record<GmailScanFilter, string> = {
    all: ' Filtro: toda la bandeja (leídos y no leídos). Revise Gmail y las etiquetas del flujo.',
    unread: ' Filtro: solo no leídos. Revise Gmail y las etiquetas del flujo.',
    read: ' Filtro: solo leídos. Revise Gmail y las etiquetas del flujo.',
    pending_identification:
      ' Filtro: pendientes de identificación. Revise esa vista y las etiquetas del flujo.',
    error_email_rescan:
      ' Filtro: re-escaneo ERROR EMAIL. Revise esos hilos y las etiquetas del flujo.',
    manual_redigitaliza_por_remitente:
      ' Filtro: re-escaneo manual por remitente. Verifica que el correo tenga adjuntos/imagen-PDF en bandeja.',
  }

  return base + porFiltro[scan]
}

/** Aclara por qué quedó 0/0 según métricas del servidor (GET /pagos/gmail/status). */
function detalleCausaSinFilas(s: GmailStatus): string {
  const raw = s.last_run_summary
  if (raw == null || typeof raw !== 'object') return ''

  const listed = Number(raw.gmail_messages_listed)
  const skipS = Number(raw.messages_skipped_invalid_sender)
  const skipD = Number(raw.messages_skipped_drive_folder)
  if (
    !Number.isFinite(listed) ||
    !Number.isFinite(skipS) ||
    !Number.isFinite(skipD)
  ) {
    return ''
  }

  if (raw.list_error === true) {
    return ' Motivo: falló la API de Gmail al listar correos (no significa "bandeja vacía"); revise credenciales, cuotas y el mensaje de error arriba.'
  }

  if (listed === 0) {
    return ' Motivo: Gmail no devolvió hilos con el criterio del módulo (entrada + imagen/PDF o medios admitidos). Un correo solo de texto o sin medio escaneable no entra, aunque figure como no leído.'
  }

  const emails = s.last_emails ?? 0
  const files = s.last_files ?? 0
  if (emails === 0 && files === 0 && skipS + skipD >= listed) {
    return ` Motivo: se listaron ${listed} hilo(s) pero ninguno pasó al detalle (remitente «De» inválido: ${skipS}; fallo carpeta Drive: ${skipD}).`
  }

  return ''
}

/** Si hubo revisión de hilos pero 0 archivos en Excel. */
function detalleCeroArchivosConCorreos(s: GmailStatus): string {
  const emails = s.last_emails ?? 0
  const files = s.last_files ?? 0
  if (files > 0 || emails === 0) return ''
  return ' Ningún comprobante generó fila final (plantilla incompleta, regla «una sola pieza», dedupe de binario, etc.).'
}

function detalleDiagnosticoIdentificacion(s: GmailStatus): string {
  const rs = s.last_run_summary
  if (!rs || typeof rs !== 'object') return ''
  return diagnosticoIdentificacionDesdeRunSummary(rs)
}

/** Notificación final con conteos válidos / pendientes (backend run_summary). */
function textoNotificacionFinProcesamientoGmail(s: GmailStatus): string | null {
  const rs = s.last_run_summary
  if (
    !rs ||
    typeof rs.pagos_validos_alta_automatica !== 'number' ||
    typeof rs.pagos_invalidos_pendientes_revision !== 'number'
  ) {
    return null
  }
  const correos = s.last_emails ?? 0
  const validos = rs.pagos_validos_alta_automatica
  const invalidos = rs.pagos_invalidos_pendientes_revision
  const comp =
    typeof rs.comprobantes_digitados === 'number'
      ? rs.comprobantes_digitados
      : null
  const compTxt = comp !== null ? ` Comprobantes digitalizados: ${comp}.` : ''
  return (
    `Procesamiento terminado. Se procesaron ${correos} correo(s).` +
    ` Hay ${validos} pago(s) válido(s) (alta automática) y ${invalidos} pago(s) no válido(s) o pendientes de revisión.${compTxt}` +
    ` Puede ver los pendientes en el Excel (botón Procesar manualmente → menú → Descargar Excel pendientes de revisión).`
  )
}

export function useGmailPipeline({
  onDone,
  onStatusUpdate,
  suppressDoneToasts,
}: UseGmailPipelineOptions = {}) {
  const [loading, setLoading] = useState(false)

  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)

  const [pollGaveUp, setPollGaveUp] = useState(false)

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const abortedRef = useRef(false)

  const fetchErrorStreakRef = useRef(0)
  const staleToastShownRef = useRef(false)
  const pollingActiveRef = useRef(false)
  /** Tras agotar intentos con last_status=running, no reanudar polling hasta un run() nuevo. */
  const gaveUpWhileRunningRef = useRef(false)

  /** Último scan_filter enviado a run-now (el status no lo devuelve). */
  const lastScanFilterRef = useRef<GmailScanFilter>('all')

  const onDoneRef = useRef(onDone)

  onDoneRef.current = onDone

  const pollSessionRef = useRef(0)

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)

      pollingRef.current = null
    }

    cancelGlobalGmailPollSession()
    abortedRef.current = true
    fetchErrorStreakRef.current = 0
    staleToastShownRef.current = false
    pollingActiveRef.current = false
    setPollGaveUp(false)
    setLoading(false)
  }, [])

  const _pollStatus = useCallback(
    (attempt: number, session: number) => {
      if (abortedRef.current || session !== globalGmailPollSession) return

      if (pollingRef.current) {
        clearTimeout(pollingRef.current)
        pollingRef.current = null
      }

      const delayMs = pollDelayMs(attempt)
      pollingRef.current = setTimeout(async () => {
        pollingRef.current = null
        globalGmailPollTimeout = null
        if (abortedRef.current || session !== globalGmailPollSession) {
          if (session !== globalGmailPollSession) {
            setLoading(false)
          }
          return
        }

        try {
          const s = await pagoService.getGmailStatus()

          fetchErrorStreakRef.current = 0

          setGmailStatus(s)

          onStatusUpdate?.(s)

          if (s.running_looks_stale && s.last_status === 'running') {
            if (!suppressDoneToasts && !staleToastShownRef.current) {
              staleToastShownRef.current = true
              toast(
                'El escaneo Gmail lleva mucho tiempo sin avanzar. El servidor lo liberará en la próxima consulta; pulse «Procesar manualmente» de nuevo.',
                { duration: 12000 }
              )
            }
            pollingActiveRef.current = false
            gaveUpWhileRunningRef.current = true
            setPollGaveUp(true)
            setLoading(false)
            return
          }

          if (s.last_status && s.last_status !== 'running') {
            pollingActiveRef.current = false
            setPollGaveUp(false)
            // Pipeline terminado

            setLoading(false)

            const emails = s.last_emails ?? 0

            const files = s.last_files ?? 0

            const hasData = !!s.latest_data_date

            if (s.last_status === 'error') {
              const errDetail = s.last_error ? `\n${s.last_error}` : ''
              const resumenErr = textoNotificacionFinProcesamientoGmail(s)
              const sufijoResumen = resumenErr ? `\n${resumenErr}` : ''

              if (!suppressDoneToasts) {
                toast.error(
                  `Error al procesar correos.${errDetail}${sufijoResumen}`,
                  {
                    duration: 14000,
                  }
                )
              }
              onDoneRef.current?.(s)

              // No abrir diálogo de descarga en caso de error
            } else if (emails === 0 && files === 0) {
              if (hasData) {
                // Datos de una ejecución anterior disponibles para descargar
                const resumenCero = textoNotificacionFinProcesamientoGmail(s)
                const baseCero = `Sin correos procesados en esta ejecución (inbox con imagen/PDF según el filtro). Hay datos del ${s.latest_data_date} listos para descargar.`
                if (!suppressDoneToasts) {
                  toast(
                    resumenCero ? `${baseCero}\n${resumenCero}` : baseCero,
                    {
                      duration: 10000,
                    }
                  )
                }

                onDoneRef.current?.(s)
              } else {
                if (!suppressDoneToasts) {
                  toast(
                    `${mensajeSinCorreosNiFilas(lastScanFilterRef.current)}${detalleCausaSinFilas(s)}`,
                    {
                      duration: 12000,
                    }
                  )
                }
                onDoneRef.current?.(s)

                // Sin datos: no abrir el diálogo de descarga
              }
            } else {
              const dateHint = s.latest_data_date
                ? ` (fecha correo: ${s.latest_data_date})`
                : ''
              const resumenFin = textoNotificacionFinProcesamientoGmail(s)
              const diagIdent = detalleDiagnosticoIdentificacion(s)
              const cuerpo = resumenFin
                ? `${resumenFin}${diagIdent}${dateHint}${detalleCeroArchivosConCorreos(s)}`
                : `Listo: se revisaron ${emails} correo(s) y ${files} archivo(s) procesados.${dateHint}${detalleCeroArchivosConCorreos(s)}`

              if (!suppressDoneToasts) {
                toast.success(cuerpo, { duration: resumenFin ? 14000 : 10000 })
              }

              onDoneRef.current?.(s)
            }

            return
          }

          if (attempt >= POLL_MAX_ATTEMPTS) {
            pollingActiveRef.current = false
            gaveUpWhileRunningRef.current = true
            setPollGaveUp(true)
            setLoading(false)

            const processed = s.last_emails ?? 0

            const hasData = !!s.latest_data_date

            if (hasData) {
              const resumenTope = textoNotificacionFinProcesamientoGmail(s)
              const diagIdent = detalleDiagnosticoIdentificacion(s)
              const msgTope = resumenTope
                ? `${resumenTope}${diagIdent} Tiempo de espera máximo alcanzado; si aún corre en servidor, consulte estado o descargue Excel.`
                : `Procesamiento en curso (${processed} correo(s) hasta ahora). Puede descargar ya los datos disponibles.`
              if (!suppressDoneToasts) {
                toast.success(msgTope, { duration: resumenTope ? 14000 : 8000 })
              }

              onDoneRef.current?.(s)
            } else {
              const resumenTope = textoNotificacionFinProcesamientoGmail(s)
              const msgTope = resumenTope
                ? `${resumenTope} Tiempo de espera máximo alcanzado en el navegador.`
                : `El procesamiento sigue en curso (${processed} correo(s)). Espere y vuelva a intentar descargar.`
              if (!suppressDoneToasts) {
                toast(msgTope, { duration: 10000 })
              }
            }

            return
          }

          _pollStatus(attempt + 1, session)
        } catch {
          fetchErrorStreakRef.current += 1
          if (
            fetchErrorStreakRef.current >= POLL_MAX_CONSECUTIVE_FETCH_ERRORS
          ) {
            pollingActiveRef.current = false
            setPollGaveUp(true)
            setLoading(false)
            if (!suppressDoneToasts) {
              toast(
                'No pudimos consultar el progreso del escaneo Gmail (el servidor no respondió a tiempo varias veces). ' +
                  'El procesamiento puede seguir en segundo plano con muchos correos o imágenes grandes. ' +
                  'Espere unos minutos y recargue la página, o revise los logs del backend en Render.',
                { duration: 14000, icon: '!' }
              )
            }
            return
          }
          if (attempt < POLL_MAX_ATTEMPTS) {
            _pollStatus(attempt + 1, session)
          } else {
            pollingActiveRef.current = false
            setLoading(false)
          }
        }
      }, delayMs)
      globalGmailPollTimeout = pollingRef.current
    },

    [onStatusUpdate, suppressDoneToasts]
  )

  const armPolling = useCallback(
    (scanFilter?: GmailScanFilter) => {
      const session = beginGlobalGmailPollSession()
      pollSessionRef.current = session
      abortedRef.current = false
      fetchErrorStreakRef.current = 0
      staleToastShownRef.current = false
      pollingActiveRef.current = true
      setPollGaveUp(false)
      lastScanFilterRef.current = scanFilter ?? 'all'
      setLoading(true)
      void pagoService.getGmailStatus().then(s => {
        if (session !== globalGmailPollSession) return
        setGmailStatus(s)
        onStatusUpdate?.(s)
      })
      _pollStatus(0, session)
    },
    [_pollStatus, onStatusUpdate]
  )

  const run = useCallback(
    async (
      scanFilter?: GmailScanFilter,
      fromEmail?: string | null,
      maxMessages?: number | null,
      /** Solo modo manual_redigitaliza_por_remitente: remitente | destinatario | participante. */
      criterio?: 'remitente' | 'destinatario' | 'participante' | null
    ) => {
      if (loading) {
        if (!suppressDoneToasts) {
          toast('Ya hay un escaneo Gmail en seguimiento.', { duration: 3000 })
        }
        return
      }

      abortedRef.current = false

      fetchErrorStreakRef.current = 0
      staleToastShownRef.current = false
      gaveUpWhileRunningRef.current = false
      setPollGaveUp(false)

      setLoading(true)
      lastScanFilterRef.current = scanFilter ?? 'all'

      toast('Procesando correos en segundo plano...', { duration: 4000 })

      try {
        await pagoService.runGmailNow(
          true,
          scanFilter,
          fromEmail ?? null,
          maxMessages ?? null,
          criterio ?? null
        )

        // El endpoint devuelve inmediatamente (status="running"); hacer polling
        armPolling(scanFilter)
      } catch (e) {
        setLoading(false)

        toast.error(getErrorMessage(e))
      }
    },
    [loading, armPolling]
  )

  const refreshStatus = useCallback(() => {
    pagoService
      .getGmailStatus()
      .then(s => {
        setGmailStatus(s)

        onStatusUpdate?.(s)
      })
      .catch(() => {})
  }, [onStatusUpdate])

  /**
   * Sólo arranca el polling a /status (sin lanzar otro pipeline).
   * Útil cuando otro endpoint ya creó el sync_id (p. ej. /pagos/gmail/procesar-mensajes
   * en el módulo Actualizaciones > Gmail). Igualmente respeta el lock global de 2 h:
   * si el backend ya estaba en estado "running", el polling termina en el primer
   * tic con last_status != "running".
   */
  const startPolling = useCallback(
    (scanFilter?: GmailScanFilter) => {
      if (gaveUpWhileRunningRef.current) return
      armPolling(scanFilter)
    },
    [armPolling]
  )

  return {
    loading,
    pollGaveUp,
    gmailStatus,
    setGmailStatus,
    run,
    startPolling,
    stopPolling,
    refreshStatus,
  }
}
