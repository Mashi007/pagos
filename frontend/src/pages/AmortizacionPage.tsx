import { useState } from 'react'
import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function AmortizacionPage() {
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
          <h1 className="text-3xl font-bold tracking-tight">Amortización</h1>
          <p className="text-muted-foreground">
            Tablas de amortización y cálculos
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
            <CardTitle>Amortización</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <div className="text-6xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2">Página en Desarrollo</h3>
              <p className="text-muted-foreground mb-4">
                Esta funcionalidad está siendo implementada y estará disponible próximamente.
              </p>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Generación de tablas</p>
                <p>• Cálculos automáticos</p>
                <p>• Visualización de cronogramas</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}
