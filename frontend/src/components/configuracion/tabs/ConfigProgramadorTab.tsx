import { Calendar, Clock } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../ui/card'

export function ConfigProgramadorTab() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-green-200 bg-green-50 p-4">
        <div className="mb-2 flex items-center gap-2">
          <Calendar className="h-5 w-5 text-green-600" />

          <h3 className="font-semibold text-green-900">
            Programador de Tareas
          </h3>
        </div>

        <p className="text-sm text-green-700">
          Configura tareas automáticas, recordatorios y procesos programados del
          sistema.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Clock className="h-5 w-5 text-blue-600" />
            Tareas Programadas
          </CardTitle>

          <CardDescription>
            Configuración de tareas automáticas del sistema
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <h4 className="font-medium">Recordatorios de Pago</h4>

              <p className="text-sm text-gray-600">
                Envío automático de recordatorios antes del vencimiento
              </p>
            </div>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={true}
                className="toggle-input-peer peer sr-only"
              />

              <div className="toggle-switch-track"></div>
            </label>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <h4 className="font-medium">Backup Automático</h4>

              <p className="text-sm text-gray-600">
                Respaldo automático de la base de datos
              </p>
            </div>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={true}
                className="toggle-input-peer peer sr-only"
              />

              <div className="toggle-switch-track"></div>
            </label>
          </div>

          <div className="flex items-center justify-between rounded-lg border p-3">
            <div>
              <h4 className="font-medium">Reportes Automáticos</h4>

              <p className="text-sm text-gray-600">
                Generación y envío automático de reportes
              </p>
            </div>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={false}
                className="toggle-input-peer peer sr-only"
              />

              <div className="toggle-switch-track"></div>
            </label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
