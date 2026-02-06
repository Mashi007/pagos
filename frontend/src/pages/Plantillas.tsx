import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PlantillasNotificaciones } from '../components/notificaciones/PlantillasNotificaciones'
import { GestionVariables } from '../components/notificaciones/GestionVariables'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { FileText, Database } from 'lucide-react'

const SUBTAB_PLANTILLAS = 'plantillas'
const SUBTAB_VARIABLES = 'variables'

export function Plantillas() {
  const [searchParams, setSearchParams] = useSearchParams()
  const subtabFromUrl = searchParams.get('subtab')
  const [plantillaAEditar, setPlantillaAEditar] = useState<any>(null)
  const [activeTab, setActiveTab] = useState(() =>
    subtabFromUrl === SUBTAB_VARIABLES ? SUBTAB_VARIABLES : SUBTAB_PLANTILLAS
  )

  // Sincronizar pestaña activa con URL (subtab=variables abre Variables Personalizadas)
  useEffect(() => {
    const sub = searchParams.get('subtab')
    if (sub === SUBTAB_VARIABLES) setActiveTab(SUBTAB_VARIABLES)
    else if (sub === SUBTAB_PLANTILLAS) setActiveTab(SUBTAB_PLANTILLAS)
  }, [searchParams])

  const handleTabChange = (value: string) => {
    setActiveTab(value)
    const next = new URLSearchParams(searchParams)
    if (value === SUBTAB_VARIABLES) next.set('subtab', SUBTAB_VARIABLES)
    else next.delete('subtab')
    setSearchParams(next, { replace: true })
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <h1 className="text-xl font-bold">Plantillas de notificaciones</h1>
        <p className="text-sm text-gray-500">Herramienta de construcción de plantillas y gestión de variables (solo Administrador)</p>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value={SUBTAB_PLANTILLAS}>
            <FileText className="h-4 w-4 mr-2" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value={SUBTAB_VARIABLES}>
            <Database className="h-4 w-4 mr-2" />
            Variables Personalizadas
          </TabsTrigger>
        </TabsList>

        <TabsContent value={SUBTAB_PLANTILLAS} className="mt-6">
          <PlantillasNotificaciones
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
            tabSeccionActiva={activeTab}
          />
        </TabsContent>

        <TabsContent value={SUBTAB_VARIABLES} className="mt-6 min-h-[400px]">
          <GestionVariables />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Plantillas

