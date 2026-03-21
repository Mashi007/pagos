import { Save } from 'lucide-react'

import { Button } from '../../../components/ui/button'

interface CrearClienteFormActionsProps {
  onCancel: () => void

  isFormValid: () => boolean

  isSubmitting: boolean
}

export function CrearClienteFormActions({
  onCancel,

  isFormValid,

  isSubmitting,
}: CrearClienteFormActionsProps) {
  return (
    <div className="flex justify-end gap-4 border-t pt-6">
      <Button
        type="button"
        variant="outline"
        onClick={onCancel}
        disabled={isSubmitting}
      >
        Cancelar
      </Button>

      <Button
        type="submit"
        disabled={!isFormValid() || isSubmitting}
        className="flex items-center gap-2"
      >
        <Save className="h-4 w-4" />

        {isSubmitting ? 'Guardando...' : 'Guardar Cliente'}
      </Button>
    </div>
  )
}
