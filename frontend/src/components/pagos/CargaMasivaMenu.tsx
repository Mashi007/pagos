import { useState, useEffect } from 'react'
import { Upload, FileSpreadsheet, CheckCircle, ChevronDown, Mail } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover'
import { ExcelUploaderPagosUI } from './ExcelUploaderPagosUI'
import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'
import toast from 'react-hot-toast'
import { pagoService } from '../../services/pagoService'

interface CargaMasivaMenuProps {
  onSuccess?: () => void
}

interface GmailStatus {
  last_run: string | null
  last_status: string | null
  last_emails: number
  last_files: number
  next_run_approx: string | null
}

export function CargaMasivaMenu({ onSuccess }: CargaMasivaMenuProps) {
  const [showPagos, setShowPagos] = useState(false)
  const [showConciliacion, setShowConciliacion] = useState(false)
  const [isOpen, setIsOpen] = useState(false)
  const [loadingGmail, setLoadingGmail] = useState(false)
  const [gmailStatus, setGmailStatus] = useState<GmailStatus | null>(null)

  useEffect(() => {
    if (!isOpen) return
    pagoService.getGmailStatus().then(setGmailStatus).catch(() => setGmailStatus(null))
  }, [isOpen])

  async function handleGenerarExcelDesdeGmail() {
    setIsOpen(false)
    setLoadingGmail(true)
    toast('Puede tardar 1-2 minutos segun la cantidad de correos.', { duration: 3500 })
    try {
      await pagoService.runGmailNow()
      await pagoService.downloadGmailExcel()
      toast.success('Excel generado desde Gmail descargado.')
      pagoService.getGmailStatus().then(setGmailStatus)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Error al generar Excel desde Gmail.'
      toast.error(msg)
    } finally {
      setLoadingGmail(false)
    }
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
          <p className="text-xs text-gray-500 px-2 py-1 mb-1">Cargar desde archivo</p>
          
          {gmailStatus && (
            <p className="text-xs text-gray-600 px-2 py-1 mb-1 border-b border-gray-100">
              {gmailStatus.last_status === 'error' ? (
                <span className="text-amber-600">Última sync falló</span>
              ) : gmailStatus.last_run ? (
                <>Última sync: {new Date(gmailStatus.last_run).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} – {gmailStatus.last_emails} correos, {gmailStatus.last_files} archivos</>
              ) : (
                <span className="text-gray-500">Sin sync aún</span>
              )}
            </p>
          )}
<div className="space-y-1">
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowPagos(true)
                setIsOpen(false)
              }}
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Pagos (Excel)
            </button>
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowConciliacion(true)
                setIsOpen(false)
              }}
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Conciliación
            </button>
            <button
              className="w-full flex items-center px-3 py-2.5 text-sm rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
              onClick={handleGenerarExcelDesdeGmail}
              disabled={loadingGmail}
            >
              <Mail className="w-4 h-4 mr-2" />
              {loadingGmail ? 'Generando...' : 'Generar Excel desde Gmail'}
            </button>
          </div>
        </PopoverContent>
      </Popover>

      {/* Modal Carga Masiva Pagos */}
      {showPagos && (
        <ExcelUploaderPagosUI
          onClose={() => setShowPagos(false)}
          onSuccess={() => {
            setShowPagos(false)
            onSuccess?.()
          }}
        />
      )}

      {/* Modal Conciliación */}
      {showConciliacion && (
        <ConciliacionExcelUploader
          onClose={() => setShowConciliacion(false)}
          onSuccess={() => {
            setShowConciliacion(false)
            onSuccess?.()
          }}
        />
      )}
    </>
  )
}

