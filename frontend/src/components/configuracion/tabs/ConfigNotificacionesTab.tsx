import { useState } from 'react'

import { Link } from 'react-router-dom'

import { Bell, RefreshCw } from 'lucide-react'

import { Input } from '../../ui/input'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../ui/card'

import { Button } from '../../ui/button'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

const DEFAULT_NOTIFICACIONES = {
  emailActivo: false,

  smsActivo: false,

  pushActivo: false,

  emailServidor: '',

  emailPuerto: 587,

  emailUsuario: '',

  smsProveedor: 'Twilio',
}

export function ConfigNotificacionesTab() {
  const [config, setConfig] = useState(DEFAULT_NOTIFICACIONES)

  const [demoKey, setDemoKey] = useState(0)

  const handleChange = (campo: string, valor: string | number | boolean) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }

  return (
    <div className="space-y-6">
      <ConfigTabManualStrip note="Envíos reales y plantillas: solo desde el módulo Notificaciones (manual).">
        <Button variant="default" size="sm" asChild>
          <Link to="/notificaciones?tab=configuracion">
            <Bell className="mr-2 h-4 w-4" />
            Abrir notificaciones (configuración real)
          </Link>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setConfig(DEFAULT_NOTIFICACIONES)
            setDemoKey(k => k + 1)
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Restablecer formulario de referencia
        </Button>
      </ConfigTabManualStrip>

      <div
        className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"
        role="status"
      >
        <p className="font-medium">Aviso</p>
        <p className="mt-1">
          Esta sección no guarda SMTP ni envíos. La configuración operativa
          (plantillas, PDFs y envío por caso, solo manual) está en{' '}
          <Link
            className="font-medium text-amber-950 underline"
            to="/notificaciones?tab=configuracion"
          >
            Notificaciones → Configuración
          </Link>
          ; el servidor de correo en Configuración → Email.
        </p>
      </div>

      <Card key={demoKey}>
        <CardHeader>
          <CardTitle className="text-base">Referencia local (no persiste)</CardTitle>
          <CardDescription>
            Sin horarios ni programación: los campos son solo demostración en el
            navegador.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.emailActivo}
                onChange={e => handleChange('emailActivo', e.target.checked)}
                className="rounded"
              />

              <label className="text-sm font-medium">
                Notificaciones por Email
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.smsActivo}
                onChange={e => handleChange('smsActivo', e.target.checked)}
                className="rounded"
              />

              <label className="text-sm font-medium">
                Notificaciones por SMS
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.pushActivo}
                onChange={e => handleChange('pushActivo', e.target.checked)}
                className="rounded"
              />

              <label className="text-sm font-medium">
                Notificaciones Push
              </label>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Servidor SMTP</label>

              <Input
                value={config.emailServidor}
                onChange={e => handleChange('emailServidor', e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Puerto SMTP</label>

              <Input
                type="number"
                value={config.emailPuerto}
                onChange={e =>
                  handleChange('emailPuerto', parseInt(e.target.value) || 0)
                }
                placeholder="587"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Usuario Email</label>

              <Input
                value={config.emailUsuario}
                onChange={e => handleChange('emailUsuario', e.target.value)}
                placeholder="noreply@empresa.com"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Proveedor SMS</label>

              <Select
                value={config.smsProveedor}
                onValueChange={v => handleChange('smsProveedor', v)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="Twilio">Twilio</SelectItem>

                  <SelectItem value="AWS_SNS">AWS SNS</SelectItem>

                  <SelectItem value="Local">Local</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
