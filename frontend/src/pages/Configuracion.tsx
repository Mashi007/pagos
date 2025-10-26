import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Settings,
  Save,
  RefreshCw,
  Bell,
  Mail,
  Shield,
  Database,
  Globe,
  Users,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  Eye,
  EyeOff,
  CheckSquare,
  Building,
  Brain,
  Wrench,
  Calendar,
  FileText,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDate } from '@/utils'
import { ValidadoresConfig } from '@/components/configuracion/ValidadoresConfig'
import { ConcesionariosConfig } from '@/components/configuracion/ConcesionariosConfig'
import { AnalistasConfig } from '@/components/configuracion/AnalistasConfig'
import { configuracionGeneralService, ConfiguracionGeneral } from '@/services/configuracionGeneralService'
import { logoService } from '@/services/logoService'
import { toast } from 'sonner'
import UsuariosConfig from '@/components/configuracion/UsuariosConfig'

// Mock data para configuración
const mockConfiguracion = {
  general: {
    nombreEmpresa: 'RAPICREDIT',
    version: '1.0.0',
    idioma: 'ES',
    zonaHoraria: 'America/Caracas',
    moneda: 'VES',
    ultimaActualizacion: '2024-07-20T10:00:00Z',
  },
  notificaciones: {
    emailActivo: true,
    smsActivo: true,
    pushActivo: true,
    emailServidor: 'smtp.gmail.com',
    emailPuerto: 587,
    emailUsuario: 'noreply@rapicredit.com',
    smsProveedor: 'Twilio',
    horarioNotificaciones: '08:00-18:00',
    diasNotificacion: ['LUN', 'MAR', 'MIE', 'JUE', 'VI'],
  },
  seguridad: {
    sessionTimeout: 30,
    intentosLogin: 3,
    bloqueoTemporal: 15,
    requiere2FA: false,
    politicaContraseñas: 'ALTA',
    auditoriaActiva: true,
    ipWhitelist: false,
    sslActivo: true,
  },
  baseDatos: {
    tipo: 'PostgreSQL',
    version: '13.7',
    backupAutomatico: true,
    frecuenciaBackup: 'DIARIO',
    horaBackup: '02:00',
    retencionBackup: 30,
    compresionBackup: true,
    ultimoBackup: '2024-07-20T02:00:00Z',
  },
  integraciones: {
    apiActiva: true,
    versionAPI: 'v1',
    rateLimit: 1000,
    webhooksActivos: true,
    loggingActivo: true,
    metricaActiva: true,
    alertasActivas: true,
  },
  facturacion: {
    tasaInteres: 12.5,
    tasaMora: 24.0,
    diasGracia: 5,
    montoMinimo: 5000,
    montoMaximo: 50000,
    plazoMinimo: 12,
    plazoMaximo: 60,
    cuotaInicialMinima: 10,
  },
  inteligenciaArtificial: {
    openaiApiKey: '',
    openaiModel: 'gpt-3.5-turbo',
    aiScoringEnabled: true,
    aiPredictionEnabled: true,
    aiChatbotEnabled: true
  },
}

export function Configuracion() {
  const [configuracion, setConfiguracion] = useState(mockConfiguracion)
  const [configuracionGeneral, setConfiguracionGeneral] = useState<ConfiguracionGeneral | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seccionActiva, setSeccionActiva] = useState('general')
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [cambiosPendientes, setCambiosPendientes] = useState(false)
  const [submenuAbierto, setSubmenuAbierto] = useState(false)
  const [logo, setLogo] = useState<string | null>(null)

  // Cargar configuración general al montar el componente
  useEffect(() => {
    cargarConfiguracionGeneral()
    cargarLogo()
  }, [])

  const cargarLogo = async () => {
    try {
      const logoUrl = await logoService.obtenerLogo()
      if (logoUrl) {
        setLogo(logoUrl)
      }
    } catch (error) {
      console.error('Error cargando logo:', error)
    }
  }

  const cargarConfiguracionGeneral = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('🔄 Cargando configuración general...')
      
      const config = await configuracionGeneralService.obtenerConfiguracionGeneral()
      console.log('✅ Configuración general cargada:', config)
      
      setConfiguracionGeneral(config)
      
      // Actualizar también el mock para compatibilidad
      setConfiguracion(prev => ({
        ...prev,
        general: {
          ...prev.general,
          nombreEmpresa: config.nombre_empresa,
          version: config.version_sistema,
          idioma: config.idioma,
          zonaHoraria: config.zona_horaria,
          moneda: config.moneda
        }
      }))
    } catch (err) {
      console.error('❌ Error cargando configuración general:', err)
      setError('Error al cargar configuración general')
      // Usar datos mock como fallback
    } finally {
      setLoading(false)
    }
  }

  const actualizarConfiguracionGeneral = async (campo: string, valor: string) => {
    try {
      setLoading(true)
      setError(null)
      
      console.log(`🔄 Actualizando ${campo} a:`, valor)
      
      const updateData = { [campo]: valor }
      const response = await configuracionGeneralService.actualizarConfiguracionGeneral(updateData)
      
      console.log('✅ Configuración actualizada:', response)
      
      // Actualizar estado local
      setConfiguracionGeneral(prev => prev ? { ...prev, [campo]: valor } : null)
      setConfiguracion(prev => ({
        ...prev,
        general: {
          ...prev.general,
          [campo]: valor
        }
      }))
      
      // Mostrar mensaje de éxito
      toast.success(`${campo} actualizado exitosamente`)
      
    } catch (err) {
      console.error('❌ Error actualizando configuración:', err)
      setError(`Error al actualizar ${campo}`)
      toast.error(`Error al actualizar ${campo}`)
    } finally {
      setLoading(false)
    }
  }

  const secciones = [
    { id: 'general', nombre: 'General', icono: Globe },
    { 
      id: 'herramientas', 
      nombre: 'Herramientas', 
      icono: Wrench, 
      submenu: true,
      items: [
        { id: 'notificaciones', nombre: 'Notificaciones', icono: Bell },
        { id: 'programador', nombre: 'Programador', icono: Calendar },
        { id: 'auditoria', nombre: 'Auditoría', icono: FileText },
      ]
    },
    // { id: 'seguridad', nombre: 'Seguridad', icono: Shield }, // OCULTO - No necesario por ahora
    { id: 'baseDatos', nombre: 'Base de Datos', icono: Database },
    // { id: 'integraciones', nombre: 'Integraciones', icono: Settings }, // OCULTO
    { id: 'facturacion', nombre: 'Facturación', icono: DollarSign },
    { id: 'inteligenciaArtificial', nombre: 'Inteligencia Artificial', icono: Brain },
    { id: 'validadores', nombre: 'Validadores', icono: CheckSquare },
    { id: 'concesionarios', nombre: 'Concesionarios', icono: Building },
    { id: 'analistaes', nombre: 'Asesores', icono: Users },
    { id: 'usuarios', nombre: 'Usuarios', icono: Users },
  ]

  const handleGuardar = () => {
    console.log('Guardando configuración...', configuracion)
    setCambiosPendientes(false)
    // Lógica para guardar configuración
  }

  const handleCambio = (seccion: string, campo: string, valor: any) => {
    console.log(`🔄 Cambio en ${seccion}.${campo}:`, valor)
    
    setConfiguracion(prev => ({
      ...prev,
      [seccion]: {
        ...prev[seccion as keyof typeof prev],
        [campo]: valor
      }
    }))
    
    setCambiosPendientes(true)
    
    // Si es configuración general, actualizar también en el backend
    if (seccion === 'general') {
      actualizarConfiguracionGeneral(campo, valor)
    }
  }

  const renderSeccionGeneral = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Nombre de la Empresa</label>
          <Input
            value={configuracion.general.nombreEmpresa}
            onChange={(e) => handleCambio('general', 'nombreEmpresa', e.target.value)}
            placeholder="Nombre de la empresa"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Versión del Sistema</label>
          <Input
            value={configuracion.general.version}
            disabled
            className="bg-gray-100"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Idioma</label>
          <Select value={configuracion.general.idioma} onValueChange={(value: string) => handleCambio('general', 'idioma', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ES">Español</SelectItem>
              <SelectItem value="EN">English</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Zona Horaria</label>
          <Select value={configuracion.general.zonaHoraria} onValueChange={(value: string) => handleCambio('general', 'zonaHoraria', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="America/Caracas">Caracas (UTC-4)</SelectItem>
              <SelectItem value="America/New_York">New York (UTC-5)</SelectItem>
              <SelectItem value="America/Los_Angeles">Los Angeles (UTC-8)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Moneda</label>
          <Select value={configuracion.general.moneda} onValueChange={(value: string) => handleCambio('general', 'moneda', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="VES">Bolívar Soberano (VES)</SelectItem>
              <SelectItem value="USD">Dólar Americano (USD)</SelectItem>
              <SelectItem value="EUR">Euro (EUR)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Logo de la Empresa</label>
          <div className="space-y-4">
            {logo ? (
              <div className="flex items-center space-x-4">
                <img src={logo} alt="Logo" className="w-16 h-16 object-contain border rounded-lg p-2" />
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={async () => {
                    try {
                      await logoService.eliminarLogo()
                      setLogo(null)
                      toast.success('Logo eliminado exitosamente')
                    } catch (error) {
                      console.error('Error eliminando logo:', error)
                      toast.error('Error al eliminar logo')
                    }
                  }}
                >
                  Eliminar
                </Button>
              </div>
            ) : (
              <div>
                <Input
                  type="file"
                  accept="image/*"
                  onChange={async (e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      try {
                        await logoService.subirLogo(file)
                        const logoUrl = await logoService.obtenerLogo()
                        if (logoUrl) {
                          setLogo(logoUrl)
                        }
                        toast.success('Logo cargado exitosamente')
                      } catch (error) {
                        console.error('Error subiendo logo:', error)
                        toast.error('Error al cargar logo')
                      }
                    }
                  }}
                  className="cursor-pointer"
                />
                <p className="text-xs text-gray-500 mt-1">Formatos permitidos: PNG, JPG, SVG</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  const renderSeccionNotificaciones = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.notificaciones.emailActivo}
            onChange={(e) => handleCambio('notificaciones', 'emailActivo', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Notificaciones por Email</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.notificaciones.smsActivo}
            onChange={(e) => handleCambio('notificaciones', 'smsActivo', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Notificaciones por SMS</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.notificaciones.pushActivo}
            onChange={(e) => handleCambio('notificaciones', 'pushActivo', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Notificaciones Push</label>
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Servidor SMTP</label>
          <Input
            value={configuracion.notificaciones.emailServidor}
            onChange={(e) => handleCambio('notificaciones', 'emailServidor', e.target.value)}
            placeholder="smtp.gmail.com"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Puerto SMTP</label>
          <Input
            type="number"
            value={configuracion.notificaciones.emailPuerto}
            onChange={(e) => handleCambio('notificaciones', 'emailPuerto', parseInt(e.target.value))}
            placeholder="587"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Usuario Email</label>
          <Input
            value={configuracion.notificaciones.emailUsuario}
            onChange={(e) => handleCambio('notificaciones', 'emailUsuario', e.target.value)}
            placeholder="noreply@empresa.com"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Proveedor SMS</label>
          <Select value={configuracion.notificaciones.smsProveedor} onValueChange={(value: string) => handleCambio('notificaciones', 'smsProveedor', value)}>
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
        <div>
          <label className="text-sm font-medium">Horario de Notificaciones</label>
          <Input
            value={configuracion.notificaciones.horarioNotificaciones}
            onChange={(e) => handleCambio('notificaciones', 'horarioNotificaciones', e.target.value)}
            placeholder="08:00-18:00"
          />
        </div>
      </div>
    </div>
  )

  const renderSeccionSeguridad = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Timeout de Sesión (minutos)</label>
          <Input
            type="number"
            value={configuracion.seguridad.sessionTimeout}
            onChange={(e) => handleCambio('seguridad', 'sessionTimeout', parseInt(e.target.value))}
            placeholder="30"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Intentos de Login</label>
          <Input
            type="number"
            value={configuracion.seguridad.intentosLogin}
            onChange={(e) => handleCambio('seguridad', 'intentosLogin', parseInt(e.target.value))}
            placeholder="3"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Bloqueo Temporal (minutos)</label>
          <Input
            type="number"
            value={configuracion.seguridad.bloqueoTemporal}
            onChange={(e) => handleCambio('seguridad', 'bloqueoTemporal', parseInt(e.target.value))}
            placeholder="15"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Política de Contraseñas</label>
          <Select value={configuracion.seguridad.politicaContraseñas} onValueChange={(value: string) => handleCambio('seguridad', 'politicaContraseñas', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="BAJA">Baja</SelectItem>
              <SelectItem value="MEDIA">Media</SelectItem>
              <SelectItem value="ALTA">Alta</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.seguridad.requiere2FA}
            onChange={(e) => handleCambio('seguridad', 'requiere2FA', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Requerir Autenticación de Dos Factores</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.seguridad.auditoriaActiva}
            onChange={(e) => handleCambio('seguridad', 'auditoriaActiva', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Auditoría Activa</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.seguridad.ipWhitelist}
            onChange={(e) => handleCambio('seguridad', 'ipWhitelist', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Lista Blanca de IPs</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.seguridad.sslActivo}
            onChange={(e) => handleCambio('seguridad', 'sslActivo', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">SSL Activo</label>
        </div>
      </div>
    </div>
  )

  const renderSeccionBaseDatos = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Tipo de Base de Datos</label>
          <Input
            value={configuracion.baseDatos.tipo}
            disabled
            className="bg-gray-100"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Versión</label>
          <Input
            value={configuracion.baseDatos.version}
            disabled
            className="bg-gray-100"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Frecuencia de Backup</label>
          <Select value={configuracion.baseDatos.frecuenciaBackup} onValueChange={(value: string) => handleCambio('baseDatos', 'frecuenciaBackup', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="DIARIO">Diario</SelectItem>
              <SelectItem value="SEMANAL">Semanal</SelectItem>
              <SelectItem value="MENSUAL">Mensual</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Hora de Backup</label>
          <Input
            type="time"
            value={configuracion.baseDatos.horaBackup}
            onChange={(e) => handleCambio('baseDatos', 'horaBackup', e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Retención (días)</label>
          <Input
            type="number"
            value={configuracion.baseDatos.retencionBackup}
            onChange={(e) => handleCambio('baseDatos', 'retencionBackup', parseInt(e.target.value))}
            placeholder="30"
          />
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.baseDatos.backupAutomatico}
            onChange={(e) => handleCambio('baseDatos', 'backupAutomatico', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Backup Automático</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.baseDatos.compresionBackup}
            onChange={(e) => handleCambio('baseDatos', 'compresionBackup', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Comprimir Backups</label>
        </div>
      </div>
      
      <div>
        <label className="text-sm font-medium">Último Backup</label>
        <Input
          value={formatDate(configuracion.baseDatos.ultimoBackup)}
          disabled
          className="bg-gray-100"
        />
      </div>
    </div>
  )

  const renderSeccionIntegraciones = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Versión de API</label>
          <Input
            value={configuracion.integraciones.versionAPI}
            onChange={(e) => handleCambio('integraciones', 'versionAPI', e.target.value)}
            placeholder="v1"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Rate Limit (requests/hora)</label>
          <Input
            type="number"
            value={configuracion.integraciones.rateLimit}
            onChange={(e) => handleCambio('integraciones', 'rateLimit', parseInt(e.target.value))}
            placeholder="1000"
          />
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.integraciones.apiActiva}
            onChange={(e) => handleCambio('integraciones', 'apiActiva', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">API Activa</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.integraciones.webhooksActivos}
            onChange={(e) => handleCambio('integraciones', 'webhooksActivos', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Webhooks Activos</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.integraciones.loggingActivo}
            onChange={(e) => handleCambio('integraciones', 'loggingActivo', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Logging Activo</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.integraciones.metricaActiva}
            onChange={(e) => handleCambio('integraciones', 'metricaActiva', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Métricas Activas</label>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={configuracion.integraciones.alertasActivas}
            onChange={(e) => handleCambio('integraciones', 'alertasActivas', e.target.checked)}
            className="rounded"
          />
          <label className="text-sm font-medium">Alertas Activas</label>
        </div>
      </div>
    </div>
  )

  const renderSeccionFacturacion = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Tasa de Interés Anual (%)</label>
          <Input
            type="number"
            step="0.1"
            value={configuracion.facturacion.tasaInteres}
            onChange={(e) => handleCambio('facturacion', 'tasaInteres', parseFloat(e.target.value))}
            placeholder="12.5"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Tasa de Mora Anual (%)</label>
          <Input
            type="number"
            step="0.1"
            value={configuracion.facturacion.tasaMora}
            onChange={(e) => handleCambio('facturacion', 'tasaMora', parseFloat(e.target.value))}
            placeholder="24.0"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Días de Gracia</label>
          <Input
            type="number"
            value={configuracion.facturacion.diasGracia}
            onChange={(e) => handleCambio('facturacion', 'diasGracia', parseInt(e.target.value))}
            placeholder="5"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Monto Mínimo</label>
          <Input
            type="number"
            value={configuracion.facturacion.montoMinimo}
            onChange={(e) => handleCambio('facturacion', 'montoMinimo', parseInt(e.target.value))}
            placeholder="5000"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Monto Máximo</label>
          <Input
            type="number"
            value={configuracion.facturacion.montoMaximo}
            onChange={(e) => handleCambio('facturacion', 'montoMaximo', parseInt(e.target.value))}
            placeholder="50000"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Plazo Mínimo (meses)</label>
          <Input
            type="number"
            value={configuracion.facturacion.plazoMinimo}
            onChange={(e) => handleCambio('facturacion', 'plazoMinimo', parseInt(e.target.value))}
            placeholder="12"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Plazo Máximo (meses)</label>
          <Input
            type="number"
            value={configuracion.facturacion.plazoMaximo}
            onChange={(e) => handleCambio('facturacion', 'plazoMaximo', parseInt(e.target.value))}
            placeholder="60"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Cuota Inicial Mínima (%)</label>
          <Input
            type="number"
            value={configuracion.facturacion.cuotaInicialMinima}
            onChange={(e) => handleCambio('facturacion', 'cuotaInicialMinima', parseInt(e.target.value))}
            placeholder="10"
          />
        </div>
      </div>
    </div>
  )

  const renderSeccionProgramador = () => (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Calendar className="h-5 w-5 text-green-600" />
          <h3 className="font-semibold text-green-900">Programador de Tareas</h3>
        </div>
        <p className="text-sm text-green-700">
          Configura tareas automáticas, recordatorios y procesos programados del sistema.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-1">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-600" />
              Tareas Programadas
            </CardTitle>
            <CardDescription>
              Configuración de tareas automáticas del sistema
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Recordatorios de Pago</h4>
                <p className="text-sm text-gray-600">
                  Envío automático de recordatorios antes del vencimiento
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={true}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Backup Automático</h4>
                <p className="text-sm text-gray-600">
                  Respaldo automático de la base de datos
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={true}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Reportes Automáticos</h4>
                <p className="text-sm text-gray-600">
                  Generación y envío automático de reportes
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={false}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )

  const renderSeccionAuditoria = () => (
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

      <div className="grid gap-6 md:grid-cols-1">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5 text-blue-600" />
              Configuración de Auditoría
            </CardTitle>
            <CardDescription>
              Configura qué eventos se registran en el sistema de auditoría
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Auditoría de Usuarios</h4>
                <p className="text-sm text-gray-600">
                  Registra login, logout y cambios de perfil
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={true}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Auditoría de Transacciones</h4>
                <p className="text-sm text-gray-600">
                  Registra todos los movimientos financieros
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={true}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Auditoría de Configuración</h4>
                <p className="text-sm text-gray-600">
                  Registra cambios en configuraciones del sistema
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={true}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Retención de Logs</h4>
                <p className="text-sm text-gray-600">
                  Días de retención de registros de auditoría
                </p>
              </div>
              <Input
                type="number"
                value={90}
                className="w-20"
                placeholder="90"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )

  const renderSeccionInteligenciaArtificial = () => (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-blue-900">Configuración de Inteligencia Artificial</h3>
        </div>
        <p className="text-sm text-blue-700">
          Configura las funcionalidades de IA para scoring crediticio, predicción de mora y chatbot inteligente.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-1">
        {/* OpenAI API Key */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Settings className="h-5 w-5 text-blue-600" />
              OpenAI Configuration
            </CardTitle>
            <CardDescription>
              Configuración de la API de OpenAI para funcionalidades de IA
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">OpenAI API Key</label>
              <div className="relative">
                <Input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={configuracion.inteligenciaArtificial.openaiApiKey}
                  onChange={(e) => handleCambio('inteligenciaArtificial', 'openaiApiKey', e.target.value)}
                  placeholder="sk-..."
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
                Obtén tu API Key en: https://platform.openai.com/api-keys
              </p>
            </div>

            <div>
              <label className="text-sm font-medium">Modelo de OpenAI</label>
              <Select
                value={configuracion.inteligenciaArtificial.openaiModel}
                onValueChange={(value) => handleCambio('inteligenciaArtificial', 'openaiModel', value)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona un modelo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo (Recomendado)</SelectItem>
                  <SelectItem value="gpt-4">GPT-4 (Más potente)</SelectItem>
                  <SelectItem value="gpt-4-turbo">GPT-4 Turbo (Más rápido)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-gray-500 mt-1">
                GPT-3.5 Turbo es más económico, GPT-4 es más preciso
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Funcionalidades de IA */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Brain className="h-5 w-5 text-green-600" />
              Funcionalidades de IA
            </CardTitle>
            <CardDescription>
              Habilita o deshabilita las diferentes funcionalidades de inteligencia artificial
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Scoring Crediticio con IA</h4>
                <p className="text-sm text-gray-600">
                  Analiza automáticamente la capacidad de pago de los clientes
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={configuracion.inteligenciaArtificial.aiScoringEnabled}
                  onChange={(e) => handleCambio('inteligenciaArtificial', 'aiScoringEnabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Predicción de Mora</h4>
                <p className="text-sm text-gray-600">
                  Predice la probabilidad de mora usando machine learning
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={configuracion.inteligenciaArtificial.aiPredictionEnabled}
                  onChange={(e) => handleCambio('inteligenciaArtificial', 'aiPredictionEnabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <h4 className="font-medium">Chatbot Inteligente</h4>
                <p className="text-sm text-gray-600">
                  Asistente virtual para atención al cliente
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={configuracion.inteligenciaArtificial.aiChatbotEnabled}
                  onChange={(e) => handleCambio('inteligenciaArtificial', 'aiChatbotEnabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </CardContent>
        </Card>

        {/* Estado de la configuración */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Estado de la Configuración
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">API Key configurada:</span>
                <Badge variant={configuracion.inteligenciaArtificial.openaiApiKey ? "default" : "destructive"}>
                  {configuracion.inteligenciaArtificial.openaiApiKey ? "✅ Configurada" : "❌ No configurada"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Modelo seleccionado:</span>
                <Badge variant="secondary">{configuracion.inteligenciaArtificial.openaiModel}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Funcionalidades activas:</span>
                <Badge variant="secondary">
                  {[
                    configuracion.inteligenciaArtificial.aiScoringEnabled && "Scoring",
                    configuracion.inteligenciaArtificial.aiPredictionEnabled && "Predicción",
                    configuracion.inteligenciaArtificial.aiChatbotEnabled && "Chatbot"
                  ].filter(Boolean).join(", ") || "Ninguna"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )

  const renderContenidoSeccion = () => {
    switch (seccionActiva) {
      case 'general': return renderSeccionGeneral()
      case 'notificaciones': return renderSeccionNotificaciones()
      case 'programador': return renderSeccionProgramador()
      case 'auditoria': return renderSeccionAuditoria()
      // case 'seguridad': return renderSeccionSeguridad() // OCULTO
      case 'baseDatos': return renderSeccionBaseDatos()
      // case 'integraciones': return renderSeccionIntegraciones() // OCULTO
      case 'facturacion': return renderSeccionFacturacion()
      case 'inteligenciaArtificial': return renderSeccionInteligenciaArtificial()
      case 'validadores': return <ValidadoresConfig />
      case 'concesionarios': return <ConcesionariosConfig />
      case 'analistaes': return <AnalistasConfig />
      case 'usuarios': return <UsuariosConfig />
      default: return renderSeccionGeneral()
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <h1 className="text-3xl font-bold text-gray-900">Configuración del Sistema</h1>
      <p className="text-gray-600">Gestiona la configuración general del sistema RAPICREDIT.</p>

      <div className="grid gap-6">
        {/* Contenido de la Sección */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center">
                  {(() => {
                    const seccion = secciones.find(s => s.id === seccionActiva)
                    const IconComponent = seccion?.icono || Settings
                    return (
                      <>
                        <IconComponent className="mr-2 h-5 w-5" />
                        {seccion?.nombre}
                      </>
                    )
                  })()}
                </CardTitle>
                <CardDescription>
                  Configuración de la sección {secciones.find(s => s.id === seccionActiva)?.nombre?.toLowerCase() || 'General'}
                </CardDescription>
              </div>
              <div className="flex space-x-2">
                {cambiosPendientes && (
                  <Badge variant="warning" className="animate-pulse">
                    Cambios pendientes
                  </Badge>
                )}
                <Button
                  onClick={handleGuardar}
                  disabled={!cambiosPendientes}
                  className={cambiosPendientes ? 'animate-pulse' : ''}
                >
                  <Save className="mr-2 h-4 w-4" />
                  Guardar
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {renderContenidoSeccion()}
          </CardContent>
        </Card>
      </div>

      {/* Información del Sistema */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="mr-2 h-5 w-5" /> Información del Sistema
          </CardTitle>
          <CardDescription>Detalles técnicos y estado del sistema.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Última Actualización</div>
              <div className="font-semibold">{formatDate(configuracion.general.ultimaActualizacion)}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Estado del Sistema</div>
              <div className="font-semibold text-green-600 flex items-center">
                <CheckCircle className="h-4 w-4 mr-1" />
                Activo
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Base de Datos</div>
              <div className="font-semibold text-green-600 flex items-center">
                <CheckCircle className="h-4 w-4 mr-1" />
                Conectada
              </div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="text-sm text-gray-500">Backup</div>
              <div className="font-semibold text-green-600 flex items-center">
                <CheckCircle className="h-4 w-4 mr-1" />
                Actualizado
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
