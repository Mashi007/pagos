import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, FileSpreadsheet } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { ExcelUploader } from './ExcelUploader'
import { useEscapeClose } from '../../hooks/useEscapeClose'
import { useCrearCliente, type CrearClienteFormProps } from './crear/useCrearCliente'
import { DatosPersonalesSection } from './crear/DatosPersonalesSection'
import { ContactoSection } from './crear/ContactoSection'
import { NotasSection } from './crear/NotasSection'
import { CrearClienteFormActions } from './crear/CrearClienteFormActions'

export function CrearClienteForm({ cliente, onClose, onSuccess, onClienteCreated, onOpenEditExisting }: CrearClienteFormProps) {
  useEscapeClose(onClose, true)
  const [showExcelUploader, setShowExcelUploader] = useState(false)

  const {
    formData,
    handleInputChange,
    handleSubmit,
    getFieldValidation,
    isFormValid,
    isSubmitting,
    opcionesEstado,
  } = useCrearCliente({ cliente, onClose, onSuccess, onClienteCreated, onOpenEditExisting })

  if (showExcelUploader) {
    return (
      <ExcelUploader
        onClose={() => setShowExcelUploader(false)}
        onSuccess={() => setShowExcelUploader(false)}
      />
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <div className="sticky top-0 bg-white border-b p-6 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {cliente ? 'Editar Cliente' : 'Nuevo Cliente'}
          </h2>
          <div className="flex gap-2">
            {!cliente && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowExcelUploader(true)}
                className="flex items-center gap-2"
              >
                <FileSpreadsheet className="w-4 h-4" />
                Cargar Excel
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              className="flex items-center gap-2"
              title="Cerrar formulario"
            >
              <X className="w-4 h-4" />
              <span className="sr-only">Cerrar</span>
            </Button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <DatosPersonalesSection
            formData={formData}
            onInputChange={handleInputChange}
            getFieldValidation={getFieldValidation}
            opcionesEstado={opcionesEstado}
          />
          <ContactoSection
            formData={formData}
            onInputChange={handleInputChange}
            getFieldValidation={getFieldValidation}
          />
          <NotasSection formData={formData} onInputChange={handleInputChange} />
          <CrearClienteFormActions
            onCancel={onClose}
            isFormValid={isFormValid}
            isSubmitting={isSubmitting}
          />
        </form>
      </motion.div>
    </motion.div>
  )
}
