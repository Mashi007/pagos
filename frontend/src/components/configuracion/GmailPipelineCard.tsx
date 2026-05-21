/**
 * Card: Pipeline Gmail - estado y refresco (sin exportación Excel).
 */
import { useState, useEffect, useCallback } from 'react'
import { Mail, Loader2, RefreshCw } from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { apiClient } from '../../services/api'

interface GmailStatus {
  last_run: string | null
  last_status: string | null
  last_emails: number
  last_files: number
  last_error: string | null
  next_run_approx: string | null
  latest_data_date: string | null
  last_correos_marcados_revision?: number
}

export function GmailPipelineCard() {
  const [status, setStatus] = useState<GmailStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await apiClient.get<GmailStatus>(
        '/api/v1/pagos/gmail/status'
      )
      setStatus(data)
    } catch (e) {
      console.error('Error fetching Gmail status:', e)
      setStatus(null)
    } finally {
      setLoadingStatus(false)
    }
  }, [])

  useEffect(() => {
    void fetchStatus()
  }, [fetchStatus])

  const handleRefrescarEstado = async () => {
    try {
      setRefreshing(true)
      await fetchStatus()
    } finally {
      setRefreshing(false)
    }
  }

  const isRunning = status?.last_status === 'running'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-blue-600" />
          Pipeline Gmail - cantidad de correos y archivos procesados
        </CardTitle>
        <CardDescription>
          El disparo principal es manual: Pagos → Agregar pago → Correos Gmail →
          Procesar correos. Los autoconciliados quedan en Pagos; los pendientes
          pasan a Pagos con errores al terminar el proceso. En el servidor puede
          activarse un escaneo automático (06:30-19:30 Caracas).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {loadingStatus && !status ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando estado…
          </div>
        ) : status ? (
          <>
            <div
              className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium ${isRunning ? 'bg-blue-50 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300' : 'bg-muted/60 text-muted-foreground'}`}
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
                  Generando… {status.last_emails} correos, {status.last_files}{' '}
                  archivos procesados
                </>
              ) : (
                <>
                  <Mail className="h-5 w-5 shrink-0" />
                  Última ejecución: {status.last_status ?? '-'} ·{' '}
                  {status.last_emails} correos, {status.last_files} archivos
                </>
              )}
            </div>

            {status.last_error && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {status.last_error}
              </p>
            )}

            {typeof status.last_correos_marcados_revision === 'number' &&
              status.last_correos_marcados_revision > 0 && (
                <p className="text-xs text-emerald-800 dark:text-emerald-200">
                  Última ejecución: {status.last_correos_marcados_revision}{' '}
                  correo(s) con al menos un OK (etiquetas IMAGEN 1 / 2 / 3 +
                  estrella).
                </p>
              )}

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void handleRefrescarEstado()}
              disabled={refreshing}
            >
              {refreshing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Actualizar estado
            </Button>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No se pudo cargar el estado del pipeline Gmail.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
