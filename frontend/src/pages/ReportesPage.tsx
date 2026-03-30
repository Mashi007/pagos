import { useState } from 'react'

import { motion } from 'framer-motion'

import { BarChart3, FileText } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import { Button } from '../components/ui/button'

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

      <div className="grid gap-6 md:grid-cols-2">
        {/* Estado de Cuenta - Link Directo */}
        <Card className="border-emerald-200 hover:shadow-lg transition-shadow">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-emerald-600" />
                  Estado de Cuenta
                </CardTitle>
              </div>
              <Badge className="bg-emerald-600 hover:bg-emerald-700">
                Disponible
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-3">
                Accede a tu estado de cuenta, préstamos activos y cuotas pendientes. Genera PDF al instante.
              </p>

              <div className="space-y-2 text-sm text-muted-foreground mb-4">
                <p>✓ Consulta tu información financiera</p>

                <p>✓ Descarga estado de cuenta en PDF</p>

                <p>✓ Información disponible al instante</p>
              </div>
            </div>

            <Button
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              onClick={() => window.location.href = '/pagos/informes'}
            >
              Acceder a Informes
            </Button>
          </CardContent>
        </Card>

        {/* Reportes - Próximamente */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Reportes Avanzados
            </CardTitle>
          </CardHeader>

          <CardContent>
            <div className="py-8 text-center">
              <h3 className="mb-2 text-lg font-semibold">
                En Desarrollo
              </h3>

              <p className="mb-4 text-sm text-muted-foreground">
                Próximamente disponibles reportes avanzados con análisis detallado.
              </p>

              <div className="space-y-2 text-sm text-muted-foreground">
                <p>• Reportes PDF personalizados</p>

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
