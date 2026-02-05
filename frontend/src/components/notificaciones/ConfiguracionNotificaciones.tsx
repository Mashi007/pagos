import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import {
  Settings,
  Mail,
  FileText,
  Clock,
  Link as LinkIcon,
  X,
} from 'lucide-react'
import { emailConfigService } from '../../services/notificacionService'
import { notificacionService, type NotificacionPlantilla } from '../../services/notificacionService'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'

/** Tipo de configuración por criterio (habilitado, cco, plantilla opcional, programador) */
export type ConfigEnvioItem = {
  habilitado: boolean
  cco: string[]
  plantilla_id?: number | null
  programador?: string
}

const CRITERIOS: { tipo: string; label: string; categoria: string; color: 'blue' | 'green' | 'orange' | 'red' | 'slate' }[] = [
  { tipo: 'PAGO_5_DIAS_ANTES', label: 'Faltan 5 días', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_3_DIAS_ANTES', label: 'Faltan 3 días', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_1_DIA_ANTES', label: 'Falta 1 día', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_DIA_0', label: 'Hoy vence', categoria: 'Día de pago', color: 'green' },
  { tipo: 'PAGO_1_DIA_ATRASADO', label: '1 día de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_5_DIAS_ATRASADO', label: '5 días de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PREJUDICIAL', label: 'Prejudicial', categoria: 'Prejudicial', color: 'red' },
  { tipo: 'MORA_61', label: '61+ días de mora', categoria: 'Mora 61+', color: 'slate' },
]

const COLORES = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-900', accent: 'text-blue-600' },
  green: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-900', accent: 'text-emerald-600' },
  orange: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-900', accent: 'text-amber-600' },
  red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-900', accent: 'text-red-600' },
  slate: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-900', accent: 'text-slate-600' },
} as const

const HORA_DEFAULT = '04:00'

function defaultEnvio(): ConfigEnvioItem {
  return { habilitado: true, cco: [], programador: HORA_DEFAULT }
}

export function ConfiguracionNotificaciones() {
  const [configEnvios, setConfigEnvios] = useState<Record<string, ConfigEnvioItem>>({})
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    setCargando(true)
    try {
      const [data, plantillasList] = await Promise.all([
        emailConfigService.obtenerConfiguracionEnvios() as Promise<Record<string, ConfigEnvioItem>>,
        notificacionService.listarPlantillas(undefined, false).catch(() => [] as NotificacionPlantilla[]),
      ])
      setConfigEnvios(data || {})
      setPlantillas(plantillasList || [])
    } catch (error) {
      toast.error('Error al cargar la configuración de envíos')
    } finally {
      setCargando(false)
    }
  }

  const getConfig = (tipo: string): ConfigEnvioItem => {
    const c = configEnvios[tipo]
    if (!c) return defaultEnvio()
    return {
      habilitado: c.habilitado !== false,
      cco: Array.isArray(c.cco) ? c.cco : [],
      plantilla_id: c.plantilla_id ?? null,
      programador: c.programador ?? HORA_DEFAULT,
    }
  }

  const setConfig = (tipo: string, upd: Partial<ConfigEnvioItem>) => {
    setConfigEnvios((prev) => {
      const current = prev[tipo] || defaultEnvio()
      return { ...prev, [tipo]: { ...current, ...upd } }
    })
  }

  const toggleEnvio = (tipo: string) => {
    const c = getConfig(tipo)
    setConfig(tipo, { habilitado: !c.habilitado })
  }

  const actualizarCCO = (tipo: string, index: number, email: string) => {
    const c = getConfig(tipo)
    const nuevosCCO = [...c.cco]
    if (index < nuevosCCO.length) nuevosCCO[index] = email
    else nuevosCCO.push(email)
    setConfig(tipo, { cco: nuevosCCO.slice(0, 3) })
  }

  const eliminarCCO = (tipo: string, index: number) => {
    const c = getConfig(tipo)
    setConfig(tipo, { cco: c.cco.filter((_, i) => i !== index) })
  }

  const guardarConfiguracionEnvios = async () => {
    try {
      setGuardandoEnvios(true)
      await emailConfigService.actualizarConfiguracionEnvios(configEnvios)
      toast.success('Configuración de envíos guardada')
    } catch (error) {
      toast.error('Error al guardar la configuración de envíos')
    } finally {
      setGuardandoEnvios(false)
    }
  }

  const plantillasPorTipo = (tipo: string): NotificacionPlantilla[] =>
    plantillas.filter((p) => p.tipo === tipo)

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center text-gray-500">
          <Clock className="h-8 w-8 mx-auto animate-pulse mb-2 text-blue-500" />
          <p>Cargando configuración...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-600" />
            Configuración por criterio
          </CardTitle>
          <CardDescription>
            Cada pestaña de notificaciones tiene su plantilla, correos (CCO), activación y hora de envío. Las plantillas se gestionan en Notificaciones &rarr; Plantillas.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card className="border-blue-100 bg-blue-50/50">
        <CardContent className="py-3 px-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <Mail className="h-4 w-4 text-blue-600" />
            <span>Los correos se envían con la cuenta configurada en <strong>Configuración &gt; Email</strong> (Gmail/SMTP).</span>
          </div>
          <Link
            to="/configuracion?tab=email"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            <LinkIcon className="h-4 w-4" />
            Ir a Configuración (Email)
          </Link>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4">
        {CRITERIOS.map(({ tipo, label, categoria, color }) => {
          const config = getConfig(tipo)
          const col = COLORES[color]
          const listaPlantillas = plantillasPorTipo(tipo)

          return (
            <Card key={tipo} className={`${col.bg} ${col.border} border-2 overflow-hidden`}>
              <CardContent className="p-0">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 p-5">
                  {/* Fila 1: Título + ON/OFF */}
                  <div className="md:col-span-12 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h3 className={`font-bold text-lg ${col.text}`}>{label}</h3>
                      <p className={`text-sm ${col.accent} opacity-80`}>{categoria}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium ${!config.habilitado ? 'text-gray-700' : 'text-gray-400'}`}>OFF</span>
                      <button
                        type="button"
                        onClick={() => toggleEnvio(tipo)}
                        className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                          config.habilitado ? 'bg-blue-600' : 'bg-gray-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform shadow ${
                            config.habilitado ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <span className={`text-xs font-medium ${config.habilitado ? 'text-gray-700' : 'text-gray-400'}`}>ON</span>
                    </div>
                  </div>

                  {/* Fila 2: Plantilla */}
                  <div className="md:col-span-12 md:grid md:grid-cols-12 md:gap-4">
                    <div className="md:col-span-4">
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                        <FileText className="h-4 w-4" />
                        Plantilla a enviar
                      </label>
                      <Select
                        value={config.plantilla_id ? String(config.plantilla_id) : '__ninguna__'}
                        onValueChange={(v) => setConfig(tipo, { plantilla_id: v === '__ninguna__' ? null : parseInt(v, 10) })}
                        disabled={!config.habilitado}
                      >
                        <SelectTrigger className="w-full bg-white">
                          <SelectValue placeholder="Seleccionar plantilla" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__ninguna__">Sin plantilla (texto por defecto)</SelectItem>
                          {listaPlantillas.map((p) => (
                            <SelectItem key={p.id} value={String(p.id)}>
                              {p.nombre || `Plantilla #${p.id}`}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="md:col-span-4">
                      <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-1">
                        <Clock className="h-4 w-4" />
                        Programador (hora)
                      </label>
                      <Input
                        type="time"
                        value={config.programador || HORA_DEFAULT}
                        onChange={(e) => setConfig(tipo, { programador: e.target.value })}
                        disabled={!config.habilitado}
                        className="bg-white"
                      />
                    </div>

                    <div className="md:col-span-4" />
                  </div>

                  {/* Fila 3: Correos CCO */}
                  <div className="md:col-span-12">
                    <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                      <Mail className="h-4 w-4" />
                      Copia (CCO) – hasta 3 correos
                    </label>
                    <div className="space-y-2">
                      {[0, 1, 2].map((index) => (
                        <div key={index} className="flex items-center gap-2">
                          <Input
                            type="email"
                            placeholder={`ejemplo${index + 1}@correo.com`}
                            value={config.cco[index] || ''}
                            onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                            className="flex-1 bg-white"
                            disabled={!config.habilitado}
                          />
                          {config.cco[index] && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => eliminarCCO(tipo, index)}
                              disabled={!config.habilitado}
                              className="shrink-0 hover:bg-red-100 hover:text-red-600"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t">
        <Link
          to="/notificaciones/plantillas"
          className="text-sm text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
        >
          <FileText className="h-4 w-4" />
          Gestionar plantillas en Notificaciones
        </Link>
        <Button
          onClick={guardarConfiguracionEnvios}
          disabled={guardandoEnvios}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <Settings className="h-4 w-4 mr-2" />
          {guardandoEnvios ? 'Guardando...' : 'Guardar configuración'}
        </Button>
      </div>
    </div>
  )
}
