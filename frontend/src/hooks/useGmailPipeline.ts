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
  next_run_approx: string | null
}

interface UseGmailPipelineOptions {
  onDone?: (status: GmailStatus) => void
  onStatusUpdate?: (status: GmailStatus) => void
}

const POLL_INTERVAL_MS = 4000
const POLL_MAX_ATTEMPTS = 75 // 75 × 4s = 5 min máximo de espera

export function useGmailPipeline({ onDone, onStatusUpdate }: UseGmailPipelineOptions = {}) {
  const [loading, setLoading] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortedRef = useRef(false)

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
            onDone?.(s)
            const emails = s.last_emails ?? 0
            const files = s.last_files ?? 0
            if (s.last_status === 'error') {
              toast.error('Error al procesar correos. Revise los logs del servidor.')
            } else if (emails === 0 && files === 0) {
              toast('No se encontraron correos para procesar. Revise que haya correos no leídos con adjuntos (imagen/PDF).', { duration: 6000 })
            } else {
              toast.success(`Listo: ${emails} correo(s), ${files} archivo(s) procesados.`)
            }
            return
          }
          if (attempt >= POLL_MAX_ATTEMPTS) {
            setLoading(false)
            toast('El procesamiento sigue en curso. Puede descargar el Excel en unos minutos.', { duration: 8000 })
            onDone?.(s)
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
    [onDone, onStatusUpdate]
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
