import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'

export function Plantillas() {
  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
        <p className="text-sm text-gray-500">Herramienta de construcción de plantillas (solo Administrador)</p>
      </div>
      <PlantillasNotificaciones />
    </div>
  )
}

export default Plantillas


