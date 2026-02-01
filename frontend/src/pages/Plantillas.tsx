import { useState } from 'react'
import { PlantillasNotificaciones } from '../components/notificaciones/PlantillasNotificaciones'
import { GestionVariables } from '../components/notificaciones/GestionVariables'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { FileText, Database } from 'lucide-react'

export function Plantillas() {
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('plantillas')

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
        <p className="text-sm text-gray-500">Herramienta de construcción de plantillas y gestión de variables (solo Administrador)</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="plantillas">
            <FileText className="h-4 w-4 mr-2" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value="variables">
            <Database className="h-4 w-4 mr-2" />
            Variables Personalizadas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="plantillas" className="mt-6">
          <PlantillasNotificaciones
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
          />
        </TabsContent>

        <TabsContent value="variables" className="mt-6">
          <GestionVariables />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas

