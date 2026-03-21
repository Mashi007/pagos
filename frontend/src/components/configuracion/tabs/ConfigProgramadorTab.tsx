import { Calendar, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card'

export function ConfigProgramadorTab() {
  return (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Calendar className="h-5 w-5 text-green-600" />
          <h3 className="font-semibold text-green-900">Programador de Tareas</h3>
        </div>
        <p className="text-sm text-green-700">
          Configura tareas automÃ¡ticas, recordatorios y procesos programados del sistema.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-600" />
            Tareas Programadas
          </CardTitle>
          <CardDescription>ConfiguraciÃ³n de tareas automÃ¡ticas del sistema</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Recordatorios de Pago</h4>
              <p className="text-sm text-gray-600">EnvÃ­o automÃ¡tico de recordatorios antes del vencimiento</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={true} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Backup AutomÃ¡tico</h4>
              <p className="text-sm text-gray-600">Respaldo automÃ¡tico de la base de datos</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={true} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Reportes AutomÃ¡ticos</h4>
              <p className="text-sm text-gray-600">GeneraciÃ³n y envÃ­o automÃ¡tico de reportes</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={false} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
