import { useState, useEffect, useRef } from 'react'
import { Upload, FileSpreadsheet, ChevronDown, Mail } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'
import { ExcelUploader } from './ExcelUploader'
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
  const [showUploadDirectPagos, setShowUploadDirectPagos] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [showConfirmarBorrar, setShowConfirmarBorrar] = useState(false)
  const [scanFilter, setScanFilter] = useState<'unread' | 'read' | 'all'>('unread')
  const lastRunForWhichWeShowedDialogRef = useRef<string | null>(null)

  const { loading: loadingGmail, gmailStatus, setGmailStatus, run: runGmail } = useGmailPipeline({
    onStatusUpdate: (s) => {
      setGmailStatus(s)
      if (s?.last_status === 'success' && s?.latest_data_date && s?.last_run) {
        if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
          lastRunForWhichWeShowedDialogRef.current = s.last_run
          setShowConfirmarBorrar(true)
        }
      }
    },
    onDone: (s) => {
      if (s?.last_run) lastRunForWhichWeShowedDialogRef.current = s.last_run
      setShowConfirmarBorrar(true)
    },
  })

  useEffect(() => {
    pagoService.getGmailStatus().then((s) => {
      setGmailStatus(s)
      if (s?.last_status === 'success' && s?.latest_data_date && s?.last_run) {
        if (lastRunForWhichWeShowedDialogRef.current !== s.last_run) {
          lastRunForWhichWeShowedDialogRef.current = s.last_run
          setShowConfirmarBorrar(true)
        }
      }
    }).catch(() => setGmailStatus(null))
  }, [])
  useEffect(() => {
    if (!isOpen) return
    pagoService.getGmailStatus().then(setGmailStatus).catch(() => setGmailStatus(null))
  }, [isOpen])

  async function handleGenerarExcelDesdeGmail() {
    setIsOpen(false)
    runGmail(scanFilter)
  }

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="lg" className="px-6 py-6 text-base font-semibold">
            <Upload className="w-5 h-5 mr-2" />
            Cargar datos
            <ChevronDown className="w-4 h-4 ml-2" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-56 p-2" align="end">
          <p className="text-xs text-gray-500 px-2 py-1 mb-1">Pagos desde Excel</p>
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowPagos(true)
                setIsOpen(false)
              }}
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Previsualizar y editar
            </button>
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowUploadDirectPagos(true)
                setIsOpen(false)
              }}
            >
              <Upload className="w-4 h-4 mr-2" />
              Subir y procesar todo
            </button>
          <p className="text-xs text-gray-500 px-2 py-1 mb-1 mt-2 border-t border-gray-100 pt-2">Otros</p>
          {gmailStatus && (
            <p className="text-xs text-gray-600 px-2 py-1 mb-1 border-b border-gray-100">
              {gmailStatus.last_status === 'error' ? (
                <span className="text-amber-600">Última sync falló</span>
              ) : gmailStatus.last_run ? (
                <>Última sync: {formatLastSyncDate(gmailStatus.last_run)} – {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
              ) : (
                <span className="text-gray-500">Sin sync aún</span>
              )}
            </p>
          )}
<div className="space-y-1">
            <div className="px-2 py-1">
              <label className="text-xs text-gray-600 block mb-1">Correos a escanear</label>
              <Select value={scanFilter} onValueChange={(v: 'unread' | 'read' | 'all') => setScanFilter(v)}>
                <SelectTrigger className="h-8 text-sm w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="unread">No leídos</SelectItem>
                  <SelectItem value="read">Leídos</SelectItem>
                  <SelectItem value="all">Todos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="w-4 h-4 mr-2" />
              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>
            <p className="text-xs text-gray-500 px-2 py-1 mt-1 border-t border-gray-100">
              {scanFilter === 'unread' ? 'Solo no leídos. Al terminar se vuelve a revisar la bandeja.' : scanFilter === 'read' ? 'Solo correos leídos.' : 'Todos los correos de la bandeja.'}
            </p>
          </div>
        </PopoverContent>
      </Popover>

      {/* Modal Previsualizar y editar (Pagos Excel) */}
      {showPagos && (
        <ExcelUploaderPagosUI
          onClose={() => setShowPagos(false)}
          onSuccess={() => {
            setShowPagos(false)
            onSuccess?.()
          }}
        />
      )}

      {/* Modal Subir y procesar todo (Pagos Excel) */}
      {showUploadDirectPagos && (
        <ExcelUploader
          onClose={() => setShowUploadDirectPagos(false)}
          onSuccess={() => {
            setShowUploadDirectPagos(false)
            onSuccess?.()
          }}
        />
      )}

      <ConfirmarBorrarDiaDialog
        open={showConfirmarBorrar}
        onOpenChange={setShowConfirmarBorrar}
        fechaDatos={gmailStatus?.latest_data_date}
        onElegir={async (borrar) => {
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

