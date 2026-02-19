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
  TestTube,
} from 'lucide-react'
import { emailConfigService } from '../../services/notificacionService'
import { notificacionService, type NotificacionPlantilla } from '../../services/notificacionService'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'

/** Claves reservadas en la config (no son tipos de caso) */
const CLAVES_GLOBALES = ['modo_pruebas', 'email_pruebas', 'emails_pruebas'] as const

/** Tipo de configuraciÃƒÂ³n por criterio (habilitado, cco, plantilla opcional, programador) */
export type ConfigEnvioItem = {
  habilitado: boolean
  cco: string[]
  plantilla_id?: number | null
  programador?: string
}

/** Respuesta de la API: config por tipo + modo_pruebas y email_pruebas (un solo objeto, sin duplicar) */
export type ConfigEnvioCompleta = Record<string, ConfigEnvioItem | boolean | string | string[]>

const CRITERIOS: { tipo: string; label: string; categoria: string; color: 'blue' | 'green' | 'orange' | 'red' | 'slate' }[] = [
  { tipo: 'PAGO_5_DIAS_ANTES', label: 'Faltan 5 dÃƒÂ­as', categoria: 'NotificaciÃƒÂ³n previa', color: 'blue' },
  { tipo: 'PAGO_3_DIAS_ANTES', label: 'Faltan 3 dÃƒÂ­as', categoria: 'NotificaciÃƒÂ³n previa', color: 'blue' },
  { tipo: 'PAGO_1_DIA_ANTES', label: 'Falta 1 dÃƒÂ­a', categoria: 'NotificaciÃƒÂ³n previa', color: 'blue' },
  { tipo: 'PAGO_DIA_0', label: 'Hoy vence', categoria: 'DÃƒÂ­a de pago', color: 'green' },
  { tipo: 'PAGO_1_DIA_ATRASADO', label: '1 dÃƒÂ­a de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_3_DIAS_ATRASADO', label: '3 dÃƒÂ­as de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_5_DIAS_ATRASADO', label: '5 dÃƒÂ­as de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PREJUDICIAL', label: 'Prejudicial', categoria: 'Prejudicial', color: 'red' },
  { tipo: 'MORA_61', label: '61+ dÃƒÂ­as de mora', categoria: 'Mora 61+', color: 'slate' },
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
  const [modoPruebas, setModoPruebas] = useState(false)
  const [emailsPruebas, setEmailsPruebas] = useState<[string, string]>(['', ''])
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])
  const [enviandoPrueba, setEnviandoPrueba] = useState(false)
  const [plantillaSeleccionada, setPlantillaSeleccionada] = useState<number | null>(null)

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    setCargando(true)
    try {
      const [data, plantillasList] = await Promise.all([
        emailConfigService.obtenerConfiguracionEnvios() as Promise<ConfigEnvioCompleta>,
        notificacionService.listarPlantillas(undefined, false).catch(() => [] as NotificacionPlantilla[]),
      ])
      const raw = data || {}
      setModoPruebas(raw.modo_pruebas === true)
      if (Array.isArray(raw.emails_pruebas)) {
        const arr = raw.emails_pruebas
        setEmailsPruebas([arr[0] ?? '', arr[1] ?? ''])
      } else if (typeof raw.email_pruebas === 'string') {
        setEmailsPruebas([raw.email_pruebas, ''])
      } else {
        setEmailsPruebas(['', ''])
      }
      const sinGlobales = { ...raw }
      CLAVES_GLOBALES.forEach((k) => delete sinGlobales[k])
      setConfigEnvios(sinGlobales as Record<string, ConfigEnvioItem>)
      setPlantillas(plantillasList || [])
    } catch (error) {
      toast.error('Error al cargar la configuraciÃƒÂ³n de envÃƒÂ­os')
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
      const payload: ConfigEnvioCompleta = {
        ...configEnvios,
        modo_pruebas: modoPruebas,
        emails_pruebas: emailsPruebas.filter((e) => e?.trim()),
        email_pruebas: emailsPruebas[0]?.trim() || '',
      }
      await emailConfigService.actualizarConfiguracionEnvios(payload)
      toast.success('ConfiguraciÃƒÂ³n de envÃƒÂ­os guardada')
    } catch (error) {
      toast.error('Error al guardar la configuraciÃƒÂ³n de envÃƒÂ­os')
    } finally {
      setGuardandoEnvios(false)
    }
  }

  const enModoPrueba = modoPruebas
  const enModoProduccion = !modoPruebas

  const plantillasPorTipo = (tipo: string): NotificacionPlantilla[] =>
    plantillas.filter((p) => p.tipo === tipo)


  const handleEnviarPrueba = async (indice: 0 | 1) => {
    const email = emailsPruebas[indice]?.trim()
    if (modoPruebas && email) {
      try {
        setEnviandoPrueba(true)
        
        // Si hay plantilla seleccionada, usarla; si no, usar mensaje genÃƒÂ©rico
        let asunto = 'Prueba de Notificaciones - RapiCredit'
        let mensaje = 'Este es un correo de prueba para verificar que las plantillas de notificaciÃƒÂ³n se envÃƒÂ­an correctamente.'
        
        if (plantillaSeleccionada) {
          const plantilla = plantillas.find(p => p.id === plantillaSeleccionada)
          if (plantilla) {
            asunto = plantilla.nombre || asunto
            mensaje = plantilla.cuerpo || mensaje
          }
        }
        
        const resultado = await emailConfigService.probarConfiguracionEmail(
          email,
          asunto,
          mensaje,
          undefined
        )
        
        if (resultado.success || resultado.mensaje?.includes('enviado')) {
          toast.success(`Correo de prueba enviado exitosamente a ${email}`)
        } else {
          toast.error(resultado.mensaje || 'Error al enviar el correo de prueba')
        }
      } catch (error: any) {
        toast.error(error?.message || 'Error al enviar el correo de prueba')
      } finally {
        setEnviandoPrueba(false)
      }
    } else {
      toast.error('Configura el correo para enviar pruebas')
    }
  }

  if (cargando) {
  

  return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center text-gray-500">
          <Clock className="h-8 w-8 mx-auto animate-pulse mb-2 text-blue-500" />
          <p>Cargando configuraciÃƒÂ³n...</p>
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
            ConfiguraciÃƒÂ³n por caso
          </CardTitle>
          <CardDescription>
            Asigna una plantilla a cada caso, activa el envÃƒÂ­o y guarda. Las plantillas se crean en ConfiguraciÃƒÂ³n ? Plantillas (texto + variables).
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Modo Prueba / ProducciÃƒÂ³n: un solo bloque, sin duplicar config */}
      <Card className={enModoPrueba ? 'border-amber-300 bg-amber-50/50' : 'border-emerald-200 bg-emerald-50/30'}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            {enModoPrueba ? (
              <>
                <TestTube className="h-4 w-4 text-amber-600" />
                Modo prueba
              </>
            ) : (
              <>
                <Mail className="h-4 w-4 text-emerald-600" />
                Modo producciÃƒÂ³n
              </>
            )}
          </CardTitle>
          <CardDescription>
            {enModoPrueba
              ? 'Todos los emails de notificaciones se envÃƒÂ­an ÃƒÂºnicamente al correo de pruebas. Los clientes no reciben correo. El envÃƒÂ­o por caso queda desactivado en la tabla mientras estÃƒÂ© activo modo prueba.'
              : 'Los emails se envÃƒÂ­an al correo de cada cliente segÃƒÂºn la opciÃƒÂ³n EnvÃƒÂ­o de cada caso.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Toggle Modo Prueba */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Prueba</span>
            <button
              type="button"
              role="switch"
              aria-checked={modoPruebas}
              onClick={() => setModoPruebas(!modoPruebas)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                modoPruebas ? 'bg-amber-500' : 'bg-emerald-600'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${modoPruebas ? 'translate-x-5' : 'translate-x-1'}`} />
            </button>
            <span className="text-sm text-gray-600">{modoPruebas ? 'Activado (solo correo de pruebas)' : 'Desactivado (envÃ­o a clientes)'}</span>
          </div>

          {/* Correos de Prueba */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap w-40">Correo para pruebas 1</label>
              <Input
                type="email"
                placeholder="ejemplo@correo.com"
                value={emailsPruebas[0]}
                onChange={(e) => setEmailsPruebas((prev) => [e.target.value, prev[1]])}
                className="max-w-xs h-9 bg-white"
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap w-40">Correo para pruebas 2</label>
              <Input
                type="email"
                placeholder="ejemplo2@correo.com"
                value={emailsPruebas[1]}
                onChange={(e) => setEmailsPruebas((prev) => [prev[0], e.target.value])}
                className="max-w-xs h-9 bg-white"
              />
            </div>
          </div>

          {/* Selector de Plantilla para Prueba */}
          {modoPruebas && (emailsPruebas[0]?.trim() || emailsPruebas[1]?.trim()) && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Selecciona una plantilla (opcional)
              </label>
              <Select
                value={plantillaSeleccionada?.toString() || ''}
                onValueChange={(val) => setPlantillaSeleccionada(val ? parseInt(val) : null)}
              >
                <SelectTrigger className="w-full bg-white">
                  <SelectValue placeholder="Plantilla predeterminada" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Plantilla predeterminada</SelectItem>
                  {plantillas.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.nombre || `Plantilla #${p.id}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Botones Enviar Prueba - uno para cada correo */}
          {modoPruebas && (emailsPruebas[0]?.trim() || emailsPruebas[1]?.trim()) && (
            <div className="pt-4 border-t border-amber-200 space-y-2">
              {emailsPruebas[0]?.trim() && (
                <Button
                  onClick={() => handleEnviarPrueba(0)}
                  disabled={enviandoPrueba}
                  className="w-full bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 text-white font-semibold py-2 h-auto flex items-center justify-center gap-2 rounded-lg transition-all"
                >
                  <Mail className="h-5 w-5" />
                  {enviandoPrueba ? 'Enviando...' : `Enviar a ${emailsPruebas[0]}`}
                </Button>
              )}
              {emailsPruebas[1]?.trim() && (
                <Button
                  onClick={() => handleEnviarPrueba(1)}
                  disabled={enviandoPrueba}
                  className="w-full bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 disabled:opacity-50 text-white font-semibold py-2 h-auto flex items-center justify-center gap-2 rounded-lg transition-all"
                >
                  <Mail className="h-5 w-5" />
                  {enviandoPrueba ? 'Enviando...' : `Enviar a ${emailsPruebas[1]}`}
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Caso</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Plantilla</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-700 w-24">EnvÃƒÂ­o</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 w-32">Opciones</th>
            </tr>
          </thead>
          <tbody>
            {CRITERIOS.map(({ tipo, label, categoria, color }) => {
              const config = getConfig(tipo)
              const col = COLORES[color]
              const listaPlantillas = plantillasPorTipo(tipo)
            

  return (
                <tr key={tipo} className={`border-b border-gray-100 ${col.bg}`}>
                  <td className="py-3 px-4">
                    <span className={`font-medium ${col.text}`}>{label}</span>
                    <span className={`block text-xs ${col.accent} opacity-80`}>{categoria}</span>
                  </td>
                  <td className="py-3 px-4">
                    <Select
                      value={config.plantilla_id ? String(config.plantilla_id) : '__ninguna__'}
                      onValueChange={(v) => setConfig(tipo, { plantilla_id: v === '__ninguna__' ? null : parseInt(v, 10) })}
                      disabled={enModoPrueba || !config.habilitado}
                    >
                      <SelectTrigger className="w-full max-w-xs bg-white border-gray-200">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__ninguna__">Texto por defecto</SelectItem>
                        {listaPlantillas.map((p) => (
                          <SelectItem key={p.id} value={String(p.id)}>{p.nombre || `#${p.id}`}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      type="button"
                      onClick={() => !enModoPrueba && toggleEnvio(tipo)}
                      disabled={enModoPrueba}
                      title={enModoPrueba ? 'EnvÃƒÂ­o desactivado en modo prueba' : (config.habilitado ? 'Desactivar envÃƒÂ­o' : 'Activar envÃƒÂ­o')}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                        enModoPrueba ? 'bg-gray-300 cursor-not-allowed' : config.habilitado ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${config.habilitado && !enModoPrueba ? 'translate-x-5' : 'translate-x-1'}`} />
                    </button>
                    {enModoPrueba && <span className="block text-xs text-gray-500 mt-0.5">Desactivado</span>}
                  </td>
                  <td className="py-3 px-4">
                    <details className="group">
                      <summary className="cursor-pointer text-blue-600 hover:text-blue-800 text-xs font-medium list-none">
                        CCO / hora
                      </summary>
                      <div className="mt-2 space-y-2 pl-0">
                        <Input
                          type="time"
                          value={config.programador || HORA_DEFAULT}
                          onChange={(e) => setConfig(tipo, { programador: e.target.value })}
                          disabled={enModoPrueba || !config.habilitado}
                          className="h-8 text-xs bg-white w-28"
                        />
                        {[0, 1, 2].map((i) => (
                          <div key={i} className="flex gap-1">
                            <Input
                              type="email"
                              placeholder="CCO"
                              value={config.cco[i] || ''}
                              onChange={(e) => actualizarCCO(tipo, i, e.target.value)}
                              className="h-8 text-xs flex-1 bg-white"
                              disabled={enModoPrueba || !config.habilitado}
                            />
                            {config.cco[i] && (
                              <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => eliminarCCO(tipo, i)}>
                                <X className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <Link to="/configuracion?tab=email" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
            <Mail className="h-4 w-4" /> Email (SMTP)
          </Link>
          <Link to="/configuracion?tab=plantillas" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
            <FileText className="h-4 w-4" /> Crear/editar plantillas
          </Link>
        </div>
        <Button onClick={guardarConfiguracionEnvios} disabled={guardandoEnvios} className="bg-blue-600 hover:bg-blue-700">
          {guardandoEnvios ? 'Guardando...' : 'Guardar'}
        </Button>              
              {/* BotÃƒÂ³n EnvÃƒÂ­o Manual de Prueba */}
              
      </div>
    </div>
  )
}














