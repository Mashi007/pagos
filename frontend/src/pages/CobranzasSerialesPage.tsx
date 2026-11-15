/**
 * Cobranzas → Seriales (solo itmaster@).
 * Pestaña «Revisión por cédula» (SerialesRevisionCedula) y pestaña «Carga masiva»
 * de 5 en 5 con aprobación por préstamo (SerialesCargaMasiva).
 */
import { useState } from 'react'
import { FileSpreadsheet } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { SerialesRevisionCedula } from '../components/cobranzas/SerialesRevisionCedula'
import { SerialesCargaMasiva } from '../components/cobranzas/SerialesCargaMasiva'

export function CobranzasSerialesPage() {
  const [tab, setTab] = useState('revision')
  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Seriales"
        description="Carga depósitos Mercantil a préstamos con cuotas atrasadas. Revisión por cédula: eliges a mano los depósitos de cada mes. Carga masiva: simula de 5 en 5 y apruebas los préstamos."
        icon={FileSpreadsheet}
      />
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="revision">Revisión por cédula</TabsTrigger>
          <TabsTrigger value="masiva">Carga masiva</TabsTrigger>
        </TabsList>
        <TabsContent value="revision" forceMount className="mt-4">
          <SerialesRevisionCedula />
        </TabsContent>
        <TabsContent value="masiva" forceMount className="mt-4">
          <SerialesCargaMasiva />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default CobranzasSerialesPage
