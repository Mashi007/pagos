// Ejemplo de integración del Modal en componente que tiene "Nuevo escaneo"
// Este es un ejemplo para mostrar cómo usar ModalCambiarCedula

import { useState } from 'react'
import { ModalCambiarCedula } from '@/components/modals/ModalCambiarCedula'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'

export function EscanerPage() {
const [showModalCambiarCedula, setShowModalCambiarCedula] = useState(false)
const [isLoading, setIsLoading] = useState(false)

// Simulación de referencia actual
const referenciaActual = 'RPC-20260428-00111'

const handleNuevoEscaneo = () => {
// Abrir modal para solicitar cédulas
setShowModalCambiarCedula(true)
}

const handleConfirmarCambiarCedula = async (mismaCedula: string, nuevaCedula: string) => {
setIsLoading(true)
try {
// Aquí va la lógica para procesar el cambio de cédula
// Por ejemplo: llamar a API para validar/guardar
console.log('Cambio de cédula:', { mismaCedula, nuevaCedula })

      toast.success(`✅ Iniciando nuevo escaneo\nCédula anterior: ${mismaCedula}\nNueva cédula: ${nuevaCedula}`)

      // Después cerrar modal y proceder con el escaneo
      setShowModalCambiarCedula(false)

      // TODO: Redirigir a interfaz de escaneo o continuar con el flujo
    } catch (error) {
      toast.error('Error al iniciar nuevo escaneo')
      console.error(error)
    } finally {
      setIsLoading(false)
    }

}

return (

<div>
{/_ Contenido del escáner _/}

      {/* Área de éxito - "Reporte enviado" */}
      <div className="rounded-lg border border-green-200 bg-green-50 p-6">
        <h3 className="text-lg font-semibold text-green-900 mb-2">✓ Reporte enviado</h3>
        <p className="text-sm text-green-800 mb-4">Referencia: {referenciaActual}</p>

        <Button
          onClick={handleNuevoEscaneo}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          Nuevo escaneo
        </Button>
      </div>

      {/* Modal para cambiar cédula */}
      <ModalCambiarCedula
        isOpen={showModalCambiarCedula}
        onClose={() => setShowModalCambiarCedula(false)}
        onConfirm={handleConfirmarCambiarCedula}
        isLoading={isLoading}
      />
    </div>

)
}

/\*
INSTRUCCIONES DE INTEGRACIÓN:

1. Importar el modal en el componente que tiene el botón "Nuevo escaneo":
   import { ModalCambiarCedula } from '@/components/modals/ModalCambiarCedula'

2. Crear estado para mostrar/ocultar modal:
   const [showModalCambiarCedula, setShowModalCambiarCedula] = useState(false)

3. En el onClick del botón "Nuevo escaneo":
   onClick={() => setShowModalCambiarCedula(true)}

4. Renderizar el modal:
   <ModalCambiarCedula
   isOpen={showModalCambiarCedula}
   onClose={() => setShowModalCambiarCedula(false)}
   onConfirm={handleConfirmarCambiarCedula}
   isLoading={isLoading}
   />

5. Implementar handleConfirmarCambiarCedula con tu lógica:
   const handleConfirmarCambiarCedula = async (mismaCedula, nuevaCedula) => {
   // Guardar cédulas en estado o localStorage
   // Redirigir a interfaz de escaneo
   // Continuar flujo
   }
   \*/
