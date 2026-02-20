import { useState } from 'react'
import { Input } from '../../ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { formatDate } from '../../../utils'

const DEFAULT_BASE_DATOS = {
  tipo: 'PostgreSQL',
  version: '15',
  frecuenciaBackup: 'DIARIO',
  horaBackup: '02:00',
  retencionBackup: 30,
  backupAutomatico: true,
  compresionBackup: true,
  ultimoBackup: new Date().toISOString(),
}

export function ConfigBaseDatosTab() {
  const [config, setConfig] = useState(DEFAULT_BASE_DATOS)
  const handleChange = (campo: string, valor: string | number | boolean) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }
  return (
    <div className="space-y-6">
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
          <label className="text-sm font-medium">Frecuencia de Backup</label>
          <Select value={config.frecuenciaBackup} onValueChange={(v) => handleChange('frecuenciaBackup', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="DIARIO">Diario</SelectItem>
              <SelectItem value="SEMANAL">Semanal</SelectItem>
              <SelectItem value="MENSUAL">Mensual</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Hora de Backup</label>
          <Input type="time" value={config.horaBackup} onChange={(e) => handleChange('horaBackup', e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium">Retención (días)</label>
          <Input type="number" value={config.retencionBackup} onChange={(e) => handleChange('retencionBackup', parseInt(e.target.value) || 0)} placeholder="30" />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input type="checkbox" checked={config.backupAutomatico} onChange={(e) => handleChange('backupAutomatico', e.target.checked)} className="rounded" />
          <label className="text-sm font-medium">Backup Automático</label>
        </div>
        <div className="flex items-center space-x-2">
          <input type="checkbox" checked={config.compresionBackup} onChange={(e) => handleChange('compresionBackup', e.target.checked)} className="rounded" />
          <label className="text-sm font-medium">Comprimir Backups</label>
        </div>
      </div>
      <div>
        <label className="text-sm font-medium">Último Backup</label>
        <Input value={formatDate(config.ultimoBackup)} disabled className="bg-gray-100" />
      </div>
    </div>
  )
}
