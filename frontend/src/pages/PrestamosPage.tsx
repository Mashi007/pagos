import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useSimpleAuth } from '@/store/simpleAuthStore'

export function PrestamosPage() {
  const { user } = useSimpleAuth()
  const hasAnyRole = () => true // Todos tienen acceso completo
  const [loading, setLoading] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Préstamos</h1>
          <p className="text-muted-foreground">
            Gestión de préstamos y financiamientos
          </p>
        </div>
        <Badge variant="outline" className="text-sm">
          En Desarrollo
        </Badge>
      </div>

      {/* Contenido Principal */}
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Préstamos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-6xl mb-4">🚧</div>
              <h3 className="text-xl font-semibold mb-2">Página en Desarrollo</h3>
              <p className="text-muted-foreground mb-4">
                Esta funcionalidad está siendo implementada y estará disponible próximamente.
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Funcionalidades básicas implementadas</p>
                <p>• Integración con backend en progreso</p>
                <p>• Pruebas de usuario pendientes</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Cards de información */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Estado</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge variant="secondary">En Desarrollo</Badge>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Progreso</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{width: '60%'}}></div>
              </div>
              <p className="text-sm text-muted-foreground mt-2">60% completado</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Próxima Actualización</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">Próximamente</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  )
}
