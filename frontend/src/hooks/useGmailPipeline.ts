/**
 * Hook para ejecutar el pipeline Gmail y hacer polling hasta que termine.
 * El endpoint run-now devuelve inmediatamente (status="running"); este hook
 * hace polling a /status cada 4s hasta que last_status sea "success" o "error".
 */
import { useState, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { pagoService } from '../services/pagoService'
import { getErrorMessage } from '../types/errors'

interface GmailStatus {
  last_run: string | null
  last_status: string | null
  last_emails: number
  last_files: number
  last_error?: string | null
  next_run_approx: string | null
  latest_data_date?: string | null  // fecha más reciente con datos disponibles para descargar
}

interface UseGmailPipelineOptions {
  onDone?: (status: GmailStatus) => void
  onStatusUpdate?: (status: GmailStatus) => void
}

const POLL_INTERVAL_MS = 5000
const POLL_MAX_ATTEMPTS = 300 // 300 × 5s = 25 min máximo de espera (pipeline con muchos correos)

export function useGmailPipeline({ onDone, onStatusUpdate }: UseGmailPipelineOptions = {}) {
  const [loading, setLoading] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortedRef = useRef(false)
  const onDoneRef = useRef(onDone)
  onDoneRef.current = onDone

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current)
      pollingRef.current = null
    }
    abortedRef.current = true
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
            const hasData = !!(s.latest_data_date)
            if (s.last_status === 'error') {
              const errDetail = s.last_error ? `\n${s.last_error}` : ''
              toast.error(`Error al procesar correos.${errDetail}`, { duration: 10000 })
              // No abrir diálogo de descarga en caso de error
            } else if (emails === 0 && files === 0) {
              if (hasData) {
                // Datos de una ejecución anterior disponibles para descargar
                toast(
                  `Sin correos nuevos (solo se procesan no leídos; al terminar se vuelve a revisar la bandeja). Hay datos del ${s.latest_data_date} listos para descargar.`,
                  { duration: 8000 }
                )
                onDoneRef.current?.(s)
              } else {
                toast(
                  'No se encontraron correos para procesar. Regla: solo mensajes NO LEÍDOS con adjuntos (imagen/PDF). Cualquier fecha. Marque como no leído si quiere reprocesar.',
                  { duration: 7000 }
                )
                // Sin datos: no abrir el diálogo de descarga
              }
            } else {
              const dateHint = s.latest_data_date ? ` (fecha correo: ${s.latest_data_date})` : ''
              toast.success(`Listo: ${emails} correo(s), ${files} archivo(s) procesados.${dateHint}`)
              onDoneRef.current?.(s)
            }
            return
          }
          if (attempt >= POLL_MAX_ATTEMPTS) {
            setLoading(false)
            const processed = s.last_emails ?? 0
            const hasData = !!(s.latest_data_date)
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

  const run = useCallback(async () => {
    if (loading) return
    abortedRef.current = false
    setLoading(true)
    toast('Procesando correos en segundo plano...', { duration: 4000 })
    try {
      await pagoService.runGmailNow()
      // El endpoint devuelve inmediatamente (status="running"); hacer polling
      _pollStatus(0)
    } catch (e) {
      setLoading(false)
      toast.error(getErrorMessage(e))
    }
  }, [loading, _pollStatus])

  const refreshStatus = useCallback(() => {
    pagoService.getGmailStatus().then((s) => {
      setGmailStatus(s)
      onStatusUpdate?.(s)
    }).catch(() => {})
  }, [onStatusUpdate])

  return { loading, gmailStatus, setGmailStatus, run, stopPolling, refreshStatus }
}
