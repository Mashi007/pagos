import { useState } from 'react'
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
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { formatDate } from '@/utils'
import { ValidadoresConfig } from '@/components/configuracion/ValidadoresConfig'
import { ConcesionariosConfig } from '@/components/configuracion/ConcesionariosConfig'
import { AsesoresConfig } from '@/components/configuracion/AsesoresConfig'

// Mock data para configuración
const mockConfiguracion = {
  general: {
    nombreEmpresa: 'RAPICREDIT',
    version: '1.0.0',
    idioma: 'ES',
    zonaHoraria: 'America/Caracas',
    moneda: 'VES',
    formatoFecha: 'DD/MM/YYYY',
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
}

export function Configuracion() {
  const [configuracion, setConfiguracion] = useState(mockConfiguracion)
  const [seccionActiva, setSeccionActiva] = useState('general')
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [cambiosPendientes, setCambiosPendientes] = useState(false)

  const secciones = [
    { id: 'general', nombre: 'General', icono: Globe },
    { id: 'notificaciones', nombre: 'Notificaciones', icono: Bell },
    { id: 'seguridad', nombre: 'Seguridad', icono: Shield },
    { id: 'baseDatos', nombre: 'Base de Datos', icono: Database },
    { id: 'integraciones', nombre: 'Integraciones', icono: Settings },
    { id: 'facturacion', nombre: 'Facturación', icono: DollarSign },
    { id: 'validadores', nombre: 'Validadores', icono: CheckSquare },
    { id: 'concesionarios', nombre: 'Concesionarios', icono: Building },
    { id: 'asesores', nombre: 'Asesores', icono: Users },
  ]

  const handleGuardar = () => {
    console.log('Guardando configuración...', configuracion)
    setCambiosPendientes(false)
    // Lógica para guardar configuración
  }

  const handleCambio = (seccion: string, campo: string, valor: any) => {
    setConfiguracion(prev => ({
      ...prev,
      [seccion]: {
        ...prev[seccion as keyof typeof prev],
        [campo]: valor
      }
    }))
    setCambiosPendientes(true)
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
          <label className="text-sm font-medium">Formato de Fecha</label>
          <Select value={configuracion.general.formatoFecha} onValueChange={(value: string) => handleCambio('general', 'formatoFecha', value)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
              <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
              <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
            </SelectContent>
          </Select>
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

  const renderContenidoSeccion = () => {
    switch (seccionActiva) {
      case 'general': return renderSeccionGeneral()
      case 'notificaciones': return renderSeccionNotificaciones()
      case 'seguridad': return renderSeccionSeguridad()
      case 'baseDatos': return renderSeccionBaseDatos()
      case 'integraciones': return renderSeccionIntegraciones()
      case 'facturacion': return renderSeccionFacturacion()
      case 'validadores': return <ValidadoresConfig />
      case 'concesionarios': return <ConcesionariosConfig />
      case 'asesores': return <AsesoresConfig />
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

      <div className="grid gap-6 lg:grid-cols-4">
        {/* Sidebar de Secciones */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Secciones</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {secciones.map((seccion) => {
                const IconComponent = seccion.icono
                return (
                  <button
                    key={seccion.id}
                    onClick={() => setSeccionActiva(seccion.id)}
                    className={`w-full flex items-center space-x-3 p-3 rounded-lg text-left transition-colors ${
                      seccionActiva === seccion.id
                        ? 'bg-blue-100 text-blue-700'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <IconComponent className="h-5 w-5" />
                    <span className="font-medium">{seccion.nombre}</span>
                  </button>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Contenido de la Sección */}
        <Card className="lg:col-span-3">
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
                  Configuración de la sección {secciones.find(s => s.id === seccionActiva)?.nombre.toLowerCase()}
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
