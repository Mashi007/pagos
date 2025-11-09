import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmailConfig } from '@/components/configuracion/EmailConfig'
import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Mail, FileText, Settings } from 'lucide-react'

export function ConfiguracionNotificaciones() {
  const [activeTab, setActiveTab] = useState('email')

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

      {/* Tabs para Email y Plantillas */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="email" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Configuración Email
          </TabsTrigger>
          <TabsTrigger value="plantillas" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Plantillas
          </TabsTrigger>
        </TabsList>

        <TabsContent value="email" className="space-y-4">
          <EmailConfig />
        </TabsContent>

        <TabsContent value="plantillas" className="space-y-4">
          <PlantillasNotificaciones />
        </TabsContent>
      </Tabs>
    </div>
  )
}

