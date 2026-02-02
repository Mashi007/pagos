import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getErrorMessage, isAxiosError, getErrorDetail } from '../types/errors'
import { env } from '../config/env'
import {
  Settings,
  Save,
  RefreshCw,
  Bell,
  Mail,
  MessageSquare,
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
  Upload,
  Download,
  Trash2,
  Car,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select'
import { formatDate } from '../utils'
import { validarNombreEmpresa, validarMoneda, validarZonaHoraria, validarIdioma } from '../utils/validators'
import { ValidadoresConfig } from '../components/configuracion/ValidadoresConfig'
import { ConcesionariosConfig } from '../components/configuracion/ConcesionariosConfig'
import { AnalistasConfig } from '../components/configuracion/AnalistasConfig'
import { ModelosVehiculosConfig } from '../components/configuracion/ModelosVehiculosConfig'
import { EmailConfig } from '../components/configuracion/EmailConfig'
import { WhatsAppConfig } from '../components/configuracion/WhatsAppConfig'
import { AIConfig } from '../components/configuracion/AIConfig'
import { configuracionGeneralService, ConfiguracionGeneral } from '../services/configuracionGeneralService'
import { apiClient } from '../services/api'
import { toast } from 'sonner'
import UsuariosConfig from '../components/configuracion/UsuariosConfig'
import {
  SECCIONES_CONFIGURACION,
  NOMBRES_SECCION_ESPECIAL,
  findSeccionById as findSeccionByIdHelper,
} from '../constants/configuracionSecciones'

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
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const [configuracion, setConfiguracion] = useState(mockConfiguracion)
  const [configuracionGeneral, setConfiguracionGeneral] = useState<ConfiguracionGeneral | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Inicializar sección desde URL para que Email, WhatsApp y AI se vean al entrar por enlace
  const [seccionActiva, setSeccionActiva] = useState(() => {
    const tab = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('tab') : null
    if (tab === 'email') return 'emailConfig'
    if (tab === 'whatsapp') return 'whatsappConfig'
    if (tab === 'ai') return 'aiConfig'
    return 'general'
  })
  const [estadoCarga, setEstadoCarga] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  // Sincronizar sección con el parámetro tab de la URL (al cambiar tab por navegación o al abrir /pagos/configuracion?tab=ai)
  useEffect(() => {
    const tab = searchParams.get('tab')
    if (tab === 'email') {
      setSeccionActiva('emailConfig')
    } else if (tab === 'whatsapp') {
      setSeccionActiva('whatsappConfig')
    } else if (tab === 'ai') {
      setSeccionActiva('aiConfig')
    }
  }, [searchParams])
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [cambiosPendientes, setCambiosPendientes] = useState(false)
  const [submenuAbierto, setSubmenuAbierto] = useState(false)
  const [erroresValidacion, setErroresValidacion] = useState<Record<string, string>>({})

  // Cargar configuración general al montar el componente
  useEffect(() => {
    cargarConfiguracionGeneral()
  }, [])

  // Navegar a rutas externas cuando se seleccionan secciones con href
  useEffect(() => {
    if (seccionActiva === 'plantillas') {
      navigate('/herramientas/plantillas')
    } else if (seccionActiva === 'scheduler') {
      navigate('/scheduler')
    }
  }, [seccionActiva, navigate])

  const cargarConfiguracionGeneral = async (preserveLogoStateIfMissing = false) => {
    try {
      setLoading(true)
      setEstadoCarga('loading')
      setError(null)
      console.log('ðŸ”„ Cargando configuración general...')

      const config = await configuracionGeneralService.obtenerConfiguracionGeneral()
      console.log('Configuración general cargada:', config)
      console.log('logo_filename en servidor:', config.logo_filename ?? '(no devuelto)')

      setConfiguracionGeneral(config)
      
      // ✅ Verificar si hay logo personalizado
      if (config.logo_filename) {
        // Verificar que el logo realmente existe haciendo una petición HEAD.
        // En producción env.API_URL es '' → URL relativa /api/... (mismo origen, proxy en server.js).
        // credentials: 'same-origin' evita 401 si el servidor espera cookie de sesión.
        try {
          const base = (env.API_URL || '').replace(/\/$/, '')
          const logoUrl = `${base}/api/v1/configuracion/logo/${config.logo_filename}?t=${Date.now()}`
          const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
          const headResponse = await fetch(logoUrl, {
            method: 'HEAD',
            credentials: 'same-origin',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          })
          
          if (headResponse.ok) {
            // El logo existe, mostrar opción de eliminar
            setHasCustomLogo(true)
            setLogoPreview(logoUrl)
            setLogoInfo({ filename: config.logo_filename, url: logoUrl })
            console.log(`✅ Logo personalizado encontrado: ${config.logo_filename}`)
          } else {
            // El logo no existe aunque esté en la BD, limpiar estado
            setHasCustomLogo(false)
            setLogoPreview(null)
            setLogoInfo(null)
            console.warn(`âš ï¸ Logo ${config.logo_filename} no encontrado en el servidor`)
          }
        } catch (logoError) {
          // Si hay error verificando, asumir que no existe
          setHasCustomLogo(false)
          setLogoPreview(null)
          setLogoInfo(null)
          console.warn(`âš ï¸ Error verificando logo:`, logoError)
        }
      } else {
        // Si el servidor no devuelve logo_filename: no borrar el preview cuando
        // acabamos de subir (preserveLogoStateIfMissing) para que no desaparezca
        // hasta que el backend persista y devuelva logo_filename (p. ej. tras redesplegar).
        if (!preserveLogoStateIfMissing) {
          setHasCustomLogo(false)
          setLogoPreview(null)
          setLogoInfo(null)
        }
      }

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
      setEstadoCarga('success')
    } catch (err) {
      console.error('âŒ Error cargando configuración general:', err)
      setError('Error al cargar configuración general')
      setEstadoCarga('error')
      // Usar datos mock como fallback
    } finally {
      setLoading(false)
      // Resetear estado después de 2 segundos
      setTimeout(() => setEstadoCarga('idle'), 2000)
    }
  }

  const actualizarConfiguracionGeneral = async (campo: string, valor: string) => {
    try {
      setLoading(true)
      setError(null)

      console.log(`ðŸ”„ Actualizando ${campo} a:`, valor)

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
      console.error('âŒ Error actualizando configuración:', err)
      setError(`Error al actualizar ${campo}`)
      toast.error(`Error al actualizar ${campo}`)
    } finally {
      setLoading(false)
    }
  }

  const seccionesList = SECCIONES_CONFIGURACION
  const secciones = seccionesList
  const findSeccionById = (id: string) => findSeccionByIdHelper(seccionesList, id)
  const nombresSeccionEspecial = NOMBRES_SECCION_ESPECIAL

  const handleGuardar = async () => {
    try {
      setLoading(true)

      // Guardar cambios de configuración general si hay cambios pendientes
      if (configuracionGeneral && cambiosPendientes) {
        // Mapeo de campos frontend a backend
        const camposMap: Record<string, string> = {
          'nombreEmpresa': 'nombre_empresa',
          'idioma': 'idioma',
          'zonaHoraria': 'zona_horaria',
          'moneda': 'moneda'
        }

        // Actualizar cada campo que haya cambiado
        for (const [campoFrontend, campoBackend] of Object.entries(camposMap)) {
          const valorFrontend = configuracion.general[campoFrontend as keyof typeof configuracion.general]
          const valorBackend = configuracionGeneral[campoBackend as keyof typeof configuracionGeneral]

          if (valorFrontend && valorFrontend !== valorBackend) {
            await actualizarConfiguracionGeneral(campoBackend, String(valorFrontend))
          }
        }

        // Si hay un logo preview, significa que se subió un logo
        // Verificar explícitamente que el logo esté guardado en la BD
        if (logoPreview && logoInfo) {
          // Verificar que el logo_filename esté persistido en la BD (usa apiClient para base URL correcta)
          const updatedConfig = await configuracionGeneralService.obtenerConfiguracionGeneral()

          // Verificar que logo_filename esté en la BD y coincida con el logo subido
          if (updatedConfig.logo_filename) {
            if (updatedConfig.logo_filename === logoInfo.filename) {
              // Actualizar estado local con configuración recargada
              setConfiguracionGeneral(updatedConfig)

              // Disparar evento para actualizar todos los componentes Logo con la información completa
              window.dispatchEvent(new CustomEvent('logoUpdated', {
                detail: {
                  confirmed: true,
                  filename: logoInfo.filename,
                  url: logoInfo.url
                }
              }))

              // Limpiar estado después de confirmar
              setLogoPreview(null)
              setLogoInfo(null)

              toast.success('Logo guardado exitosamente en la base de datos')
            } else {
              toast.warning('El logo se guardó pero hay una discrepancia. Por favor, verifica.')
              // Continuar con el guardado aunque haya discrepancia
              setLogoPreview(null)
              setLogoInfo(null)
            }
          } else {
            toast.error('Error: El logo no se guardó correctamente en la base de datos. Por favor, intenta subirlo nuevamente.')
            // No limpiar estado para que el usuario pueda intentar de nuevo
            throw new Error('Logo no encontrado en BD después de guardar')
          }
        }

        // Marcar cambios como guardados solo si no hubo errores
        setCambiosPendientes(false)

        // Mostrar mensaje de éxito general solo si no hay logo (el logo ya mostró su mensaje)
        if (!logoPreview || !logoInfo) {
          toast.success('Configuración guardada exitosamente')
        }
      }
    } catch (error: unknown) {
      console.error('Error guardando configuración:', error)
      const errorMessage = getErrorMessage(error)
      toast.error(`Error al guardar configuración: ${errorMessage}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCambio = (seccion: string, campo: string, valor: string | number | boolean | null) => {
    console.log(`ðŸ”„ Cambio en ${seccion}.${campo}:`, valor)

    // ✅ Validación en tiempo real
    const claveError = `${seccion}.${campo}`
    let error: string | null = null

    if (seccion === 'general') {
      if (campo === 'nombreEmpresa' && typeof valor === 'string') {
        const validacion = validarNombreEmpresa(valor)
        if (!validacion.valido) {
          error = validacion.error || null
        }
      } else if (campo === 'moneda' && typeof valor === 'string') {
        if (!validarMoneda(valor)) {
          error = 'Moneda no válida'
        }
      } else if (campo === 'zonaHoraria' && typeof valor === 'string') {
        if (!validarZonaHoraria(valor)) {
          error = 'Zona horaria no válida'
        }
      } else if (campo === 'idioma' && typeof valor === 'string') {
        if (!validarIdioma(valor)) {
          error = 'Idioma no válido'
        }
      }
    }

    // Actualizar errores
    setErroresValidacion(prev => {
      if (error) {
        return { ...prev, [claveError]: error }
      } else {
        const nuevosErrores = { ...prev }
        delete nuevosErrores[claveError]
        return nuevosErrores
      }
    })

    setConfiguracion(prev => ({
      ...prev,
      [seccion]: {
        ...prev[seccion as keyof typeof prev],
        [campo]: valor
      }
    }))

    setCambiosPendientes(true)

    // NO actualizar automáticamente en el backend
    // El usuario debe hacer clic en "Guardar" para persistir los cambios
  }

  const [uploadingLogo, setUploadingLogo] = useState(false)
  const [deletingLogo, setDeletingLogo] = useState(false)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [logoInfo, setLogoInfo] = useState<{ filename: string; url: string } | null>(null)
  const [hasCustomLogo, setHasCustomLogo] = useState(false)

  const handleCargarLogo = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validar tipo de archivo
    const allowedTypes = ['image/svg+xml', 'image/png', 'image/jpeg', 'image/jpg']
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no válido. Use SVG, PNG o JPG')
      return
    }

    // Validar tamaño (máximo 2MB)
    if (file.size > 2 * 1024 * 1024) {
      toast.error('El archivo es demasiado grande. Máximo 2MB')
      return
    }

    try {
      setUploadingLogo(true)

      // Crear FormData para enviar el archivo
      const formData = new FormData()
      formData.append('logo', file)

      // Subir logo usando fetch directamente para FormData (axios puede tener problemas con FormData)
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
      const response = await fetch(`${env.API_URL}/api/v1/configuracion/upload-logo`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          // NO establecer Content-Type, el navegador lo hace automáticamente para FormData
        },
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
        throw new Error(errorData.detail || `Error ${response.status}`)
      }

      const result = await response.json()

      // Guardar información del logo para usar después al confirmar
      setLogoInfo({ filename: result.filename, url: result.url })

      // Mostrar preview del logo desde el servidor con timestamp para evitar caché
      if (result.url) {
        const logoUrl = `${result.url}?t=${Date.now()}`
        setLogoPreview(logoUrl)
      } else {
        // Fallback: mostrar preview local si no hay URL
        const reader = new FileReader()
        reader.onloadend = () => {
          setLogoPreview(reader.result as string)
        }
        reader.readAsDataURL(file)
      }

      // ✅ Marcar que hay logo personalizado para mostrar botón eliminar
      setHasCustomLogo(true)

      // Marcar como cambio pendiente para activar botón Guardar
      // Esto permite al usuario validar/confirmar antes de aplicar el cambio
      setCambiosPendientes(true)

      toast.success('Logo cargado exitosamente.')

      // Disparar evento para actualizar componentes Logo inmediatamente
      window.dispatchEvent(new CustomEvent('logoUpdated', {
        detail: { filename: result.filename, url: result.url }
      }))
      
      // Recargar configuración general; si el backend aún no devuelve logo_filename,
      // mantener el preview del logo recién subido (preserveLogoStateIfMissing = true)
      await cargarConfiguracionGeneral(true)
    } catch (error: unknown) {
      console.error('Error cargando logo:', error)
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) {
        errorMessage = detail
      }
      toast.error(`Error al cargar logo: ${errorMessage}`)
    } finally {
      setUploadingLogo(false)
      // Limpiar input
      event.target.value = ''
    }
  }

  const handleEliminarLogo = async () => {
    try {
      setDeletingLogo(true)

      // Llamar al endpoint DELETE para eliminar el logo
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
      const response = await fetch(`${env.API_URL}/api/v1/configuracion/logo`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
        throw new Error(errorData.detail || `Error ${response.status}`)
      }

      const result = await response.json()

      // Limpiar estados del logo
      setLogoPreview(null)
      setLogoInfo(null)
      setHasCustomLogo(false)

      // Disparar evento para actualizar componentes Logo
      window.dispatchEvent(new CustomEvent('logoUpdated', {
        detail: { filename: null, url: null }
      }))

      // También disparar evento para limpiar caché del logo
      window.dispatchEvent(new CustomEvent('logoDeleted'))

      toast.success(result.message || 'Logo eliminado exitosamente. Se usará el logo por defecto.')

      // Recargar configuración general para actualizar el estado
      await cargarConfiguracionGeneral()
    } catch (error: unknown) {
      console.error('Error eliminando logo:', error)
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) {
        errorMessage = detail
      }
      toast.error(`Error al eliminar logo: ${errorMessage}`)
    } finally {
      setDeletingLogo(false)
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
            className={erroresValidacion['general.nombreEmpresa'] ? 'border-red-500' : ''}
          />
          {erroresValidacion['general.nombreEmpresa'] && (
            <p className="text-xs text-red-600 mt-1">{erroresValidacion['general.nombreEmpresa']}</p>
          )}
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
      </div>

      {/* Sección de Carga de Logo */}
      <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50/30">
        <CardHeader>
          <div className="flex items-center space-x-2">
            <Upload className="h-5 w-5 text-blue-600" />
            <CardTitle className="text-lg">Cargar Logo de la Empresa</CardTitle>
          </div>
          <CardDescription>
            Suba un nuevo logo para la empresa. El logo se mostrará en el sidebar, login y otras páginas del sistema.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col space-y-4">
            <div className="bg-white/60 rounded-lg p-4 border border-blue-100">
              <p className="text-sm text-gray-700 mb-3">
                <strong>ðŸ“‹ Formatos soportados:</strong> SVG, PNG, JPG
              </p>
              <p className="text-xs text-gray-600">
                <strong>ðŸ“ Tamaño máximo:</strong> 2MB. Se recomienda usar SVG para mejor calidad.
              </p>
            </div>

            {/* Preview del logo actual o nuevo */}
            {logoPreview && (
              <div className="flex flex-col items-center space-y-3 p-4 bg-white rounded-lg border border-blue-200">
                <img
                  src={logoPreview}
                  alt="Vista previa del logo"
                  className="max-h-24 max-w-48 object-contain"
                />
                {hasCustomLogo && (
                  <p className="text-xs text-gray-500">
                    Logo personalizado actual: {logoInfo?.filename || 'logo-custom'}
                  </p>
                )}
              </div>
            )}

            {/* Botón para eliminar logo personalizado */}
            {hasCustomLogo && (
              <div className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                  <div>
                    <p className="text-sm font-medium text-red-900">Logo personalizado activo</p>
                    <p className="text-xs text-red-700">Puede eliminar el logo para restaurar el logo por defecto</p>
                  </div>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleEliminarLogo}
                  disabled={deletingLogo || uploadingLogo}
                  className="flex items-center space-x-2"
                >
                  {deletingLogo ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Eliminando...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      <span>Eliminar Logo</span>
                    </>
                  )}
                </Button>
              </div>
            )}

            {/* Mensaje cuando no hay logo personalizado */}
            {!hasCustomLogo && !logoPreview && (
              <div className="flex items-center justify-center p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                  <p className="text-sm text-blue-900">
                    Usando logo por defecto. Puede subir un logo personalizado arriba.
                  </p>
                </div>
              </div>
            )}

            {/* Input de archivo */}
            <div className="flex flex-col space-y-2">
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-blue-300 rounded-lg cursor-pointer bg-white/50 hover:bg-blue-50/50 transition-colors">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  {uploadingLogo ? (
                    <>
                      <RefreshCw className="w-8 h-8 mb-2 text-blue-600 animate-spin" />
                      <p className="text-sm text-gray-600">Subiendo logo...</p>
                    </>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 mb-2 text-blue-600" />
                      <p className="mb-2 text-sm text-gray-600">
                        <span className="font-semibold">Haga clic para seleccionar</span> o arrastre el archivo aquí
                      </p>
                      <p className="text-xs text-gray-500">SVG, PNG o JPG (MAX. 2MB)</p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".svg,.png,.jpg,.jpeg,image/svg+xml,image/png,image/jpeg"
                  onChange={handleCargarLogo}
                  disabled={uploadingLogo}
                />
              </label>
            </div>
          </div>
        </CardContent>
      </Card>
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
    // Si la sección tiene href, no renderizar contenido (la navegación se maneja en useEffect)
    if (seccionActiva === 'plantillas' || seccionActiva === 'scheduler') {
      return null
    }
    
    switch (seccionActiva) {
      case 'general': return renderSeccionGeneral()
      case 'notificaciones': return renderSeccionNotificaciones()
      case 'emailConfig': return <EmailConfig />
      case 'whatsappConfig': return <WhatsAppConfig />
      case 'aiConfig': return <AIConfig />
      case 'programador': return renderSeccionProgramador()
      case 'auditoria': return renderSeccionAuditoria()
      // case 'seguridad': return renderSeccionSeguridad() // OCULTO
      case 'baseDatos': return renderSeccionBaseDatos()
      // case 'integraciones': return renderSeccionIntegraciones() // OCULTO
      case 'facturacion': return renderSeccionFacturacion()
      case 'inteligenciaArtificial': return <AIConfig />
      case 'validadores': return <ValidadoresConfig />
      case 'concesionarios': return <ConcesionariosConfig />
      case 'analistas': return <AnalistasConfig />
      case 'modelosVehiculos': return <ModelosVehiculosConfig />
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
      <div className="grid gap-6">
        {/* Contenido de la Sección */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center">
                  {(() => {
                    const seccion = findSeccionById(seccionActiva) || (nombresSeccionEspecial[seccionActiva]
                      ? { nombre: nombresSeccionEspecial[seccionActiva].nombre, icono: nombresSeccionEspecial[seccionActiva].icono }
                      : secciones.find(s => s.id === seccionActiva))
                    const IconComponent = seccion?.icono || Settings
                    return (
                      <>
                        <IconComponent className="mr-2 h-5 w-5" />
                        {seccion?.nombre ?? 'Configuración'}
                      </>
                    )
                  })()}
                </CardTitle>
              </div>
              <div className="flex space-x-2">
                {/* ✅ Ocultar botón "Guardar" en secciones que tienen su propio botón de guardar */}
                {/* emailConfig y whatsappConfig tienen sus propios botones de guardar */}
                {seccionActiva !== 'emailConfig' && seccionActiva !== 'whatsappConfig' && seccionActiva !== 'aiConfig' && (
                  <>
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
                  </>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading && estadoCarga === 'loading' && (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin text-blue-600 mr-2" />
                <span className="text-gray-600">Cargando configuración...</span>
              </div>
            )}
            {!loading && renderContenidoSeccion()}
          </CardContent>
        </Card>
      </div>
    </motion.div>
  )
}

export default Configuracion
