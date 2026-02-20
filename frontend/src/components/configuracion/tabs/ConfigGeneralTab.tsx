import { useState, useEffect } from 'react'
import {
  Upload,
  RefreshCw,
  Trash2,
  AlertTriangle,
  CheckCircle,
  Save,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card'
import { Button } from '../../ui/button'
import { Input } from '../../ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select'
import { validarNombreEmpresa, validarMoneda, validarZonaHoraria, validarIdioma } from '../../../utils/validators'
import { configuracionGeneralService, ConfiguracionGeneral } from '../../../services/configuracionGeneralService'
import { env } from '../../../config/env'
import { toast } from 'sonner'
import { getErrorMessage, getErrorDetail } from '../../../types/errors'

interface GeneralFormState {
  nombreEmpresa: string
  version: string
  idioma: string
  zonaHoraria: string
  moneda: string
}

const INITIAL_STATE: GeneralFormState = {
  nombreEmpresa: '',
  version: '',
  idioma: '',
  zonaHoraria: '',
  moneda: '',
}

export function ConfigGeneralTab() {
  const [configuracionGeneral, setConfiguracionGeneral] = useState<ConfiguracionGeneral | null>(null)
  const [formState, setFormState] = useState<GeneralFormState>(INITIAL_STATE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cambiosPendientes, setCambiosPendientes] = useState(false)
  const [erroresValidacion, setErroresValidacion] = useState<Record<string, string>>({})
  const [uploadingLogo, setUploadingLogo] = useState(false)
  const [deletingLogo, setDeletingLogo] = useState(false)
  const [logoPreview, setLogoPreview] = useState<string | null>(null)
  const [logoInfo, setLogoInfo] = useState<{ filename: string; url: string } | null>(null)
  const [hasCustomLogo, setHasCustomLogo] = useState(false)

  const cargarConfiguracionGeneral = async (preserveLogoStateIfMissing = false) => {
    try {
      setLoading(true)
      setError(null)
      const config = await configuracionGeneralService.obtenerConfiguracionGeneral()
      setConfiguracionGeneral(config)
      setFormState({
        nombreEmpresa: config.nombre_empresa ?? '',
        version: config.version_sistema ?? '',
        idioma: config.idioma ?? '',
        zonaHoraria: config.zona_horaria ?? '',
        moneda: config.moneda ?? '',
      })

      if (config.logo_filename) {
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
            setHasCustomLogo(true)
            setLogoPreview(logoUrl)
            setLogoInfo({ filename: config.logo_filename, url: logoUrl })
          } else {
            setHasCustomLogo(false)
            setLogoPreview(null)
            setLogoInfo(null)
          }
        } catch {
          setHasCustomLogo(false)
          setLogoPreview(null)
          setLogoInfo(null)
        }
      } else {
        if (!preserveLogoStateIfMissing) {
          setHasCustomLogo(false)
          setLogoPreview(null)
          setLogoInfo(null)
        }
      }
    } catch (err) {
      console.error('Error cargando configuración general:', err)
      setError('Error al cargar configuración general')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    cargarConfiguracionGeneral()
  }, [])

  const actualizarConfiguracionGeneral = async (campo: string, valor: string) => {
    try {
      setLoading(true)
      setError(null)
      await configuracionGeneralService.actualizarConfiguracionGeneral({ [campo]: valor })
      setConfiguracionGeneral(prev => prev ? { ...prev, [campo]: valor } : null)
      setFormState(prev => ({ ...prev, [campo]: valor }))
      toast.success(`${campo} actualizado exitosamente`)
    } catch (err) {
      console.error('Error actualizando configuración:', err)
      setError(`Error al actualizar ${campo}`)
      toast.error(`Error al actualizar ${campo}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCambio = (campo: keyof GeneralFormState, valor: string) => {
    const claveError = `general.${campo}`
    let error: string | null = null
    if (campo === 'nombreEmpresa') {
      const validacion = validarNombreEmpresa(valor)
      if (!validacion.valido) error = validacion.error ?? null
    } else if (campo === 'moneda' && !validarMoneda(valor)) {
      error = 'Moneda no válida'
    } else if (campo === 'zonaHoraria' && !validarZonaHoraria(valor)) {
      error = 'Zona horaria no válida'
    } else if (campo === 'idioma' && !validarIdioma(valor)) {
      error = 'Idioma no válido'
    }
    setErroresValidacion(prev => {
      const next = { ...prev }
      if (error) next[claveError] = error
      else delete next[claveError]
      return next
    })
    setFormState(prev => ({ ...prev, [campo]: valor }))
    setCambiosPendientes(true)
  }

  const handleGuardar = async () => {
    try {
      setLoading(true)
      if (configuracionGeneral && cambiosPendientes) {
        const camposMap: Record<string, string> = {
          nombreEmpresa: 'nombre_empresa',
          idioma: 'idioma',
          zonaHoraria: 'zona_horaria',
          moneda: 'moneda',
        }
        for (const [campoFrontend, campoBackend] of Object.entries(camposMap)) {
          const valorFrontend = formState[campoFrontend as keyof GeneralFormState]
          const valorBackend = configuracionGeneral[campoBackend as keyof ConfiguracionGeneral]
          if (valorFrontend && valorFrontend !== valorBackend) {
            await actualizarConfiguracionGeneral(campoBackend, String(valorFrontend))
          }
        }
        if (logoPreview && logoInfo) {
          const updatedConfig = await configuracionGeneralService.obtenerConfiguracionGeneral()
          if (updatedConfig.logo_filename === logoInfo.filename) {
            setConfiguracionGeneral(updatedConfig)
            window.dispatchEvent(new CustomEvent('logoUpdated', {
              detail: { confirmed: true, filename: logoInfo.filename, url: logoInfo.url }
            }))
            setLogoPreview(null)
            setLogoInfo(null)
            toast.success('Logo guardado exitosamente en la base de datos')
          } else {
            setLogoPreview(null)
            setLogoInfo(null)
          }
        }
        setCambiosPendientes(false)
        if (!logoPreview || !logoInfo) {
          toast.success('Configuración guardada exitosamente')
        }
      }
    } catch (err: unknown) {
      console.error('Error guardando configuración:', err)
      toast.error(`Error al guardar configuración: ${getErrorMessage(err)}`)
    } finally {
      setLoading(false)
    }
  }

  const handleCargarLogo = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const allowedTypes = ['image/svg+xml', 'image/png', 'image/jpeg', 'image/jpg']
    if (!allowedTypes.includes(file.type)) {
      toast.error('Formato no válido. Use SVG, PNG o JPG')
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error('El archivo es demasiado grande. Máximo 2MB')
      return
    }
    try {
      setUploadingLogo(true)
      const formData = new FormData()
      formData.append('logo', file)
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
      const response = await fetch(`${env.API_URL}/api/v1/configuracion/upload-logo`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
        throw new Error(errorData.detail || `Error ${response.status}`)
      }
      const result = await response.json()
      setLogoInfo({ filename: result.filename, url: result.url })
      setLogoPreview(result.url ? `${result.url}?t=${Date.now()}` : null)
      if (!result.url) {
        const reader = new FileReader()
        reader.onloadend = () => setLogoPreview(reader.result as string)
        reader.readAsDataURL(file)
      }
      setHasCustomLogo(true)
      setCambiosPendientes(true)
      toast.success('Logo cargado exitosamente.')
      window.dispatchEvent(new CustomEvent('logoUpdated', { detail: { filename: result.filename, url: result.url } }))
      await cargarConfiguracionGeneral(true)
    } catch (err: unknown) {
      const msg = getErrorDetail(err) || getErrorMessage(err)
      toast.error(`Error al cargar logo: ${msg}`)
    } finally {
      setUploadingLogo(false)
      event.target.value = ''
    }
  }

  const handleEliminarLogo = async () => {
    try {
      setDeletingLogo(true)
      const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token')
      const response = await fetch(`${env.API_URL}/api/v1/configuracion/logo`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
        throw new Error(errorData.detail || `Error ${response.status}`)
      }
      const result = await response.json()
      setLogoPreview(null)
      setLogoInfo(null)
      setHasCustomLogo(false)
      window.dispatchEvent(new CustomEvent('logoUpdated', { detail: { filename: null, url: null } }))
      window.dispatchEvent(new CustomEvent('logoDeleted'))
      toast.success(result.message || 'Logo eliminado exitosamente.')
      await cargarConfiguracionGeneral()
    } catch (err: unknown) {
      const msg = getErrorDetail(err) || getErrorMessage(err)
      toast.error(`Error al eliminar logo: ${msg}`)
    } finally {
      setDeletingLogo(false)
    }
  }

  if (loading && !configuracionGeneral) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="h-6 w-6 animate-spin text-blue-600 mr-2" />
        <span className="text-gray-600">Cargando configuración...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="text-sm font-medium">Nombre de la Empresa</label>
          <Input
            value={formState.nombreEmpresa}
            onChange={(e) => handleCambio('nombreEmpresa', e.target.value)}
            placeholder="Nombre de la empresa"
            className={erroresValidacion['general.nombreEmpresa'] ? 'border-red-500' : ''}
          />
          {erroresValidacion['general.nombreEmpresa'] && (
            <p className="text-xs text-red-600 mt-1">{erroresValidacion['general.nombreEmpresa']}</p>
          )}
        </div>
        <div>
          <label className="text-sm font-medium">Versión del Sistema</label>
          <Input value={formState.version} disabled className="bg-gray-100" />
        </div>
        <div>
          <label className="text-sm font-medium">Idioma</label>
          <Select value={formState.idioma} onValueChange={(v) => handleCambio('idioma', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="ES">Español</SelectItem>
              <SelectItem value="EN">English</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Zona Horaria</label>
          <Select value={formState.zonaHoraria} onValueChange={(v) => handleCambio('zonaHoraria', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="America/Caracas">Caracas (UTC-4)</SelectItem>
              <SelectItem value="America/New_York">New York (UTC-5)</SelectItem>
              <SelectItem value="America/Los_Angeles">Los Angeles (UTC-8)</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-sm font-medium">Moneda</label>
          <Select value={formState.moneda} onValueChange={(v) => handleCambio('moneda', v)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="VES">Bolívar Soberano (VES)</SelectItem>
              <SelectItem value="USD">Dólar Americano (USD)</SelectItem>
              <SelectItem value="EUR">Euro (EUR)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

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
            {logoPreview && (
              <div className="flex flex-col items-center space-y-3 p-4 bg-white rounded-lg border border-blue-200">
                <img src={logoPreview} alt="Vista previa del logo" className="max-h-24 max-w-48 object-contain" />
                {hasCustomLogo && (
                  <p className="text-xs text-gray-500">Logo personalizado actual: {logoInfo?.filename || 'logo-custom'}</p>
                )}
              </div>
            )}
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
                    <><RefreshCw className="w-4 h-4 animate-spin" /><span>Eliminando...</span></>
                  ) : (
                    <><Trash2 className="w-4 h-4" /><span>Eliminar Logo</span></>
                  )}
                </Button>
              </div>
            )}
            {!hasCustomLogo && !logoPreview && (
              <div className="flex items-center justify-center p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                  <p className="text-sm text-blue-900">Usando logo por defecto. Puede subir un logo personalizado arriba.</p>
                </div>
              </div>
            )}
            <div className="flex flex-col space-y-2">
              <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-blue-300 rounded-lg cursor-pointer bg-white/50 hover:bg-blue-50/50 transition-colors">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  {uploadingLogo ? (
                    <><RefreshCw className="w-8 h-8 mb-2 text-blue-600 animate-spin" /><p className="text-sm text-gray-600">Subiendo logo...</p></>
                  ) : (
                    <>
                      <Upload className="w-8 h-8 mb-2 text-blue-600" />
                      <p className="mb-2 text-sm text-gray-600"><span className="font-semibold">Haga clic para seleccionar</span> o arrastre el archivo aquí</p>
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

      {cambiosPendientes && (
        <div className="flex justify-end">
          <Button onClick={handleGuardar} disabled={loading}>
            {loading ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Guardar cambios
          </Button>
        </div>
      )}
    </div>
  )
}
