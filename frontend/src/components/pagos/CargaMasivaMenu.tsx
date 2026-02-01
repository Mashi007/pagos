import { useState } from 'react'
import { Upload, FileSpreadsheet, CheckCircle, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ExcelUploader } from './ExcelUploader'
import { ConciliacionExcelUploader } from './ConciliacionExcelUploader'

interface CargaMasivaMenuProps {
  onSuccess?: () => void
}

export function CargaMasivaMenu({ onSuccess }: CargaMasivaMenuProps) {
  const [showPagos, setShowPagos] = useState(false)
  const [showConciliacion, setShowConciliacion] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline">
            <Upload className="w-5 h-5 mr-2" />
            Carga Masiva
            <ChevronDown className="w-4 h-4 ml-2" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-56 p-2" align="end">
          <div className="space-y-1">
            <button
              className="w-full flex items-center px-3 py-2 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowPagos(true)
                setIsOpen(false)
              }}
            >
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              Pagos
            </button>
            <button
              className="w-full flex items-center px-3 py-2 text-sm rounded-md hover:bg-gray-100 transition-colors"
              onClick={() => {
                setShowConciliacion(true)
                setIsOpen(false)
              }}
            >
              <CheckCircle className="w-4 h-4 mr-2" />
              Conciliación
            </button>
          </div>
        </PopoverContent>
      </Popover>

      {/* Modal Carga Masiva Pagos */}
      {showPagos && (
        <ExcelUploader
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

