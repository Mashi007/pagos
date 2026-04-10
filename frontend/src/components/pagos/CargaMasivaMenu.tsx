import { useState, useEffect, useRef } from 'react'

import { Upload, FileSpreadsheet, ChevronDown, Mail } from 'lucide-react'

import { Button } from '../../components/ui/button'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../../components/ui/popover'

import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'

import { ConfirmarBorrarDiaDialog } from './ConfirmarBorrarDiaDialog'

import toast from 'react-hot-toast'

import { getErrorMessage } from '../../types/errors'

import { pagoService } from '../../services/pagoService'

import { formatLastSyncDate } from '../../utils'

interface CargaMasivaMenuProps {
  onSuccess?: () => void
}

export function CargaMasivaMenu({ onSuccess }: CargaMasivaMenuProps) {
  const [showPagos, setShowPagos] = useState(false)

  const [isOpen, setIsOpen] = useState(false)

  const [showConfirmarBorrar, setShowConfirmarBorrar] = useState(false)

  const [gmailStatus, setGmailStatus] = useState<Awaited<
    ReturnType<typeof pagoService.getGmailStatus>
  > | null>(null)

  const lastRunForWhichWeShowedDialogRef = useRef<string | null>(null)

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
            Gmail
          </p>

          <p className="mb-2 flex items-start gap-2 px-2 text-xs text-gray-600">
            <Mail className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Para procesar correos use la lista Pagos: Agregar pago → Generar
            Excel desde email → Procesar correos.
          </p>

          {gmailStatus && (
            <p className="mb-1 border-t border-gray-100 px-2 py-1 text-xs text-gray-600">
              {gmailStatus.last_status === 'error' ? (
                <span className="block text-amber-600">
                  <span className="font-medium text-amber-700">
                    Última sync Gmail falló
                  </span>
                  {gmailStatus.last_error ? (
                    <span className="mt-1 block max-h-24 overflow-y-auto whitespace-pre-wrap break-words font-normal text-amber-900/85">
                      {gmailStatus.last_error.length > 280
                        ? `${gmailStatus.last_error.slice(0, 280)}…`
                        : gmailStatus.last_error}
                    </span>
                  ) : null}
                  <span className="mt-1 block font-normal text-gray-600">
                    Reintente desde Pagos → Agregar pago → Procesar correos.
                  </span>
                </span>
              ) : gmailStatus.last_run ? (
                <>
                  Última sync: {formatLastSyncDate(gmailStatus.last_run)} -{' '}
                  {gmailStatus.last_emails} correos, {gmailStatus.last_files}{' '}
                  archivos
                  {typeof gmailStatus.last_correos_marcados_revision ===
                    'number' &&
                  gmailStatus.last_correos_marcados_revision > 0 ? (
                    <>
                      <br />
                      <span className="text-emerald-800">
                        {gmailStatus.last_correos_marcados_revision} correo(s)
                        con comprobante OK (IMAGEN 1 / 2 / 3 + estrella).
                      </span>
                    </>
                  ) : null}
                </>
              ) : (
                <span className="text-gray-500">Sin sync aún</span>
              )}
            </p>
          )}
        </PopoverContent>
      </Popover>

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
            if (result.pipeline_running) {
              toast(
                'Sigue un proceso Gmail en curso. Espere a que termine antes de iniciar otro o verá error 409.',
                { duration: 10000 }
              )
            }
          } else {
            toast(result.mensaje || 'Información del día se mantiene en BD.')
          }

          pagoService.getGmailStatus().then(setGmailStatus)
        }}
      />
    </>
  )
}
