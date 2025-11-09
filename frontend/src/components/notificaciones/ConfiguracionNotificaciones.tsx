import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmailConfig } from '@/components/configuracion/EmailConfig'
import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'
import { GeneraVariables } from '@/components/notificaciones/GeneraVariables'
import { ResumenPlantillas } from '@/components/notificaciones/ResumenPlantillas'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Mail, FileText, Settings, Database } from 'lucide-react'
import { NotificacionPlantilla } from '@/services/notificacionService'

export function ConfiguracionNotificaciones() {
  const [activeTab, setActiveTab] = useState('email')
  const [plantillaAEditar, setPlantillaAEditar] = useState<NotificacionPlantilla | null>(null)

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-blue-600" />
            Configuración de Notificaciones
          </CardTitle>
          <CardDescription>
            Gestiona las plantillas de notificaciones y la configuración de email para enviar correos a los clientes.
            Las plantillas permiten personalizar los mensajes usando variables como {'{{nombre}}'}, {'{{monto}}'}, {'{{fecha_vencimiento}}'}, etc.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Tabs para Email, Plantillas, Variables y Resumen */}
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
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Configuración Email
          </TabsTrigger>
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

        <TabsContent value="email" className="space-y-4">
          <EmailConfig />
        </TabsContent>

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

