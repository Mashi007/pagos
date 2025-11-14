import { useState } from 'react'
import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'

export function Plantillas() {
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
        <p className="text-sm text-gray-500">Herramienta de construcción de plantillas (solo Administrador)</p>
      </div>

      <PlantillasNotificaciones 
        plantillaInicial={plantillaAEditar}
        onPlantillaCargada={() => setPlantillaAEditar(null)}
      />
    </div>
  )
}

export default Plantillas


