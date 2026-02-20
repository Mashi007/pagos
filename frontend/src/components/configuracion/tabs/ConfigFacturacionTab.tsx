import { useState } from 'react'
import { Input } from '../../ui/input'

const DEFAULT_FACTURACION = {
  tasaInteres: 12.5,
  tasaMora: 24.0,
  diasGracia: 5,
  montoMinimo: 5000,
  montoMaximo: 50000,
  plazoMinimo: 12,
  plazoMaximo: 60,
  cuotaInicialMinima: 10,
}

export function ConfigFacturacionTab() {
  const [config, setConfig] = useState(DEFAULT_FACTURACION)
  const handleChange = (campo: string, valor: number) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Tasa de Interés Anual (%)</label>
          <Input type="number" step="0.1" value={config.tasaInteres} onChange={(e) => handleChange('tasaInteres', parseFloat(e.target.value) || 0)} placeholder="12.5" />
        </div>
        <div>
          <label className="text-sm font-medium">Tasa de Mora Anual (%)</label>
          <Input type="number" step="0.1" value={config.tasaMora} onChange={(e) => handleChange('tasaMora', parseFloat(e.target.value) || 0)} placeholder="24.0" />
        </div>
        <div>
          <label className="text-sm font-medium">Días de Gracia</label>
          <Input type="number" value={config.diasGracia} onChange={(e) => handleChange('diasGracia', parseInt(e.target.value) || 0)} placeholder="5" />
        </div>
        <div>
          <label className="text-sm font-medium">Monto Mínimo</label>
          <Input type="number" value={config.montoMinimo} onChange={(e) => handleChange('montoMinimo', parseInt(e.target.value) || 0)} placeholder="5000" />
        </div>
        <div>
          <label className="text-sm font-medium">Monto Máximo</label>
          <Input type="number" value={config.montoMaximo} onChange={(e) => handleChange('montoMaximo', parseInt(e.target.value) || 0)} placeholder="50000" />
        </div>
        <div>
          <label className="text-sm font-medium">Plazo Mínimo (meses)</label>
          <Input type="number" value={config.plazoMinimo} onChange={(e) => handleChange('plazoMinimo', parseInt(e.target.value) || 0)} placeholder="12" />
        </div>
        <div>
          <label className="text-sm font-medium">Plazo Máximo (meses)</label>
          <Input type="number" value={config.plazoMaximo} onChange={(e) => handleChange('plazoMaximo', parseInt(e.target.value) || 0)} placeholder="60" />
        </div>
        <div>
          <label className="text-sm font-medium">Cuota Inicial Mínima (%)</label>
          <Input type="number" value={config.cuotaInicialMinima} onChange={(e) => handleChange('cuotaInicialMinima', parseInt(e.target.value) || 0)} placeholder="10" />
        </div>
      </div>
    </div>
  )
}
