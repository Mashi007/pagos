import { useState, useEffect } from 'react'
import { Mail, Save, TestTube, CheckCircle, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { emailConfigService } from '@/services/notificacionService'

interface EmailConfigData {
  smtp_host: string
  smtp_port: string
  smtp_user: string
  smtp_password?: string
  from_email: string
  from_name: string
  smtp_use_tls: string
}

export function EmailConfig() {
  const [config, setConfig] = useState<EmailConfigData>({
    smtp_host: 'smtp.gmail.com',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    from_name: 'RapiCredit',
    smtp_use_tls: 'true'
  })
  
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [probando, setProbando] = useState(false)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEmail()
      setConfig(data)
    } catch (error) {
      console.error('Error cargando configuración de email:', error)
      toast.error('Error cargando configuración')
    }
  }

  const handleChange = (campo: keyof EmailConfigData, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    try {
      setGuardando(true)
      await emailConfigService.actualizarConfiguracionEmail(config)
      toast.success('Configuración de email guardada exitosamente')
    } catch (error) {
      console.error('Error guardando configuración:', error)
      toast.error('Error guardando configuración')
    } finally {
      setGuardando(false)
    }
  }

  const handleProbar = async () => {
    try {
      setProbando(true)
      setResultadoPrueba(null)
      
      const resultado = await emailConfigService.probarConfiguracionEmail()
      setResultadoPrueba(resultado)
      
      if (resultado.mensaje?.includes('enviado')) {
        toast.success('Email de prueba enviado exitosamente')
      } else {
        toast.error('Error enviando email de prueba')
      }
    } catch (error) {
      console.error('Error probando configuración:', error)
      toast.error('Error probando configuración')
      setResultadoPrueba({ error: 'Error desconocido' })
    } finally {
      setProbando(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Información */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Mail className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-blue-900">Configuración de Email</h3>
        </div>
        <p className="text-sm text-blue-700">
          Configura el servidor SMTP para enviar notificaciones por email a los clientes.
        </p>
      </div>

      {/* Configuración SMTP */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            Configuración SMTP (Gmail)
          </CardTitle>
          <CardDescription>
            Ingresa tus credenciales de Gmail para enviar notificaciones
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Servidor SMTP</label>
              <Input
                value={config.smtp_host}
                onChange={(e) => handleChange('smtp_host', e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Puerto SMTP</label>
              <Input
                value={config.smtp_port}
                onChange={(e) => handleChange('smtp_port', e.target.value)}
                placeholder="587"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Email (Usuario Gmail)</label>
              <Input
                type="email"
                value={config.smtp_user}
                onChange={(e) => handleChange('smtp_user', e.target.value)}
                placeholder="tu-email@gmail.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Contraseña de Aplicación</label>
              <div className="relative">
                <Input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={config.smtp_password || ''}
                  onChange={(e) => handleChange('smtp_password', e.target.value)}
                  placeholder="App Password de Gmail"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setMostrarPassword(!mostrarPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {mostrarPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Genera una App Password en tu cuenta de Google
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Email del Remitente</label>
              <Input
                type="email"
                value={config.from_email}
                onChange={(e) => handleChange('from_email', e.target.value)}
                placeholder="tu-email@gmail.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Nombre del Remitente</label>
              <Input
                value={config.from_name}
                onChange={(e) => handleChange('from_name', e.target.value)}
                placeholder="RapiCredit"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={config.smtp_use_tls === 'true'}
              onChange={(e) => handleChange('smtp_use_tls', e.target.checked ? 'true' : 'false')}
              className="rounded"
            />
            <label className="text-sm font-medium">Usar TLS (Recomendado para Gmail)</label>
          </div>

          {/* Botones */}
          <div className="flex gap-2 pt-4">
            <Button
              onClick={handleGuardar}
              disabled={guardando}
              className="flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {guardando ? 'Guardando...' : 'Guardar Configuración'}
            </Button>
            
            <Button
              onClick={handleProbar}
              disabled={probando || !config.smtp_user}
              variant="outline"
              className="flex items-center gap-2"
            >
              <TestTube className="h-4 w-4" />
              {probando ? 'Probando...' : 'Probar Configuración'}
            </Button>
          </div>

          {/* Resultado de la prueba */}
          {resultadoPrueba && (
            <div className={`p-4 rounded-lg border ${
              resultadoPrueba.mensaje?.includes('enviado') 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-start gap-2">
                {resultadoPrueba.mensaje?.includes('enviado') ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${
                    resultadoPrueba.mensaje?.includes('enviado') ? 'text-green-900' : 'text-red-900'
                  }`}>
                    {resultadoPrueba.mensaje}
                  </p>
                  {resultadoPrueba.error && (
                    <p className="text-sm text-red-600 mt-1">{resultadoPrueba.error}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Instrucciones */}
      <Card>
        <CardHeader>
          <CardTitle>📝 Instrucciones para Gmail</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="border-l-4 border-blue-500 pl-4">
            <p className="font-semibold mb-2">Para obtener una Contraseña de Aplicación:</p>
            <ol className="list-decimal ml-5 space-y-1">
              <li>Ve a tu cuenta de Google: https://myaccount.google.com/</li>
              <li>Selecciona <strong>Seguridad</strong></li>
              <li>Activa la <strong>Verificación en 2 pasos</strong> si no está activada</li>
              <li>Busca <strong>Contraseñas de aplicaciones</strong></li>
              <li>Selecciona <strong>Correo</strong> y el dispositivo</li>
              <li>Genera y copia la contraseña de 16 caracteres</li>
              <li>Pégala en el campo "Contraseña de Aplicación"</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


