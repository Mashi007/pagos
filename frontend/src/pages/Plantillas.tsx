import { useState } from 'react'
import { FileText, Database } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'
import { GeneraVariables } from '@/components/notificaciones/GeneraVariables'
import { ResumenPlantillas } from '@/components/notificaciones/ResumenPlantillas'

export function Plantillas() {
  const [activeTab, setActiveTab] = useState('plantillas')
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
        <p className="text-sm text-gray-500">Herramienta de construcción de plantillas (solo Administrador)</p>
      </div>

      {/* Tabs para Plantillas, Variables y Resumen */}
      <Tabs 
        value={activeTab} 
        onValueChange={(value) => {
          setActiveTab(value)
          // Si cambiamos a plantillas y hay una plantilla para editar, cargarla
          if (value === 'plantillas' && plantillaAEditar) {
            // La plantilla se pasará al componente PlantillasNotificaciones
          }
        }} 
        className="space-y-4"
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="plantillas" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value="variables" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Genera Variables
          </TabsTrigger>
          <TabsTrigger value="resumen" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Resumen
          </TabsTrigger>
        </TabsList>

        <TabsContent value="plantillas" className="space-y-4">
          <PlantillasNotificaciones 
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
          />
        </TabsContent>

        <TabsContent value="variables" className="space-y-4">
          <GeneraVariables />
        </TabsContent>

        <TabsContent value="resumen" className="space-y-4">
          <ResumenPlantillas 
            onEditarPlantilla={(plantilla) => {
              setPlantillaAEditar(plantilla)
              setActiveTab('plantillas')
            }}
            onCambiarPestaña={(pestaña) => setActiveTab(pestaña)}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas


