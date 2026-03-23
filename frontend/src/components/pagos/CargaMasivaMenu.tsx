import { useState, useEffect, useRef } from 'react'

import { Upload, FileSpreadsheet, ChevronDown, Mail, X } from 'lucide-react'

import { Button } from '../../components/ui/button'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../../components/ui/popover'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'

import { ConfirmarBorrarDiaDialog } from './ConfirmarBorrarDiaDialog'

import toast from 'react-hot-toast'

import { getErrorMessage } from '../../types/errors'

import { pagoService } from '../../services/pagoService'

import { formatLastSyncDate } from '../../utils'

import { useGmailPipeline } from '../../hooks/useGmailPipeline'

interface CargaMasivaMenuProps {
  onSuccess?: () => void
}

export function CargaMasivaMenu({ onSuccess }: CargaMasivaMenuProps) {
  const [showPagos, setShowPagos] = useState(false)

  const [isOpen, setIsOpen] = useState(false)

  const [showConfirmarBorrar, setShowConfirmarBorrar] = useState(false)

  const [scanFilter, setScanFilter] = useState<'unread' | 'read' | 'all'>(
    'unread'
  )

  const lastRunForWhichWeShowedDialogRef = useRef<string | null>(null)

  const {
    loading: loadingGmail,
    gmailStatus,
    setGmailStatus,
    run: runGmail,
    stopPolling: stopGmailPolling,
  } = useGmailPipeline({
    onStatusUpdate: s => {
      setGmailStatus(s)

      if (s?.last_status === 'success' && s?.latest_data_date && s?.last_run) {
        if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
          lastRunForWhichWeShowedDialogRef.current = s.last_run

          setShowConfirmarBorrar(true)
        }
      }
    },

    onDone: s => {
      if (s?.last_run) lastRunForWhichWeShowedDialogRef.current = s.last_run

      setShowConfirmarBorrar(true)
    },
  })

  useEffect(() => {
    pagoService
      .getGmailStatus()
      .then(s => {
        setGmailStatus(s)

        if (
          s?.last_status === 'success' &&
          s?.latest_data_date &&
          s?.last_run
        ) {
          if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
            lastRunForWhichWeShowedDialogRef.current = s.last_run

            setShowConfirmarBorrar(true)
          }
        }
      })
      .catch(() => setGmailStatus(null))
  }, [])

  useEffect(() => {
    if (!isOpen) return

    pagoService
      .getGmailStatus()
      .then(setGmailStatus)
      .catch(() => setGmailStatus(null))
  }, [isOpen])

  useEffect(() => {
    return () => {
      stopGmailPolling()
    }
  }, [stopGmailPolling])

  function handleDetenerSeguimientoGmail() {
    stopGmailPolling()
    toast(
      'Seguimiento en pantalla detenido. El servidor puede seguir procesando el pipeline en segundo plano.',
      { duration: 5000 }
    )
  }

  async function handleGenerarExcelDesdeGmail() {
    setIsOpen(false)

    runGmail(scanFilter)
  }

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            size="lg"
            className="px-6 py-6 text-base font-semibold"
          >
            <Upload className="mr-2 h-5 w-5" />
            Cargar datos
            <ChevronDown className="ml-2 h-4 w-4" />
          </Button>
        </PopoverTrigger>

        <PopoverContent className="w-56 p-2" align="end">
          <button
            className="flex w-full items-center rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-gray-100"
            onClick={() => {
              setIsOpen(false)

              setShowPagos(true)
            }}
          >
            <FileSpreadsheet className="mr-2 h-4 w-4" />
            Pagos desde Excel
          </button>

          <p className="mb-1 mt-2 border-t border-gray-100 px-2 py-1 pt-2 text-xs text-gray-500">
            Otros
          </p>

          {gmailStatus && (
            <p className="mb-1 border-b border-gray-100 px-2 py-1 text-xs text-gray-600">
              {gmailStatus.last_status === 'error' ? (
                <span className="text-amber-600">Última sync falló</span>
              ) : gmailStatus.last_run ? (
                <>
                  Última sync: {formatLastSyncDate(gmailStatus.last_run)} -{' '}
                  {gmailStatus.last_emails} correos, {gmailStatus.last_files}{' '}
                  archivos
                </>
              ) : (
                <span className="text-gray-500">Sin sync aún</span>
              )}
            </p>
          )}

          <div className="space-y-1">
            <div className="px-2 py-1">
              <label className="mb-1 block text-xs text-gray-600">
                Correos a escanear
              </label>

              <Select
                value={scanFilter}
                onValueChange={(v: 'unread' | 'read' | 'all') =>
                  setScanFilter(v)
                }
              >
                <SelectTrigger className="h-8 w-full text-sm">
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="unread">No leídos</SelectItem>

                  <SelectItem value="read">Leídos</SelectItem>

                  <SelectItem value="all">
                    Todos (leídos y no leídos)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <button
              className="flex w-full items-center rounded-md px-3 py-2.5 text-sm transition-colors hover:bg-gray-100 disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="mr-2 h-4 w-4" />

              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>

            {loadingGmail && (
              <button
                type="button"
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-amber-800 transition-colors hover:bg-amber-50"
                onClick={handleDetenerSeguimientoGmail}
              >
                <X className="h-4 w-4 shrink-0" />
                Detener seguimiento (deja de consultar el estado)
              </button>
            )}

            <p className="mt-1 border-t border-gray-100 px-2 py-1 text-xs text-gray-500">
              {scanFilter === 'unread'
                ? 'Solo no leídos. Al terminar se vuelve a revisar la bandeja.'
                : scanFilter === 'read'
                  ? 'Solo correos leídos.'
                  : 'Con «Todos»: leídos y no leídos de toda la bandeja.'}
            </p>
          </div>
        </PopoverContent>
      </Popover>

      {/* Revisar y editar antes de guardar (Pagos Excel) */}

      {showPagos && (
        <ExcelUploaderPagosUI
          onClose={() => setShowPagos(false)}
          onSuccess={() => {
            setShowPagos(false)

            onSuccess?.()
          }}
        />
      )}

      <ConfirmarBorrarDiaDialog
        open={showConfirmarBorrar}
        onOpenChange={setShowConfirmarBorrar}
        fechaDatos={gmailStatus?.latest_data_date}
        correosRevisados={gmailStatus?.last_emails}
        archivosProcesados={gmailStatus?.last_files}
        onElegir={async borrar => {
          const fecha = gmailStatus?.latest_data_date ?? undefined

          try {
            await pagoService.downloadGmailExcel(fecha)

            toast.success('Excel descargado.')
          } catch (e) {
            toast.error(getErrorMessage(e))

            pagoService.getGmailStatus().then(setGmailStatus)

            return
          }

          const result = await pagoService.confirmarDiaGmail(borrar, fecha)

          if (result.confirmado) {
            toast.success(result.mensaje || 'Información del día borrada.')
          } else {
            toast(result.mensaje || 'Información del día se mantiene en BD.')
          }

          pagoService.getGmailStatus().then(setGmailStatus)
        }}
      />
    </>
  )
}
