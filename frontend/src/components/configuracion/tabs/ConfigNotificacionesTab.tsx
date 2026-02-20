import { useState } from 'react'
import { Input } from '../../ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card'

const DEFAULT_NOTIFICACIONES = {
  emailActivo: false,
  smsActivo: false,
  pushActivo: false,
  emailServidor: '',
  emailPuerto: 587,
  emailUsuario: '',
  smsProveedor: 'Twilio',
  horarioNotificaciones: '08:00-18:00',
}

export function ConfigNotificacionesTab() {
  const [config, setConfig] = useState(DEFAULT_NOTIFICACIONES)
  const handleChange = (campo: string, valor: string | number | boolean) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input type="checkbox" checked={config.emailActivo} onChange={(e) => handleChange('emailActivo', e.target.checked)} className="rounded" />
          <label className="text-sm font-medium">Notificaciones por Email</label>
        </div>
        <div className="flex items-center space-x-2">
          <input type="checkbox" checked={config.smsActivo} onChange={(e) => handleChange('smsActivo', e.target.checked)} className="rounded" />
          <label className="text-sm font-medium">Notificaciones por SMS</label>
        </div>
        <div className="flex items-center space-x-2">
          <input type="checkbox" checked={config.pushActivo} onChange={(e) => handleChange('pushActivo', e.target.checked)} className="rounded" />
          <label className="text-sm font-medium">Notificaciones Push</label>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Servidor SMTP</label>
          <Input value={config.emailServidor} onChange={(e) => handleChange('emailServidor', e.target.value)} placeholder="smtp.gmail.com" />
        </div>
        <div>
          <label className="text-sm font-medium">Puerto SMTP</label>
          <Input type="number" value={config.emailPuerto} onChange={(e) => handleChange('emailPuerto', parseInt(e.target.value) || 0)} placeholder="587" />
        </div>
        <div>
          <label className="text-sm font-medium">Usuario Email</label>
          <Input value={config.emailUsuario} onChange={(e) => handleChange('emailUsuario', e.target.value)} placeholder="noreply@empresa.com" />
        </div>
        <div>
          <label className="text-sm font-medium">Proveedor SMS</label>
          <Select value={config.smsProveedor} onValueChange={(v) => handleChange('smsProveedor', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="Twilio">Twilio</SelectItem>
              <SelectItem value="AWS_SNS">AWS SNS</SelectItem>
              <SelectItem value="Local">Local</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Horario de Notificaciones</label>
          <Input value={config.horarioNotificaciones} onChange={(e) => handleChange('horarioNotificaciones', e.target.value)} placeholder="08:00-18:00" />
        </div>
      </div>
    </div>
  )
}
