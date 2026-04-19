/**





 * Hook para ejecutar el pipeline Gmail y hacer polling hasta que termine.





 * El endpoint run-now devuelve inmediatamente (status="running"); este hook





 * hace polling a /status cada 5s hasta que last_status sea "success" o "error".





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
}

interface UseGmailPipelineOptions {
  onDone?: (status: GmailStatus) => void

  onStatusUpdate?: (status: GmailStatus) => void
}

const POLL_INTERVAL_MS = 5000

const POLL_MAX_ATTEMPTS = 300 // 300 × 5s = 25 min máximo de espera (pipeline con muchos correos)

type GmailScanFilter =
  | 'unread'
  | 'read'
  | 'all'
  | 'pending_identification'
  | 'error_email_rescan'

function mensajeSinCorreosNiFilas(scan: GmailScanFilter): string {
  const base =
    'No hubo correos que cumplieran la búsqueda del pipeline (p. ej. imagen/PDF que aplique) o ninguno generó filas en esta pasada (p. ej. varias piezas en el hilo, PDF multipágina, remitente sin coincidencia en clientes).'

  const porFiltro: Record<GmailScanFilter, string> = {
    all:
      ' Filtro: toda la bandeja (leídos y no leídos). Revise Gmail y las etiquetas del flujo.',
    unread: ' Filtro: solo no leídos. Revise Gmail y las etiquetas del flujo.',
    read: ' Filtro: solo leídos. Revise Gmail y las etiquetas del flujo.',
    pending_identification:
      ' Filtro: pendientes de identificación. Revise esa vista y las etiquetas del flujo.',
    error_email_rescan:
      ' Filtro: re-escaneo ERROR EMAIL. Revise esos hilos y las etiquetas del flujo.',
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
    return ' Motivo: falló la API de Gmail al listar correos (no significa “bandeja vacía”); revise credenciales, cuotas y el mensaje de error arriba.'
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

export function useGmailPipeline({
  onDone,
  onStatusUpdate,
}: UseGmailPipelineOptions = {}) {
  const [loading, setLoading] = useState(false)

  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)

  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const abortedRef = useRef(false)

  /** Último scan_filter enviado a run-now (el status no lo devuelve). */
  const lastScanFilterRef = useRef<GmailScanFilter>('all')

  const onDoneRef = useRef(onDone)

  onDoneRef.current = onDone

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)

      pollingRef.current = null
    }

    abortedRef.current = true
    setLoading(false)
  }, [])

  const _pollStatus = useCallback(
    (attempt: number) => {
      if (abortedRef.current) return

      pollingRef.current = setTimeout(async () => {
        try {
          const s = await pagoService.getGmailStatus()

          setGmailStatus(s)

          onStatusUpdate?.(s)

          if (s.last_status && s.last_status !== 'running') {
            // Pipeline terminado

            setLoading(false)

            const emails = s.last_emails ?? 0

            const files = s.last_files ?? 0

            const hasData = !!s.latest_data_date

            if (s.last_status === 'error') {
              const errDetail = s.last_error ? `\n${s.last_error}` : ''

              toast.error(`Error al procesar correos.${errDetail}`, {
                duration: 10000,
              })

              // No abrir diálogo de descarga en caso de error
            } else if (emails === 0 && files === 0) {
              if (hasData) {
                // Datos de una ejecución anterior disponibles para descargar

                toast(
                  `Sin correos procesados en esta ejecución (inbox con imagen/PDF según el filtro). Hay datos del ${s.latest_data_date} listos para descargar.`,

                  { duration: 8000 }
                )

                onDoneRef.current?.(s)
              } else {
                toast(
                  `${mensajeSinCorreosNiFilas(lastScanFilterRef.current)}${detalleCausaSinFilas(s)}`,
                  {
                    duration: 12000,
                  }
                )

                // Sin datos: no abrir el diálogo de descarga
              }
            } else {
              const dateHint = s.latest_data_date
                ? ` (fecha correo: ${s.latest_data_date})`
                : ''

              toast.success(
                `Listo: se revisaron ${emails} correo(s) y ${files} archivo(s) procesados.${dateHint}${detalleCeroArchivosConCorreos(s)}`,
                { duration: 10000 }
              )

              onDoneRef.current?.(s)
            }

            return
          }

          if (attempt >= POLL_MAX_ATTEMPTS) {
            setLoading(false)

            const processed = s.last_emails ?? 0

            const hasData = !!s.latest_data_date

            if (hasData) {
              toast.success(
                `Procesamiento en curso (${processed} correo(s) hasta ahora). Puede descargar ya los datos disponibles.`,

                { duration: 8000 }
              )

              onDoneRef.current?.(s)
            } else {
              toast(
                `El procesamiento sigue en curso (${processed} correo(s)). Espere y vuelva a intentar descargar.`,

                { duration: 10000 }
              )
            }

            return
          }

          _pollStatus(attempt + 1)
        } catch {
          if (attempt < POLL_MAX_ATTEMPTS) {
            _pollStatus(attempt + 1)
          } else {
            setLoading(false)
          }
        }
      }, POLL_INTERVAL_MS)
    },

    [onStatusUpdate]
  )

  const run = useCallback(
    async (
      scanFilter?:
        | 'unread'
        | 'read'
        | 'all'
        | 'pending_identification'
        | 'error_email_rescan'
    ) => {
      if (loading) return

      abortedRef.current = false

      setLoading(true)

      lastScanFilterRef.current = scanFilter ?? 'all'

      toast('Procesando correos en segundo plano...', { duration: 4000 })

      try {
        await pagoService.runGmailNow(true, scanFilter)

        // El endpoint devuelve inmediatamente (status="running"); hacer polling

        _pollStatus(0)
      } catch (e) {
        setLoading(false)

        toast.error(getErrorMessage(e))
      }
    },
    [loading, _pollStatus]
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

  return {
    loading,
    gmailStatus,
    setGmailStatus,
    run,
    stopPolling,
    refreshStatus,
  }
}
