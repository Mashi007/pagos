import { useSearchParams } from 'react-router-dom'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { EmbudoClientes } from './EmbudoClientes'
import { EmbudoConcesionarios } from './EmbudoConcesionarios'
import { Store } from 'lucide-react'

export function Ventas() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const defaultTab = tabParam === 'seguimiento-concesionarios' ? 'seguimiento-concesionarios' : 'venta-servicios'

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 mb-4">
        <Store className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Ventas</h1>
      </div>

      <Tabs value={defaultTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="venta-servicios" className="flex items-center gap-2">
            Venta Servicios
          </TabsTrigger>
          <TabsTrigger value="seguimiento-concesionarios" className="flex items-center gap-2">
            Seguimiento Concesionarios
          </TabsTrigger>
        </TabsList>

        <TabsContent value="venta-servicios" className="mt-6">
          <EmbudoClientes />
        </TabsContent>

        <TabsContent value="seguimiento-concesionarios" className="mt-6">
          <EmbudoConcesionarios />
        </TabsContent>
      </Tabs>
    </div>
  )
}

