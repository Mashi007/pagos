import { FileText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card'

export function ConfigAuditoriaTab() {
  return (
    <div className="space-y-6">
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-5 w-5 text-purple-600" />
          <h3 className="font-semibold text-purple-900">Auditoría del Sistema</h3>
        </div>
        <p className="text-sm text-purple-700">
          Registro y seguimiento de todas las actividades del sistema para cumplimiento y seguridad.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Configuración de Auditoría
          </CardTitle>
          <CardDescription>Configura qué eventos se registran en el sistema de auditoría</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Auditoría de Usuarios</h4>
              <p className="text-sm text-gray-600">Registra login, logout y cambios de perfil</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={true} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Auditoría de Transacciones</h4>
              <p className="text-sm text-gray-600">Registra todos los movimientos financieros</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={true} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div>
              <h4 className="font-medium">Auditoría de Configuración</h4>
              <p className="text-sm text-gray-600">Registra cambios en configuraciones del sistema</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input type="checkbox" checked={true} className="sr-only peer toggle-input-peer" />
              <div className="toggle-switch-track"></div>
            </label>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
