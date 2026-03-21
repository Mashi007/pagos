import { useState } from 'react'

import { motion } from 'framer-motion'

import { BarChart3 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

export function ReportesPage() {
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
          <h1 className="text-3xl font-bold tracking-tight">Reportes</h1>

          <p className="text-muted-foreground">
            Generación de reportes y análisis
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
            <CardTitle>Reportes</CardTitle>
          </CardHeader>

          <CardContent>
            <div className="py-8 text-center">
              <div className="mb-4 flex justify-center">
                <BarChart3 className="h-16 w-16 text-muted-foreground" />
              </div>

              <h3 className="mb-2 text-xl font-semibold">
                Página en Desarrollo
              </h3>

              <p className="mb-4 text-muted-foreground">
                Esta funcionalidad está siendo implementada y estará disponible
                próximamente.
              </p>

              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Reportes PDF</p>

                <p>• Análisis de datos</p>

                <p>• Exportación Excel</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}

export default ReportesPage
