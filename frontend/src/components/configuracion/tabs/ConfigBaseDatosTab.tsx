import { useState } from 'react'

import { RefreshCw } from 'lucide-react'

import { Input } from '../../ui/input'

import { Button } from '../../ui/button'

import { formatDate } from '../../../utils'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

const DEFAULT_BASE_DATOS = {
  tipo: 'PostgreSQL',

  version: '15',

  retencionBackup: 30,

  ultimoBackup: new Date().toISOString(),
}

export function ConfigBaseDatosTab() {
  const [config, setConfig] = useState(DEFAULT_BASE_DATOS)

  return (
    <div className="space-y-6">
      <ConfigTabManualStrip note="Vista de referencia: backups programados no se configuran aquí (solo manual en infraestructura).">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setConfig(DEFAULT_BASE_DATOS)}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Restablecer vista de ejemplo
        </Button>
      </ConfigTabManualStrip>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        No hay programación de backups ni temporizadores en esta pantalla. Los
        valores son ilustrativos en el navegador.
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Tipo de Base de Datos</label>

          <Input value={config.tipo} disabled className="bg-gray-100" />
        </div>

        <div>
          <label className="text-sm font-medium">Versión</label>

          <Input value={config.version} disabled className="bg-gray-100" />
        </div>

        <div>
          <label className="text-sm font-medium">
            Retención referencial (días)
          </label>

          <Input
            type="number"
            value={config.retencionBackup}
            onChange={e =>
              setConfig(prev => ({
                ...prev,
                retencionBackup: parseInt(e.target.value) || 0,
              }))
            }
            placeholder="30"
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium">Último backup (ejemplo)</label>

        <Input
          value={formatDate(config.ultimoBackup)}
          disabled
          className="bg-gray-100"
        />
      </div>
    </div>
  )
}
