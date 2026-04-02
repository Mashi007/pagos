import { Link } from 'react-router-dom'

import { FileText } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../ui/card'

import { Button } from '../../ui/button'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

export function ConfigAuditoriaTab() {
  return (
    <div className="space-y-6">
      <ConfigTabManualStrip note="La auditoría operativa se consulta manualmente en el módulo correspondiente.">
        <Button variant="default" size="sm" asChild>
          <Link to="/auditoria">
            <FileText className="mr-2 h-4 w-4" />
            Abrir auditoría
          </Link>
        </Button>
      </ConfigTabManualStrip>

      <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
        <div className="mb-2 flex items-center gap-2">
          <FileText className="h-5 w-5 text-purple-600" />

          <h3 className="font-semibold text-purple-900">Auditoría</h3>
        </div>

        <p className="text-sm text-purple-800">
          Esta pestaña no programa tareas ni temporizadores. Revise registros y
          acciones desde el módulo de auditoría cuando lo necesite.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5 text-blue-600" />
            Resumen
          </CardTitle>

          <CardDescription>
            Sin opciones automáticas en esta pantalla de configuración.
          </CardDescription>
        </CardHeader>

        <CardContent className="text-sm text-slate-600">
          Use el botón «Abrir auditoría» para cargar listados y filtros bajo
          demanda.
        </CardContent>
      </Card>
    </div>
  )
}
